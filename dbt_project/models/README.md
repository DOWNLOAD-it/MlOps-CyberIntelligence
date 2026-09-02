# dbt Project — CICIDS2017 Transformations

Transforms raw network log data into clean analytical models using dbt with DuckDB.

## Structure

`
dbt_project/
├── models/
│   └── staging/
│       ├── stg_network_logs.sql   # Staging model for raw network logs
│       └── schema.yml             # Column definitions and data tests
├── dbt_project.yml                # Project configuration
└── profiles.yml                   # Connection profile (DuckDB)
`

## Running dbt

`ash
dbt run       # Run all models
dbt test      # Run all data quality tests
dbt docs serve  # Launch documentation server
`
"@ | Set-Content -Encoding UTF8 "d:\workspace\master work\MLOps\MLSecOps-Platform\dbt_project\README.md"

# dbt_project/models/
@"
# dbt Models

Contains all dbt transformation models organized by layer.

## Layers
- **staging/** — Raw source data cleaned and typed, one model per source table.
