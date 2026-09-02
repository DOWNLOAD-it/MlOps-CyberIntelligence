# ML Module — Network Anomaly Detection

Multi-model machine learning pipeline for detecting cyber-attacks in network traffic.

## Files
| File | Description |
|------|-------------|
| 	rain.py | Multi-model training pipeline (5 candidates, CV selection, MLflow logging) |
| evaluate.py | Evaluation report generation, overfitting detection, artifact saving |
| eatures.py | Feature extraction and StandardScaler preprocessing |
| predict.py | Inference on new streaming data using saved model |

## Anti-Leakage Guarantees
- Train/test split done **before** any preprocessing
- StandardScaler fitted on **training data only**
- CV runs **entirely within the training fold**
- Test set evaluated **exactly once** after model selection

## Models Compared
- RandomForest, ExtraTrees, GradientBoosting, LogisticRegression, SVC

## Artifacts
Saved to rtifacts/ after training:
- model.joblib — Best model
- scaler.joblib — Fitted scaler
- evaluation_report.txt — Full evaluation report
- model_comparison.json — All CV scores
- confusion_matrix.json — Test set confusion matrix
