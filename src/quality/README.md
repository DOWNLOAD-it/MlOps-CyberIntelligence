# Data Quality Module

Ensures data integrity and validates schemas before data passes between pipeline stages.

## Validation Gates

- **Raw Gate**: Checks raw CSV structure and completeness before entering the streaming pipeline.
- **Cleaned Gate**: Validates sanitized records (e.g., correct IP formats, valid port numbers) before ML training.
- **Inference Gate**: Verifies the structure and confidence scores of anomaly predictions.

## Key Files
- **`data_quality.py`**: Contains the quality check functions and validation logic.
