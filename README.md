# MlOps-CyberIntelligence

An end-to-end **MLSecOps platform** for network intrusion detection using the [CICIDS2017](https://www.unb.ca/cic/datasets/ids-2017.html) dataset.
Combines real-time streaming, automated ML training, and live SOC dashboards — fully containerised and deployable on any server.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                              │
│          CICIDS2017 CSV Files  (data/raw/*.csv)                  │
└─────────────────────────┬────────────────────────────────────────┘
                          │  Dagster Asset: streaming_ingestion_asset
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│                       REDPANDA / KAFKA                           │
│              Topic: raw-logs  (published by Producer)            │
└─────────────────────────┬────────────────────────────────────────┘
                          │  Dagster Asset: streaming_cleaning_asset
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│                    dbt + DuckDB Transform                        │
│           Topic: cleaned-logs | Export: cleaned_logs.jsonl       │
└──────────┬──────────────────────────────┬────────────────────────┘
           │ model_training_asset          │ model_inference_asset
           ▼                              ▼
┌─────────────────────┐      ┌─────────────────────────────────────┐
│  MLflow Model       │      │  Alert System                       │
│  Registry           │      │  Topic: app-errors → PostgreSQL     │
│  (best model saved) │      │  Grafana SOC Dashboard              │
└─────────────────────┘      └─────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI  ←→  Next.js WebApp  (live prediction endpoint)        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Services & Ports

| Service        | Internal Port | Host Port | URL (local / SSH tunnel)       |
|----------------|:------------:|:---------:|--------------------------------|
| Dagster UI     | 3000         | **4401**  | `http://localhost:4401`        |
| MLflow UI      | 5000         | **4402**  | `http://localhost:4402`        |
| Redpanda Admin | 8081         | **4403**  | `http://localhost:4403`        |
| Redpanda Proxy | 8082         | **4404**  | `http://localhost:4404`        |
| Redpanda Kafka | 9092         | **4405**  | `localhost:4405`               |
| Redpanda Int.  | 29092        | **4406**  | internal only                  |
| Grafana        | 3000         | **4407**  | `http://localhost:4407`        |
| FastAPI        | 8000         | **4408**  | `http://localhost:4408`        |
| Next.js WebApp | 3000         | **4409**  | `http://localhost:4409`        |
| PostgreSQL     | 5432         | —         | internal only (no host port)   |

---

## ML Pipeline

The training pipeline runs **zero-leakage** multi-model selection:

1. **80/20 stratified split** performed before any preprocessing.
2. **5-Fold Stratified CV** (F1 score) run on 4 candidate models — all within the training fold only:
   - `RandomForestClassifier`
   - `ExtraTreesClassifier`
   - `GradientBoostingClassifier`
   - `LogisticRegression`
3. **StandardScaler** fitted on training data only, then applied to test set.
4. **Best model** (by CV F1) evaluated **exactly once** on the held-out test set.
5. Best model registered in the **MLflow Model Registry** as `network-anomaly-detector`.

---

## Project Structure

```
MLSecOps-Platform/
├── app/
│   ├── api/                  # FastAPI inference backend
│   ├── webapp/               # Next.js React frontend
│   ├── Dockerfile.api
│   └── Dockerfile.webapp
├── data/
│   ├── raw/                  # CICIDS2017 CSV files (gitignored)
│   ├── exports/              # cleaned_logs.jsonl, app_errors.jsonl
│   └── processed/            # intermediate files (gitignored)
├── dbt_project/              # dbt models with DuckDB
├── grafana/                  # Grafana provisioning & dashboards
├── src/
│   ├── ingestion/            # download_data.py
│   ├── ml/                   # train.py, features.py, evaluate.py
│   ├── orchestration/        # Dagster assets.py + definitions.py
│   ├── quality/              # Data quality validation
│   └── streaming/            # producer.py, cleaner.py, inference.py
├── tests/                    # pytest test suite
├── docker-compose.yml
├── expose_endpoints.sh       # Cloudflare tunnel script (run on server)
├── forward_ports.ps1         # SSH tunnel script (run on local Windows)
├── requirements.txt
└── .env.example
```

---

## Prerequisites

| Tool           | Minimum Version | Notes                      |
|----------------|-----------------|----------------------------|
| Docker         | 24+             | With Compose v2 plugin     |
| Docker Compose | 2.20+           | `docker compose` (no dash) |
| Python         | 3.10+           | For local development only |
| Git            | any             |                            |

---

## Deployment A — Local Machine

Use this path when running everything on your own laptop/workstation.

### 1. Clone the repository

```bash
git clone https://github.com/DOWNLOAD-it/MlOps-CyberIntelligence.git
cd MlOps-CyberIntelligence
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env if you need custom ports or credentials
```

### 3. Start all services

```bash
docker compose up -d
```

First-time startup will **build the images** automatically (takes ~5 minutes).
Subsequent starts are instant.

### 4. Download the dataset

```bash
# Run the download script inside the Dagster container
docker compose exec dagster python src/ingestion/download_data.py
```

The 8 CICIDS2017 CSV files will be saved to `data/raw/`.

> **Alternative (local Python):**
> ```bash
> pip install gdown
> python src/ingestion/download_data.py
> ```

### 5. Verify all containers are running

```bash
docker compose ps
```

Expected output:

```
NAME                   STATUS   PORTS
dagster_orchestrator   Up       0.0.0.0:4401->3000/tcp
mlflow_server          Up       0.0.0.0:4402->5000/tcp
redpanda               Up       0.0.0.0:4403-4406->...
soc_grafana            Up       0.0.0.0:4407->3000/tcp
mlsecops_api           Up       0.0.0.0:4408->8000/tcp
mlsecops_webapp        Up       0.0.0.0:4409->3000/tcp
soc_postgres           Up       (internal only)
dagster_daemon         Up
```

### 6. Access the UIs

| App      | URL                              |
|----------|----------------------------------|
| Dagster  | http://localhost:4401            |
| MLflow   | http://localhost:4402            |
| Grafana  | http://localhost:4407 *(admin/admin)* |
| API Docs | http://localhost:4408/docs       |
| WebApp   | http://localhost:4409            |

### 7. Run the pipeline

**Option A – Via Dagster UI (recommended):**
1. Go to http://localhost:4401
2. Click **Jobs** → `full_mlsecops_pipeline_job` → **Launchpad** → **Launch Run**

**Option B – Via terminal:**

```bash
docker compose exec dagster dagster job execute \
  -f src/orchestration/definitions.py \
  -j full_mlsecops_pipeline_job
```

**Available jobs:**

| Job name                     | What it does                                           |
|------------------------------|--------------------------------------------------------|
| `full_mlsecops_pipeline_job` | Full pipeline: ingest → clean → train → infer          |
| `realtime_mlsecops_job`      | Streaming only: ingest → clean → infer                 |
| `ml_training_job`            | ML training only (needs existing `cleaned_logs.jsonl`) |

### 8. Reload the model in the API after training

After the training job completes, trigger the API to load the new model without restarting:

```bash
curl -X POST http://localhost:4408/api/v1/reload-model
```

---

## Deployment B — Komodo Server (Remote / University)

Use this path when the code runs on a remote server managed via Komodo.

### 1. Push code — CI/CD auto-deploys to server

Every push to `master` triggers a GitHub Actions workflow which sends a webhook to Komodo, and Komodo redeploys the stack automatically.

```bash
git add .
git commit -m "feat: your change"
git push origin master
```

### 2. Access the Komodo dashboard

> **Komodo dashboard:** https://komodo.s3.fsbm.ma

From there you can:
- View container status under **Servers → vh3 → Containers**
- Open a **web terminal** into any container (click the container name → Terminal icon)

### 3. Download the dataset on the server

In the Komodo web terminal for the **`dagster_orchestrator`** container:

```bash
# Pull the latest code (if CI/CD hasn't done it yet)
git pull

# Download the 8 CICIDS2017 CSV files to data/raw/
python src/ingestion/download_data.py
```

> The script downloads files individually by Google Drive file ID to avoid rate-limiting.
> The clean Google Drive folder ID is: `11Pv-TauVhMHxH5Th3SaKvvU9HLuYL1rC`

### 4. Run the pipeline on the server

In the Komodo web terminal for **`dagster_orchestrator`**:

```bash
# Full end-to-end pipeline (ingest → clean → train → infer)
dagster job execute \
  -f src/orchestration/definitions.py \
  -j full_mlsecops_pipeline_job

# Streaming only (skip training)
dagster job execute \
  -f src/orchestration/definitions.py \
  -j realtime_mlsecops_job

# Training only (requires cleaned_logs.jsonl to already exist)
dagster job execute \
  -f src/orchestration/definitions.py \
  -j ml_training_job
```

### 5. Reload the model in the API after training

From inside **any container** on the same Docker network, use the container name (not `localhost`):

```bash
# From inside dagster_orchestrator:
curl http://mlsecops_api:8000/health
curl -X POST http://mlsecops_api:8000/api/v1/reload-model
```

### 6. Verify container port bindings (host terminal)

Run these on the **server host** (not inside a container):

```bash
docker ps --format "table {{.Names}}\t{{.Ports}}"
netstat -tuln | grep 440
```

---

## Accessing the UIs From Any Network (Firewall Bypass)

The university firewall blocks inbound connections on ports `44XX`.
Use one of these two methods to access the platform from outside the campus network.

---

### Method A — Cloudflare Quick Tunnels ✅ (Recommended)

Works from **any network** (home Wi-Fi, mobile hotspot, etc.) with **zero account setup**.

Run this **once** inside the `dagster_orchestrator` container terminal via Komodo:

```bash
bash expose_endpoints.sh
```

After ~10 seconds, the script prints 4 public HTTPS URLs:

```
==========================================
🎉 SUCCESS! Access your apps from ANY network:
==========================================
🟢 Dagster UI : https://random-words.trycloudflare.com
🟢 MLflow UI  : https://other-words.trycloudflare.com
🟢 FastAPI    : https://more-words.trycloudflare.com
🟢 WebApp     : https://yet-more.trycloudflare.com
==========================================
```

**Important notes:**
- URLs are random and change each time you run the script.
- Links stay active as long as the container keeps running.
- To stop all tunnels: `pkill cloudflared`
- To refresh after a restart: re-run `bash expose_endpoints.sh`

---

### Method B — SSH Local Port Forwarding

Use this if **SSH port 22 is reachable** from your network.

On your **local Windows machine**, open PowerShell:

```powershell
# Using the helper script:
.\forward_ports.ps1 -Username "your_ssh_username"

# Or manually:
ssh -N `
  -L 4401:localhost:4401 `
  -L 4402:localhost:4402 `
  -L 4407:localhost:4407 `
  -L 4408:localhost:4408 `
  -L 4409:localhost:4409 `
  your_username@41.250.197.226
```

Keep that terminal open. Then open `http://localhost:44XX` in your browser.

---

## Rebuilding Docker Images

After changes to a `Dockerfile` or `requirements.txt`:

```bash
# On the server host (not inside a container):
git pull
docker compose down
docker compose build --no-cache
docker compose up -d
```

> **No rebuild needed** for changes to `.py` files in `src/` or `app/api/` — they are mounted as volumes and take effect immediately.

---

## Running Tests Locally

```bash
# Install all dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_data_quality.py -v
```

---

## CI/CD Pipeline

Every push to `master`:
1. **GitHub Actions** runs the test suite.
2. On success, sends a webhook to **Komodo**.
3. **Komodo** pulls the latest code and restarts the stack on `vh3`.

---

## Environment Variables Reference

Copy `.env.example` to `.env` and adjust as needed.

| Variable                 | Default              | Description                                  |
|--------------------------|----------------------|----------------------------------------------|
| `DAGSTER_HOST_PORT`      | `4401`               | Host port for Dagster UI                     |
| `MLFLOW_HOST_PORT`       | `4402`               | Host port for MLflow UI                      |
| `REDPANDA_ADMIN_PORT`    | `4403`               | Host port for Redpanda Admin API             |
| `REDPANDA_PROXY_PORT`    | `4404`               | Host port for Redpanda HTTP Proxy            |
| `REDPANDA_KAFKA_PORT`    | `4405`               | Host port for Kafka external listener        |
| `REDPANDA_INTERNAL_PORT` | `4406`               | Host port for Kafka internal listener        |
| `GRAFANA_HOST_PORT`      | `4407`               | Host port for Grafana                        |
| `API_HOST_PORT`          | `4408`               | Host port for FastAPI                        |
| `WEBAPP_HOST_PORT`       | `4409`               | Host port for Next.js WebApp                 |
| `STREAM_MAX_RECORDS`     | `500000`             | Max records per pipeline run                 |
| `PRODUCER_BATCH_SIZE`    | `5000`               | Kafka producer batch size                    |
| `MLFLOW_TRACKING_URI`    | `http://mlflow:5000` | MLflow server URI (internal Docker network)  |
| `POSTGRES_USER`          | `mlsecops`           | PostgreSQL username                          |
| `POSTGRES_PASSWORD`      | `supersecret`        | PostgreSQL password — **change in prod!**    |
| `POSTGRES_DB`            | `soc_alerts`         | PostgreSQL database name                     |
| `ML_N_ESTIMATORS`        | `200`                | Number of trees for ensemble models          |
| `ML_RANDOM_STATE`        | `42`                 | Random seed for reproducibility              |

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `curl: Failed to connect to localhost` | You're inside a container — `localhost` is the container itself | Use the container name: `curl http://mlsecops_api:8000/health` |
| `KeyError: 'metrics'` in Dagster | `cleaned_logs.jsonl` is empty — no data was ingested | Re-run the full pipeline starting from ingestion |
| `ERR_CONNECTION_TIMED_OUT` on `44XX` ports | University firewall blocks inbound ports | Run `bash expose_endpoints.sh` for Cloudflare tunnels |
| Port shows `Missing external address` in Komodo | No external IP set in Komodo server settings | Normal — Docker binding `0.0.0.0` is correct |
| MLflow `404 Not Found` on model versions | No model has been registered yet | Run the training pipeline first |
| Dagster daemon `No heartbeat received` warning | Ephemeral code-server process shutdown | Normal — not a crash, the daemon is healthy |
| `bash expose_endpoints.sh` shows empty URLs | Cloudflared needs more time | Increase `sleep 10` to `sleep 20` in the script |

---

## Dataset

**CICIDS2017 — Canadian Institute for Cybersecurity Intrusion Detection Dataset 2017**

- 8 CSV files covering different attack categories (DoS, DDoS, Brute Force, Infiltration, Web Attacks, etc.)
- ~2.8 million network flow records with 78 features per record
- Google Drive folder: [`11Pv-TauVhMHxH5Th3SaKvvU9HLuYL1rC`](https://drive.google.com/drive/folders/11Pv-TauVhMHxH5Th3SaKvvU9HLuYL1rC)
- Downloaded automatically by `src/ingestion/download_data.py`

---

## License

[MIT](LICENSE)
