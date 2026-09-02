# MlOps-CyberIntelligence

![Status](https://img.shields.io/badge/Status-RUNNING-success)
![Python](https://img.shields.io/badge/Python-3.10-blue)
![Docker](https://img.shields.io/badge/Docker-Enabled-blue)
![MLflow](https://img.shields.io/badge/MLflow-Tracking-blue)
![Dagster](https://img.shields.io/badge/Dagster-Orchestration-blue)
![dbt](https://img.shields.io/badge/dbt-Transformations-orange)
![Redpanda](https://img.shields.io/badge/Redpanda-Streaming-red)

## Overview
An end-to-end real-time cybersecurity MLOps platform for network intrusion detection. The platform processes the CICIDS2017 dataset, streaming network logs through Redpanda, orchestrating tasks with Dagster, transforming data with dbt, and training machine learning models tracked by MLflow.

## Architecture

```text
[Raw CSVs] 
    |
(Quality Gate 1: Raw Data)
    v
[Producer] -> [Redpanda: network-logs-raw] 
    |
    v
[Cleaner] -> [Redpanda: network-logs-clean]
    |
(Quality Gate 2: Cleaned Data)
    |
    +-----> [Model Training (Multi-Model CV -> MLflow)]
    |
    v
[Inference] -> [Redpanda: app-errors]
    |
(Quality Gate 3: Inference Output)
```

## Services & Ports
Deployed via Docker Compose on a shared server via Komodo orchestrator.

| Service | Port | Description |
|---------|------|-------------|
| **Dagster** | `4301` | Orchestration UI |
| **MLflow** | `4302` | Model tracking & registry UI |
| **Redpanda Admin** | `4303` | Admin API |
| **Redpanda Proxy** | `4304` | Schema registry / HTTP proxy |
| **Redpanda Kafka** | `4305` | Kafka-compatible broker |
| **Redpanda Internal**| `4306` | Internal RPC |

## Quick Start
1. Clone the repository.
2. Run `docker compose up --build -d`
3. Access Dagster UI at `http://localhost:4301`
4. Access MLflow UI at `http://localhost:4302`

## ML Pipeline
We employ a robust multi-model comparison pipeline:
- **Candidates:** RandomForest, ExtraTrees, GradientBoosting, LogisticRegression, SVC.
- **Selection:** 5-Fold Stratified CV on F1 score.
- **Anti-Leakage:** Strict zero-leakage guarantees. Train/test split before preprocessing, scaler fit only on training data, evaluation done exactly once on a 20% held-out test set.
- **Tracking:** Each candidate model is logged as an MLflow child run for easy UI comparison.

## Project Structure
```
MlOps-CyberIntelligence/
├── app/               # Future API/Web interface
├── data/              # Raw, processed, and exported data
├── dbt_project/       # dbt models with DuckDB
├── src/               # Source code modules
│   ├── ingestion/     # Data download scripts
│   ├── ml/            # Training, evaluation, prediction pipelines
│   ├── orchestration/ # Dagster assets and jobs
│   ├── quality/       # Data quality validation gates
│   └── streaming/     # Kafka producers, cleaners, consumers
├── tests/             # Pytest unit and integration tests
├── Data Analyse/      # EDA Jupyter notebooks
└── docker-compose.yml # Service definitions
```

## CI/CD
A GitHub Actions workflow is triggered on push to `master`, which securely sends an HMAC-SHA256 signed payload to the Komodo orchestrator webhook for automated deployment.
