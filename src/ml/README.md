# Machine Learning

Core ML logic for the platform.
- Evaluates 5 models: RandomForest, ExtraTrees, GradientBoosting, LogisticRegression, SVC (disabled due to time).
- Uses 5-Fold Stratified CV (F1 Score) for selection.
- Ensures zero data leakage.
- Integrates with MLflow for experiment tracking and model registry.
