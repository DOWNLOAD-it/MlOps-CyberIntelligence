# MlOps-CyberIntelligence

Welcome to the **MlOps-CyberIntelligence** platform. This project provides an end-to-end MLOps pipeline for intrusion detection using the CICIDS2017 Network Traffic Logs dataset.

## Architecture

The platform integrates a robust stack for data engineering, model training, and real-time inference serving:
- **Dagster**: Orchestration of data and ML pipelines.
- **Redpanda / Kafka**: Streaming data ingestion.
- **dbt + DuckDB**: Data transformations.
- **MLflow**: Model tracking and registry.
- **PostgreSQL**: Real-time alerts database for inference results.
- **FastAPI**: Backend serving for model inference.
- **React / Next.js**: Interactive UI Web App for users.
- **Grafana**: SOC Dashboard for visualization and monitoring.

## Services & Ports
- **Dagster**: 4301
- **MLflow**: 4302
- **Redpanda**: 4303-4306
- **Grafana**: 4307
- **FastAPI**: 4308
- **React WebApp**: 4309

## ML Pipeline
1. Training data is processed with zero leakage guaranteed.
2. 5 candidate models are evaluated using 5-Fold Stratified CV (F1 Score):
   - RandomForest
   - ExtraTrees
   - GradientBoosting
   - LogisticRegression
   - SVC (currently disabled due to training time)
3. The best model is evaluated ONCE on a held-out test set.

## Deployment & CI/CD
- Deployed via **Docker Compose** on a shared server using the **Komodo orchestrator**.
- **CI/CD**: GitHub Actions triggers a Komodo webhook automatically on push to the `master` branch.
