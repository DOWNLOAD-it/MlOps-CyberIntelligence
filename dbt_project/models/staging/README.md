# Staging Models

First transformation layer. Reads raw network logs and applies column renaming, type casting, and basic filtering to prepare data for downstream analytics or ML.

## Models
| Model | Description |
|-------|-------------|
| `stg_network_logs.sql` | Cleaned and strongly-typed view of raw CICIDS2017 network flows. |
