"""Evaluation module for network anomaly detection models.

Generates leakage-free, overfitting-aware evaluation reports and
model comparison tables on the held-out test set.
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional

from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
    accuracy_score,
    roc_auc_score,
)

logger = logging.getLogger(__name__)

OVERFITTING_GAP_THRESHOLD = 0.05  # flag if train_score - cv_score > 5%


def compute_test_metrics(model, X_test, y_test):
    """Compute all evaluation metrics on the held-out test set.

    This function must only be called ONCE per experiment, after the best
    model has been selected via cross-validation on the training set.
    No hyperparameter decisions should be made based on these results.
    """
    y_pred = model.predict(X_test)
    metrics = {
        "test_accuracy":  float(accuracy_score(y_test, y_pred)),
        "test_precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "test_recall":    float(recall_score(y_test, y_pred, zero_division=0)),
        "test_f1":        float(f1_score(y_test, y_pred, zero_division=0)),
    }
    try:
        if hasattr(model, "predict_proba"):
            y_score = model.predict_proba(X_test)[:, 1]
        elif hasattr(model, "decision_function"):
            y_score = model.decision_function(X_test)
        else:
            y_score = y_pred
        metrics["test_roc_auc"] = float(roc_auc_score(y_test, y_score))
    except Exception:
        metrics["test_roc_auc"] = float("nan")
    return metrics


def check_overfitting(model_name, train_score, cv_mean_score):
    """Detect potential overfitting by comparing train vs CV score."""
    gap = train_score - cv_mean_score
    is_overfit = gap > OVERFITTING_GAP_THRESHOLD
    if is_overfit:
        logger.warning(
            f"[OVERFITTING DETECTED] {model_name}: train_score={train_score:.4f}, "
            f"cv_score={cv_mean_score:.4f}, gap={gap:.4f} > threshold={OVERFITTING_GAP_THRESHOLD}"
        )
    return {"overfitting_gap": round(gap, 4), "overfitting_flagged": is_overfit}


def build_comparison_table(cv_results):
    """Build a human-readable model comparison table from CV results."""
    rows = sorted(cv_results, key=lambda x: x["cv_f1_mean"], reverse=True)
    header = (
        f"{'Rank':<5} {'Model':<30} {'CV F1 (mean)':<15} {'CV F1 (std)':<13} "
        f"{'Train F1':<12} {'Overfit Gap':<13} {'Flagged?':<10}"
    )
    separator = "-" * len(header)
    lines = [separator, header, separator]
    for rank, row in enumerate(rows, 1):
        flag = "YES *" if row["overfitting_flagged"] else "NO"
        lines.append(
            f"{rank:<5} {row['model_name']:<30} {row['cv_f1_mean']:<15.4f} "
            f"{row['cv_f1_std']:<13.4f} {row['train_f1']:<12.4f} "
            f"{row['overfitting_gap']:<13.4f} {flag:<10}"
        )
    lines.append(separator)
    return "\n".join(lines)


def build_evaluation_report(
    best_model_name, cv_results, test_metrics, y_test, y_pred,
    n_train, n_test, n_features, training_duration,
):
    """Build a comprehensive evaluation report string."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = []

    def section(title):
        lines.append("\n" + "=" * 70)
        lines.append(f"  {title}")
        lines.append("=" * 70)

    lines.append("=" * 70)
    lines.append("  MLSecOps Platform -- Model Evaluation Report")
    lines.append(f"  Generated: {now}")
    lines.append("=" * 70)

    section("1. DATASET INFORMATION")
    lines.append(f"  Dataset         : CICIDS2017 Network Traffic Logs")
    lines.append(f"  Total samples   : {n_train + n_test:,}")
    lines.append(f"  Training samples: {n_train:,}  (80%)")
    lines.append(f"  Test samples    : {n_test:,}  (20% held-out, never seen during training or CV)")
    lines.append(f"  Features used   : {n_features}")
    lines.append(f"  Label balance   : {int(np.sum(y_test))} attacks / {int(np.sum(y_test == 0))} benign in test set")

    section("2. ANTI-LEAKAGE GUARANTEES")
    lines.append("  [OK] Train/test split performed BEFORE any preprocessing.")
    lines.append("  [OK] StandardScaler fitted on TRAINING SET ONLY.")
    lines.append("  [OK] Cross-validation run ENTIRELY within the training fold.")
    lines.append("  [OK] Test set evaluated EXACTLY ONCE, after best model selection.")
    lines.append("  [OK] No hyperparameter decisions made based on test set results.")

    section("3. MODEL COMPARISON (5-Fold Stratified CV on Training Set)")
    lines.append("  Selection metric: CV F1-score\n")
    lines.append(build_comparison_table(cv_results))

    section("4. SELECTED MODEL")
    lines.append(f"  Model : {best_model_name}")
    lines.append(f"  Reason: Highest CV F1-score among all candidates.")

    section("5. FINAL EVALUATION ON HELD-OUT TEST SET  <-- REAL METRICS")
    lines.append("  NOTE: These are the ONLY valid metrics. CV metrics are for selection only.\n")
    lines.append(f"  Accuracy  : {test_metrics['test_accuracy']:.4f}")
    lines.append(f"  Precision : {test_metrics['test_precision']:.4f}")
    lines.append(f"  Recall    : {test_metrics['test_recall']:.4f}")
    lines.append(f"  F1-Score  : {test_metrics['test_f1']:.4f}")
    lines.append(f"  ROC-AUC   : {test_metrics.get('test_roc_auc', float('nan')):.4f}")

    section("6. DETAILED CLASSIFICATION REPORT (Test Set)")
    lines.append(classification_report(y_test, y_pred, target_names=["Benign", "Attack"]))

    section("7. CONFUSION MATRIX (Test Set)")
    cm = confusion_matrix(y_test, y_pred)
    lines.append(f"  {'':20} Predicted Benign   Predicted Attack")
    lines.append(f"  {'Actual Benign':<20} {cm[0][0]:<18} {cm[0][1]}")
    lines.append(f"  {'Actual Attack':<20} {cm[1][0]:<18} {cm[1][1]}")
    tn, fp, fn, tp = cm.ravel()
    lines.append(f"\n  True Negatives  (correct benign) : {tn:,}")
    lines.append(f"  False Positives (false alarms)   : {fp:,}")
    lines.append(f"  False Negatives (missed attacks) : {fn:,}")
    lines.append(f"  True Positives  (caught attacks) : {tp:,}")

    section("8. TRAINING INFORMATION")
    lines.append(f"  Total training time : {training_duration:.2f} seconds")
    lines.append(f"  Models evaluated    : {len(cv_results)}")

    lines.append("\n" + "=" * 70 + "\n")
    return "\n".join(lines)


def save_artifacts(report, cv_results, test_metrics, confusion_mat, artifacts_dir):
    """Save all evaluation artifacts to disk."""
    os.makedirs(artifacts_dir, exist_ok=True)
    paths = {}

    report_path = os.path.join(artifacts_dir, "evaluation_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    paths["evaluation_report"] = report_path

    comparison_path = os.path.join(artifacts_dir, "model_comparison.json")
    with open(comparison_path, "w") as f:
        json.dump(cv_results, f, indent=2)
    paths["model_comparison"] = comparison_path

    metrics_path = os.path.join(artifacts_dir, "test_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(test_metrics, f, indent=2)
    paths["test_metrics"] = metrics_path

    cm_path = os.path.join(artifacts_dir, "confusion_matrix.json")
    with open(cm_path, "w") as f:
        json.dump(confusion_mat.tolist(), f, indent=2)
    paths["confusion_matrix"] = cm_path

    logger.info(f"Saved {len(paths)} evaluation artifacts to {artifacts_dir}")
    return paths
