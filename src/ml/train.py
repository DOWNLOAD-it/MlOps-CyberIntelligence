"""Model training script for network anomaly detection.

Multi-model experiment pipeline for CICIDS2017 network traffic logs.
Each candidate model gets its own MLflow child run so you can compare
all models side-by-side in the MLflow UI.

The best model (by CV F1) is then evaluated once on the held-out test
set and registered in the MLflow Model Registry.

Anti-leakage guarantees:
  - Train/test split performed BEFORE any preprocessing.
  - StandardScaler fitted on training data ONLY.
  - CV runs entirely within the training fold.
  - Test set evaluated EXACTLY ONCE, after model selection.
"""

import os
import json
import logging
import time
import numpy as np
import joblib

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_validate
from sklearn.metrics import confusion_matrix as cm_fn

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
]

CV_FOLDS = 5
SELECTION_METRIC = "f1"
EXPERIMENT_NAME = "mlsecops-anomaly-detection"


def get_project_root() -> str:
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


def _run_cross_validation(name, model, X_train, y_train):
    """Run stratified CV on the training set only and return results."""
    logger.info(f"  [{name}] Running {CV_FOLDS}-fold stratified CV...")
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=42)
    cv_results = cross_validate(
        model, X_train, y_train,
        cv=cv, scoring=SELECTION_METRIC,
        return_train_score=True, n_jobs=-1,
    )
    cv_f1_mean = float(np.mean(cv_results["test_score"]))
    cv_f1_std  = float(np.std(cv_results["test_score"]))
    train_f1   = float(np.mean(cv_results["train_score"]))
    logger.info(f"  [{name}] CV F1: {cv_f1_mean:.4f} +/- {cv_f1_std:.4f} | Train F1: {train_f1:.4f}")
    overfit = check_overfitting(name, train_f1, cv_f1_mean)
    return {
        "model_name": name,
        "cv_f1_mean": cv_f1_mean,
        "cv_f1_std":  cv_f1_std,
        "train_f1":   train_f1,
        **overfit,
    }


def _log_candidate_to_mlflow(parent_run_id, name, model, cv_result,
                               X_train, y_train, is_best, artifacts_dir):
    """Log a single candidate model as a child MLflow run.

    Each candidate gets its own child run inside the parent experiment run
    so all models are visible and comparable in the MLflow UI.
    """
    with mlflow.start_run(run_name=name, nested=True) as child_run:
        mlflow.set_tags({
            "model_name":    name,
            "is_best_model": str(is_best),
            "dataset":       "CICIDS2017",
            "task":          "anomaly_detection",
            "phase":         "cross_validation",
        })

        # Log CV params
        mlflow.log_params({
            "model":            name,
            "cv_folds":         CV_FOLDS,
            "selection_metric": SELECTION_METRIC,
            "n_train_samples":  X_train.shape[0],
            "n_features":       X_train.shape[1],
        })

        # Log CV metrics (these are training-phase metrics, NOT test metrics)
        mlflow.log_metrics({
            "cv_f1_mean":       cv_result["cv_f1_mean"],
            "cv_f1_std":        cv_result["cv_f1_std"],
            "train_f1":         cv_result["train_f1"],
            "overfitting_gap":  cv_result["overfitting_gap"],
        })

        # Refit on full training set and log model artifact
        model.fit(X_train, y_train)
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path=f"{name.lower()}_model",
        )

        logger.info(f"  [{name}] Logged to MLflow child run (run_id: {child_run.info.run_id})")
        return child_run.info.run_id


