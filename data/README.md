# Data Directory

This directory holds all data used by the MLSecOps-Platform. We use the **CICIDS2017 Network Traffic Logs** dataset for intrusion detection.

## Structure

- **`raw/`**: The original, unmodified CSV files downloaded from the source. (Git-ignored)
- **`processed/`**: Intermediate files generated during pipeline execution. (Git-ignored)
- **`exports/`**: Final, cleaned output files (like `.jsonl`) ready for ML training.

**Dataset Download:** [Google Drive Raw Datasets](https://drive.google.com/drive/folders/11Pv-TauVhMHxH5Th3SaKvvU9HLuYL1rC)
