# dbt Project

Transforms raw network log data into clean analytical models using **dbt** with **DuckDB**.

## Structure

```
dbt_project/
├── models/
│   └── staging/
│       ├── stg_network_logs.sql   # Staging model
│       └── schema.yml             # Column definitions and tests
├── dbt_project.yml                # Project configuration
└── profiles.yml                   # Connection profile (DuckDB)
```

## Common Commands

```bash
dbt run         # Run all models
dbt test        # Run all data quality tests
dbt docs serve  # Launch documentation server
```