def train_model(records: list, random_state: int = 42) -> dict:
    """Multi-model training pipeline with per-model MLflow runs.

    Steps:
      1. Extract features and labels.
      2. Single 80/20 stratified split -- test set locked away.
      3. Fit scaler on training data only.
      4. For each candidate: run 5-Fold CV, log as a child MLflow run.
      5. Select best model by CV F1.
      6. Evaluate ONCE on held-out test set.
      7. Register best model + log full evaluation report to MLflow.
    """
    if not records:
        logger.error("No records provided for training.")
        return {}

    total_start = time.time()

    logger.info("Step 1/7 -- Extracting features and labels...")
    X = extract_features(records)
    y = extract_labels(records)

    logger.info("Step 2/7 -- Train/test split (80/20 stratified) BEFORE any preprocessing...")
    X_train_raw, X_test_raw, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=random_state, stratify=y
    )
    logger.info(f"  Train: {len(y_train):,} | Test: {len(y_test):,}")

    logger.info("Step 3/7 -- Fitting StandardScaler on training set ONLY...")
    X_train, scaler = preprocess_features(X_train_raw, fit=True)
    X_test, _       = preprocess_features(X_test_raw, scaler=scaler, fit=False)

    logger.info(f"Step 4/7 -- Training & logging all {len(CANDIDATE_MODELS)} models to MLflow...")

    artifacts_dir = os.path.join(get_project_root(), "src", "ml", "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)

    cv_results = []
    child_run_ids = {}

    # ---- Setup MLflow experiment ----
    if MLFLOW_AVAILABLE:
        try:
            tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")
            mlflow.set_tracking_uri(tracking_uri)
            mlflow.set_experiment(EXPERIMENT_NAME)
        except Exception as e:
            logger.warning(f"MLflow setup failed: {e}")

    # ---- Parent run wraps all candidate runs ----
    parent_ctx = mlflow.start_run(run_name="multi_model_comparison") if MLFLOW_AVAILABLE else None

    try:
        for name, model in CANDIDATE_MODELS:
            cv_result = _run_cross_validation(name, model, X_train, y_train)
            cv_results.append(cv_result)

            if MLFLOW_AVAILABLE and parent_ctx is not None:
                try:
                    child_id = _log_candidate_to_mlflow(
                        parent_run_id=parent_ctx.info.run_id,
                        name=name,
                        model=model,
                        cv_result=cv_result,
                        X_train=X_train,
                        y_train=y_train,
                        is_best=False,   # updated later for winner
                        artifacts_dir=artifacts_dir,
                    )
                    child_run_ids[name] = child_id
                except Exception as e:
                    logger.warning(f"MLflow child run failed for {name}: {e}")

        logger.info("Step 5/7 -- Selecting best model by CV F1...")
        best_result = max(cv_results, key=lambda r: r["cv_f1_mean"])
        best_name   = best_result["model_name"]
        best_model  = next(m for n, m in CANDIDATE_MODELS if n == best_name)
        logger.info(f"  Winner: {best_name} (CV F1={best_result['cv_f1_mean']:.4f})")

        logger.info(f"Step 6/7 -- Refitting '{best_name}' on full training set...")
        best_model.fit(X_train, y_train)

        logger.info("Step 7/7 -- ONE-TIME evaluation on held-out test set...")
        test_metrics = compute_test_metrics(best_model, X_test, y_test)
        y_pred       = best_model.predict(X_test)
        total_dur    = time.time() - total_start

        logger.info(
            f"  F1={test_metrics['test_f1']:.4f} | "
            f"Recall={test_metrics['test_recall']:.4f} | "
            f"ROC-AUC={test_metrics.get('test_roc_auc', float('nan')):.4f}"
        )

        confusion_mat = cm_fn(y_test, y_pred)
        report_str    = build_evaluation_report(
            best_model_name=best_name,
            cv_results=cv_results,
            test_metrics=test_metrics,
            y_test=y_test,
            y_pred=y_pred,
            n_train=len(y_train),
            n_test=len(y_test),
            n_features=X_train.shape[1],
            training_duration=total_dur,
        )
        print("\n" + report_str)

        artifact_paths = save_artifacts(
            report=report_str,
            cv_results=cv_results,
            test_metrics=test_metrics,
            confusion_mat=confusion_mat,
            artifacts_dir=artifacts_dir,
        )

        model_path  = os.path.join(artifacts_dir, "model.joblib")
        scaler_path = os.path.join(artifacts_dir, "scaler.joblib")
        joblib.dump(best_model, model_path)
        joblib.dump(scaler, scaler_path)

        # ---- Update parent run with final results ----
        if MLFLOW_AVAILABLE and parent_ctx is not None:
            try:
                mlflow.set_tags({
                    "best_model":    best_name,
                    "dataset":       "CICIDS2017",
                    "task":          "anomaly_detection",
                    "anti_leakage":  "True",
                    "pipeline":      "multi_model_comparison",
                })
                mlflow.log_params({
                    "best_model":          best_name,
                    "n_candidates":        len(CANDIDATE_MODELS),
                    "cv_folds":            CV_FOLDS,
                    "test_split":          0.2,
                    "scaler":              "StandardScaler",
                    "n_features":          X_train.shape[1],
                    "n_train":             len(y_train),
                    "n_test":              len(y_test),
                    "best_cv_f1_mean":     round(best_result["cv_f1_mean"], 4),
                    "overfitting_flagged": best_result["overfitting_flagged"],
                    "total_duration_s":    round(total_dur, 2),
                })
                # Log final test metrics on parent run
                mlflow.log_metrics(test_metrics)

                # Register best model in Model Registry
                mlflow.sklearn.log_model(
                    sk_model=best_model,
                    artifact_path=f"best_model_{best_name.lower()}",
                    registered_model_name="network-anomaly-detector",
                )

                # Log all evaluation artifacts
                for path in artifact_paths.values():
                    mlflow.log_artifact(path, "evaluation")
                mlflow.log_artifact(scaler_path, "scaler")

                parent_run_id = parent_ctx.info.run_id
                logger.info(f"MLflow parent run logged (run_id: {parent_run_id})")
            except Exception as e:
                logger.warning(f"MLflow parent run logging failed: {e}")

    finally:
        if MLFLOW_AVAILABLE and parent_ctx is not None:
            mlflow.end_run()

    return {
        "best_model":  best_name,
        "metrics":     test_metrics,
        "cv_results":  cv_results,
    }


def run_training(data_path: str = None, random_state: int = None) -> dict:
    """Orchestrator: load data and run the multi-model pipeline."""
    if random_state is None:
        random_state = int(os.getenv("ML_RANDOM_STATE", "42"))
    logger.info("Starting multi-model training pipeline...")
    records = load_training_data(data_path)
    return train_model(records, random_state=random_state)


if __name__ == "__main__":
    run_training()
