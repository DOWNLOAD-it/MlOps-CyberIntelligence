# Orchestration Module

Defines the **Dagster** assets, jobs, and sensors that orchestrate the full MLSecOps pipeline.

## Key Files

| File | Description |
|------|-------------|
| `definitions.py` | The Dagster `Definitions` object. Registers all assets, jobs, and sensors for the platform. |
| `assets.py` | Defines individual pipeline stages (ingestion, streaming, training) as software-defined assets. |

## Pipeline Flow

```text
Raw Data -> Ingestion -> Streaming/Cleaning -> dbt Transformation -> ML Training -> MLflow Registry
```
