# Orchestration Module — Dagster

Defines the Dagster assets, jobs, and sensors that orchestrate the full
MLSecOps pipeline from data ingestion to ML training.

## Key Files
| File | Description |
|------|-------------|
| definitions.py | Dagster Definitions object — registers all assets and jobs |
| ssets.py | Asset definitions for each pipeline stage |

## Pipeline Flow
`
Raw Data → Ingestion → Streaming/Cleaning → dbt Transformation → ML Training → MLflow
`
"@ | Set-Content -Encoding UTF8 "d:\workspace\master work\MLOps\MLSecOps-Platform\src\orchestration\README.md"

# src/quality/
@"
# Data Quality Module

Validates cleaned network log records before they enter the ML training pipeline.

## Checks Performed
- Column completeness (no missing required fields)
- Value range validation (e.g. no negative packet lengths)
- Label consistency (is_attack must be 0 or 1)

## Key Files
| File | Description |
|------|-------------|
| data_quality.py | Quality check functions and validation logic |
