# Ingestion Module

Handles downloading and initially preparing raw CICIDS2017 network traffic data.

## Key Files
- **`download_data.py`**: Automates downloading raw datasets from external sources (e.g., Google Drive via `gdown`) into the `data/raw/` directory.

The ingestion process is typically orchestrated as the first step in the Dagster pipeline.
