"""Model training script for network anomaly detection.

Multi-model experiment pipeline for CICIDS2017 network traffic logs.
Trains 5 candidate models, selects the best via cross-validation on the
training set only, then evaluates it once on a held-out test set.

Anti-leakage guarantees:
  - Train/test split is performed BEFORE any preprocessing.
  - StandardScaler is fitted on training data ONLY.
  - CV runs entirely within the training fold.
  - The test set is touched EXACTLY ONCE, after model selection.
"""

import os
import json
import logging
import time
import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_validate
from sklearn.metrics import f1_score, confusion_matrix as cm_fn

try:
    import mlflow
    import mlflow.sklearn
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False

from src.ml.features import extract_features, extract_labels, preprocess_features
from src.ml.evaluate import (
    compute_test_metrics,
    check_overfitting,
    build_evaluation_report,
    save_artifacts,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Candidate model registry
# ---------------------------------------------------------------------------
CANDIDATE_MODELS = [
    (
        "RandomForest",
        RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1, class_weight="balanced"),
    ),
    (
        "ExtraTrees",
        ExtraTreesClassifier(n_estimators=200, random_state=42, n_jobs=-1, class_weight="balanced"),
    ),
    (
        "GradientBoosting",
        GradientBoostingClassifier(n_estimators=100, learning_rate=0.1, random_state=42),
    ),
    (
        "LogisticRegression",
        LogisticRegression(C=1.0, max_iter=1000, random_state=42, class_weight="balanced", n_jobs=-1),
    ),
    (
        "SVC",
        SVC(kernel="rbf", probability=True, random_state=42, class_weight="balanced"),
    ),
]

CV_FOLDS = 5
SELECTION_METRIC = "f1"


