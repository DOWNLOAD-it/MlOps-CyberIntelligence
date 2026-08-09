Cybersecurity Threat Detection MLOps Platform

An end-to-end Machine Learning Operations (MLOps) platform for real-time cybersecurity log processing, data transformation, and alerting. The repository uses Dagster for orchestration, Redpanda for Kafka streaming, and dbt with DuckDB for batch transformation.

This platform is built to:
- ingest raw network logs from `data/raw/`
- stream events into Kafka topics `raw-logs`, `cleaned-logs`, and `app-errors`
- apply cleaning and simple ML inference in a Dagster asset pipeline
- materialize output data and save inspection exports under `data/exports/`
- run dbt models against DuckDB at `dbt_project/target/duck.db`

## 🚀 What the pipeline does

1. `src/streaming/producer.py` reads CSV files from `data/raw/` and publishes records to Redpanda topic `raw-logs`.
2. `src/streaming/cleaner.py` consumes `raw-logs`, cleans records, republishes them to `cleaned-logs`, and writes `data/exports/cleaned_logs.jsonl`.
3. `src/streaming/inference.py` consumes `cleaned-logs`, runs simple anomaly inference, publishes alerts to `app-errors`, and writes `data/exports/app_errors.jsonl`.
4. `dbt` runs SQL models from `dbt_project/models/` against DuckDB and stores results in `dbt_project/target/duck.db`.
5. `src/orchestration/assets.py` defines Dagster assets that orchestrate producer, cleaner, and inference steps.

## 🔧 Services and how to run them

### Start Redpanda

```bash
cd /home/houssame/my_project/MLSecOps-Platform
docker compose up --build redpanda
```

Redpanda provides Kafka brokers on `localhost:9092` and the broker is used by the streaming assets.

### Start Dagster UI and daemon

```bash
docker compose up --build dagster dagster-daemon
```

- `dagster` exposes the UI at `http://localhost:3000`
- `dagster-daemon` runs sensors and schedules
- Both containers share `PYTHONPATH=/app` and `DAGSTER_HOME=/app/dagster_home`

### Run dbt

```bash
docker compose run --rm dbt
```

This executes `dbt run --profiles-dir /app/dbt_project` inside the `dbt` service. The DuckDB database file is written to:

```bash
dbt_project/target/duck.db
```

### Run the full stack

```bash
docker compose up --build
```

This will start Redpanda, Dagster, Dagster daemon, and dbt together. If you want manual control, start Redpanda first and then the Dagster services.

## 📁 Where processed data is stored

- Raw source CSV files: `data/raw/`
- Cleaned streaming export: `data/exports/cleaned_logs.jsonl`
- Anomaly alert export: `data/exports/app_errors.jsonl`
- dbt DuckDB target: `dbt_project/target/duck.db`

## 🧪 Manual test commands

### Ingest raw CSV files manually

```bash
docker compose exec dagster python src/streaming/producer.py
```

### Run the cleaner manually

```bash
docker compose exec dagster python src/streaming/cleaner.py
```

### Run inference manually

```bash
docker compose exec dagster python src/streaming/inference.py
```

### Run dbt tests

```bash
docker compose exec dbt bash -c "cd /app/dbt_project && dbt test --profiles-dir /app/dbt_project"
```

### Inspect exported data files

```bash
ls -la data/exports
head -n 5 data/exports/cleaned_logs.jsonl
head -n 5 data/exports/app_errors.jsonl
```

## 🔗 Integrating with test and data-quality tools

This repository is designed for easy integration with tools like:

- **dbt tests**: add schema tests and data tests in `dbt_project/models/` and run `dbt test`
- **Great Expectations**: add expectation suites for `data/raw/` and `data/exports/`
- **kafka-console-consumer / rpk / kcat**: inspect Kafka topics directly
- **Prometheus / Grafana**: instrument Dagster and streaming services for metrics
- **MLflow**: track model versions and performance metrics if you add a model logging layer

### Example data-quality workflow

1. run ingestion and cleaning
2. validate `data/exports/cleaned_logs.jsonl` with a Great Expectations suite
3. run `dbt test` for schema and freshness checks
4. monitor anomalies in `data/exports/app_errors.jsonl`

## 🧩 Notes

- `data/raw/` is the source ingestion folder. Add new CSV files there for the streaming sensor.
- `data/exports/` is now used to capture the latest cleaned and anomaly output.
- The pipeline is currently focused on stream simulation and simple rule-based/anomaly inference.
- For a production-ready deployment, add proper Kafka topic management, persistent storage, and a real ML model.

## 📦 Project structure

```bash
.
├── data/
│   ├── exports/             # Processed streaming exports (cleaned, anomalies)
│   └── raw/                 # Raw input CSV files
├── dbt_project/
│   ├── models/              # dbt SQL models
│   ├── target/              # DuckDB artifacts and compiled outputs
│   └── profiles.yml         # dbt DuckDB profile
├── src/
│   ├── ingestion/           # Dataset download and ingestion helpers
│   ├── orchestration/       # Dagster assets and definitions
│   ├── streaming/           # Kafka producer/consumer processing logic
│   └── README.md            # Local developer notes
├── docker-compose.yml       # Service orchestration
├── requirements.txt         # Python dependencies
└── README.md
```
