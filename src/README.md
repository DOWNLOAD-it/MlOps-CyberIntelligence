# Source Modules (`src/`)

This directory contains the core logic for data orchestration, streaming, data quality, and machine learning.

## Modules

- **`ingestion/`**: Scripts for downloading and preparing raw datasets (e.g., fetching CICIDS2017 from Google Drive).
- **`orchestration/`**: Dagster definitions, assets, sensors, and schedules for automating the pipeline.
- **`streaming/`**: Redpanda/Kafka integration. Includes producers to stream CSV data, cleaners for real-time data normalization, and inference scripts to detect anomalies.
- **`quality/`**: Data quality gates to ensure data integrity before and after processing.
- **`ml/`**: The complete machine learning pipeline, featuring a multi-model evaluation framework, feature extraction, and MLflow logging.

## Technology Stack
- **Dagster**: Orchestration
- **Redpanda**: Streaming (Kafka-compatible)
- **Scikit-Learn**: Machine Learning
- **MLflow**: Experiment tracking and model registry
