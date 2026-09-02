# Machine Learning Module

Robust, multi-model machine learning pipeline for detecting cyber-attacks in network traffic (CICIDS2017).

## Pipeline Workflow

The `train.py` script executes the following:
1. **Extraction**: Loads features and labels from `data/exports/cleaned_logs.jsonl`.
2. **Strict Split**: Performs an 80/20 stratified train/test split.
3. **Safe Scaling**: Fits a `StandardScaler` **only** on training data to prevent data leakage.
4. **CV Selection**: Evaluates 5 candidate models (`RandomForest`, `ExtraTrees`, `GradientBoosting`, `LogisticRegression`, `SVC`) using 5-Fold Stratified CV on the training set.
5. **Evaluation**: The best model (highest CV F1) is evaluated **exactly once** on the held-out test set.
6. **Logging**: Results, test metrics, and artifacts are saved locally and logged to MLflow (each candidate as a child run).

## Anti-Leakage Guarantees
- Zero data leakage between train and test sets.
- Cross-validation operates strictly within the training fold.
- Evaluation on the test set occurs only once, after model selection is finalized.

## Artifacts
Generated artifacts (models, scalers, reports) are stored in `src/ml/artifacts/` and logged to MLflow.