def get_project_root() -> str:
    """Get the root directory of the project."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(current_dir))


def load_training_data(data_path: str = None) -> list:
    """Load cleaned records from JSONL file."""
    if data_path is None:
        data_path = os.path.join(get_project_root(), "data", "exports", "cleaned_logs.jsonl")

    if not os.path.exists(data_path):
        logger.error(f"Data file not found: {data_path}")
        return []

    records = []
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        logger.info(f"Loaded {len(records)} records from {data_path}")
    except Exception as e:
        logger.error(f"Error loading training data: {e}")

    return records


def _run_cross_validation(name: str, model, X_train: np.ndarray, y_train: np.ndarray) -> dict:
    """Run stratified CV on the training set only."""
    logger.info(f"  [{name}] Running {CV_FOLDS}-fold stratified CV...")
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=42)

    cv_results = cross_validate(
        model,
        X_train,
        y_train,
        cv=cv,
        scoring=SELECTION_METRIC,
        return_train_score=True,
        n_jobs=-1,
    )

    cv_f1_mean = float(np.mean(cv_results["test_score"]))
    cv_f1_std = float(np.std(cv_results["test_score"]))
    train_f1_mean = float(np.mean(cv_results["train_score"]))

    logger.info(
        f"  [{name}] CV F1: {cv_f1_mean:.4f} +/- {cv_f1_std:.4f} | Train F1: {train_f1_mean:.4f}"
    )

    overfit_info = check_overfitting(name, train_f1_mean, cv_f1_mean)

    return {
        "model_name": name,
        "cv_f1_mean": cv_f1_mean,
        "cv_f1_std": cv_f1_std,
        "train_f1": train_f1_mean,
        **overfit_info,
    }


def train_model(records: list, random_state: int = 42) -> dict:
    """Multi-model training pipeline with strict anti-leakage guarantees.

    Steps:
      1. Extract features and labels.
      2. Single 80/20 stratified split -- test set locked away.
      3. Fit scaler on training data only; transform-only on test.
      4. Run 5-Fold CV on each candidate inside the training set.
      5. Select best model by CV F1.
      6. Refit best model on full training set.
      7. Evaluate ONCE on held-out test set.
      8. Save report + artifacts + log to MLflow.
    """
    if not records:
        logger.error("No records provided for training.")
        return {}

    total_start = time.time()

    logger.info("Step 1/7 -- Extracting features and labels...")
    X = extract_features(records)
    y = extract_labels(records)

    logger.info("Step 2/7 -- Splitting data (80/20 stratified) BEFORE any preprocessing...")
    X_train_raw, X_test_raw, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=random_state, stratify=y
    )
    logger.info(f"  Train: {len(y_train):,} | Test: {len(y_test):,}")

    logger.info("Step 3/7 -- Fitting StandardScaler on training set ONLY...")
    X_train, scaler = preprocess_features(X_train_raw, fit=True)
    X_test, _ = preprocess_features(X_test_raw, scaler=scaler, fit=False)

    logger.info(f"Step 4/7 -- Running {CV_FOLDS}-Fold CV on {len(CANDIDATE_MODELS)} candidate models...")
    cv_results = []
    for name, model in CANDIDATE_MODELS:
        result = _run_cross_validation(name, model, X_train, y_train)
        cv_results.append(result)

    logger.info("Step 5/7 -- Selecting best model by CV F1...")
    best_result = max(cv_results, key=lambda r: r["cv_f1_mean"])
    best_name = best_result["model_name"]
    best_model = next(m for n, m in CANDIDATE_MODELS if n == best_name)
    logger.info(f"  Winner: {best_name} (CV F1={best_result['cv_f1_mean']:.4f})")
    if best_result["overfitting_flagged"]:
        logger.warning(f"  [{best_name}] overfitting flagged (gap={best_result['overfitting_gap']:.4f})")

    logger.info(f"Step 6/7 -- Refitting '{best_name}' on the full training set...")
    fit_start = time.time()
    best_model.fit(X_train, y_train)
    fit_duration = time.time() - fit_start
    logger.info(f"  Done in {fit_duration:.2f}s")

    logger.info("Step 7/7 -- One-time evaluation on held-out test set...")
    test_metrics = compute_test_metrics(best_model, X_test, y_test)
    y_pred = best_model.predict(X_test)
    total_duration = time.time() - total_start
    logger.info(
        f"  Results -> F1={test_metrics['test_f1']:.4f} | "
        f"Recall={test_metrics['test_recall']:.4f} | "
        f"ROC-AUC={test_metrics.get('test_roc_auc', float('nan')):.4f}"
    )

    # Save artifacts
    artifacts_dir = os.path.join(get_project_root(), "src", "ml", "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    confusion_mat = cm_fn(y_test, y_pred)

    report_str = build_evaluation_report(
        best_model_name=best_name,
        cv_results=cv_results,
        test_metrics=test_metrics,
        y_test=y_test,
        y_pred=y_pred,
        n_train=len(y_train),
        n_test=len(y_test),
        n_features=X_train.shape[1],
        training_duration=total_duration,
    )
    print("\n" + report_str)

    artifact_paths = save_artifacts(
        report=report_str,
        cv_results=cv_results,
        test_metrics=test_metrics,
        confusion_mat=confusion_mat,
        artifacts_dir=artifacts_dir,
    )

    model_path = os.path.join(artifacts_dir, "model.joblib")
    scaler_path = os.path.join(artifacts_dir, "scaler.joblib")
    joblib.dump(best_model, model_path)
    joblib.dump(scaler, scaler_path)
    logger.info(f"Saved best model ({best_name}) and scaler to {artifacts_dir}")

    result = {
        "best_model": best_name,
        "metrics": test_metrics,
        "cv_results": cv_results,
        "run_id": None,
        "model_version": None,
    }

    if MLFLOW_AVAILABLE:
        try:
            tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")
            mlflow.set_tracking_uri(tracking_uri)
            mlflow.set_experiment("mlsecops-anomaly-detection")

            with mlflow.start_run() as run:
                mlflow.set_tag(
                    "mlflow.note.content",
                    f"# Multi-Model Evaluation\n\n**Best Model**: `{best_name}`\n\n"
                    f"**Dataset**: CICIDS2017\n\n"
                    f"**Selection**: {CV_FOLDS}-Fold Stratified CV F1 on training set.\n\n"
                    f"**Evaluation**: Strict 20% held-out test set, evaluated once.",
                )
                mlflow.set_tags({
                    "best_model": best_name,
                    "dataset": "CICIDS2017",
                    "task": "anomaly_detection",
                    "pipeline": "multi_model_comparison",
                    "cv_folds": str(CV_FOLDS),
                    "selection_metric": SELECTION_METRIC,
                    "anti_leakage": "True",
                })
                mlflow.log_params({
                    "best_model": best_name,
                    "n_candidates": len(CANDIDATE_MODELS),
                    "cv_folds": CV_FOLDS,
                    "test_split_ratio": 0.2,
                    "stratification": "True",
                    "scaler_type": "StandardScaler",
                    "n_features": X_train.shape[1],
                    "n_train_samples": len(y_train),
                    "n_test_samples": len(y_test),
                    "total_duration_s": round(total_duration, 2),
                    "best_cv_f1_mean": round(best_result["cv_f1_mean"], 4),
                    "best_cv_f1_std": round(best_result["cv_f1_std"], 4),
                    "overfitting_gap": best_result["overfitting_gap"],
                })
                mlflow.log_metrics(test_metrics)
                mlflow.sklearn.log_model(
                    sk_model=best_model,
                    artifact_path=f"{best_name.lower()}_model",
                    registered_model_name="network-anomaly-detector",
                )
                for artifact_path in artifact_paths.values():
                    mlflow.log_artifact(artifact_path, "evaluation")
                mlflow.log_artifact(scaler_path, "scaler")

                result["run_id"] = run.info.run_id
                logger.info(f"MLflow run logged (run_id: {result['run_id']})")
        except Exception as e:
            logger.warning(f"MLflow logging failed: {e}. Artifacts saved locally.")
    else:
        logger.warning("MLflow not installed. Skipping tracking.")

    return result


def run_training(data_path: str = None, random_state: int = None) -> dict:
    """Orchestrator function to load data and run the multi-model pipeline."""
    if random_state is None:
        random_state = int(os.getenv("ML_RANDOM_STATE", "42"))
    logger.info("Starting multi-model training pipeline...")
    records = load_training_data(data_path)
    return train_model(records, random_state=random_state)


if __name__ == "__main__":
    run_training()
