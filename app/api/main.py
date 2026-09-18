from __future__ import annotations
import os
import json
import time
import requests
import psycopg2
import psycopg2.extras
import mlflow
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from app.api.schemas import NetworkRecord, PredictionResponse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MLSecOps API", description="API for Network Threat Detection")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = None
scaler = None


def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.environ.get('POSTGRES_HOST', 'soc_postgres'),
            port=os.environ.get('POSTGRES_PORT', '5432'),
            user=os.environ.get('POSTGRES_USER', 'mlsecops'),
            password=os.environ.get('POSTGRES_PASSWORD', 'supersecret'),
            dbname=os.environ.get('POSTGRES_DB', 'soc_alerts')
        )
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        return None


def init_db():
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    attack_type VARCHAR(100),
                    destination_port INT,
                    flow_duration INT,
                    confidence FLOAT
                )
                """)
            conn.commit()
            logger.info("Alerts table initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
        finally:
            conn.close()


current_model_version = None


def get_or_load_model():
    global model, scaler, current_model_version
    try:
        from mlflow.tracking import MlflowClient
        client = MlflowClient(tracking_uri=os.environ.get('MLFLOW_TRACKING_URI', 'http://mlflow:5000'))
        versions = client.get_latest_versions("network-anomaly-detector", stages=["Production"])
        if not versions:
            versions = client.get_latest_versions("network-anomaly-detector")
        if versions:
            latest_version = versions[0].version
            if current_model_version != latest_version:
                logger.info(f"New model version {latest_version} detected. Loading...")
                from src.ml.predict import load_model
                loaded_model, loaded_scaler = load_model()
                if loaded_model is not None:
                    model, scaler = loaded_model, loaded_scaler
                    current_model_version = latest_version
                    logger.info(f"ML model version {latest_version} loaded.")
    except Exception as e:
        logger.error(f"Error checking MLflow model version: {e}")

    if model is None:
        try:
            from src.ml.predict import load_model
            loaded_model, loaded_scaler = load_model()
            if loaded_model is not None:
                model, scaler = loaded_model, loaded_scaler
                logger.info("ML model loaded (fallback).")
        except Exception as e:
            logger.error(f"Error loading model fallback: {e}")

    return model, scaler


@app.on_event("startup")
def load_ml_model():
    global model, scaler
    init_db()
    try:
        from src.ml.predict import load_model
        model, scaler = load_model()
        if model is not None:
            logger.info("ML model loaded successfully.")
        else:
            logger.warning("ML model not found yet. Will auto-load once trained via Dagster.")
    except Exception as e:
        logger.error(f"Failed to load ML model on startup: {e}")


@app.get("/health")
def health_check():
    m, _ = get_or_load_model()
    return {"status": "ok", "model_loaded": m is not None}


@app.post("/api/v1/reload-model")
def reload_model_endpoint():
    global model, scaler
    from src.ml.predict import load_model
    model, scaler = load_model()
    if model is None:
        raise HTTPException(status_code=404, detail="Model artifacts not found. Run training in Dagster first.")
    return {"status": "success", "message": "Model reloaded successfully."}


@app.post("/api/v1/predict", response_model=PredictionResponse)
def predict_endpoint(record: NetworkRecord):
    m, s = get_or_load_model()
    if m is None:
        raise HTTPException(status_code=503, detail="Model not trained yet. Launch the Dagster pipeline first.")
    try:
        from src.ml.predict import predict
        data_dict = record.dict()
        is_attack, score = predict(data_dict, m, s)
        return PredictionResponse(
            is_attack=is_attack,
            confidence=score,
            attack_type="Anomaly" if is_attack else "Benign"
        )
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/predict_batch", response_model=List[PredictionResponse])
def predict_batch(records: List[NetworkRecord]):
    m, s = get_or_load_model()
    if m is None:
        raise HTTPException(status_code=503, detail="Model not trained yet. Launch the Dagster pipeline first.")
    responses = []
    from src.ml.predict import predict
    for record in records:
        try:
            is_attack, score = predict(record.dict(), model, scaler)
            responses.append(PredictionResponse(
                is_attack=is_attack,
                confidence=score,
                attack_type="Anomaly" if is_attack else "Benign"
            ))
        except Exception:
            responses.append(PredictionResponse(is_attack=False, confidence=0.0, attack_type="Error"))
    return responses


@app.get("/api/v1/alerts")
def get_alerts(
    limit: int = Query(100),
    offset: int = Query(0),
    attack_type: Optional[str] = Query(None),
    min_confidence: float = Query(0.0)
):
    conn = get_db_connection()
    if not conn:
        return []
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            query = "SELECT id, timestamp, attack_type, destination_port, flow_duration, confidence FROM alerts WHERE confidence >= %s"
            params: list = [min_confidence]
            if attack_type:
                query += " AND attack_type = %s"
                params.append(attack_type)
            query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            cur.execute(query, tuple(params))
            results = cur.fetchall()
            return [dict(r) for r in results]
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        return []
    finally:
        conn.close()


@app.get("/api/v1/alerts/stats")
def get_alerts_stats():
    conn = get_db_connection()
    empty: Dict[str, Any] = {
        "total_alerts": 0, "alerts_24h": 0, "by_type": {},
        "by_hour": [], "avg_confidence": 0.0, "top_ports": []
    }
    if not conn:
        logger.warning("Database connection failed, returning default stats.")
        return empty
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            stats: Dict[str, Any] = {}
            cur.execute("SELECT COUNT(*) as count FROM alerts")
            stats['total_alerts'] = cur.fetchone()['count']
            cur.execute("SELECT COUNT(*) as count FROM alerts WHERE timestamp >= NOW() - INTERVAL '24 HOURS'")
            stats['alerts_24h'] = cur.fetchone()['count']
            cur.execute(
                "SELECT attack_type, COUNT(*) as count FROM alerts "
                "GROUP BY attack_type ORDER BY count DESC LIMIT 10"
            )
            stats['by_type'] = {r['attack_type']: r['count'] for r in cur.fetchall()}
            cur.execute(
                "SELECT TO_CHAR(DATE_TRUNC('hour', timestamp), 'YYYY-MM-DD HH24:00') as hour, "
                "COUNT(*) as count FROM alerts "
                "WHERE timestamp >= NOW() - INTERVAL '24 HOURS' "
                "GROUP BY DATE_TRUNC('hour', timestamp) ORDER BY hour"
            )
            stats['by_hour'] = [{'hour': r['hour'], 'count': r['count']} for r in cur.fetchall()]
            cur.execute("SELECT AVG(confidence) as avg FROM alerts")
            avg_conf = cur.fetchone()['avg']
            stats['avg_confidence'] = float(avg_conf) if avg_conf else 0.0
            cur.execute(
                "SELECT destination_port as port, COUNT(*) as count FROM alerts "
                "GROUP BY destination_port ORDER BY count DESC LIMIT 10"
            )
            stats['top_ports'] = [{'port': r['port'], 'count': r['count']} for r in cur.fetchall()]
            return stats
    except Exception as e:
        logger.error(f"Error fetching alerts stats: {e}")
        return empty
    finally:
        conn.close()


@app.get("/api/v1/realtime/latest")
def realtime_latest(
    since_id: int = Query(0, description="Return only alerts with id > since_id"),
    limit: int = Query(30, description="Max rows to return")
):
    """Polling endpoint — returns newest alerts since a given ID.
    The webapp polls this every ~2.5 seconds to simulate a live feed.
    """
    conn = get_db_connection()
    if not conn:
        return {"alerts": [], "last_id": since_id}
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, timestamp::text, attack_type, destination_port, flow_duration, confidence "
                "FROM alerts WHERE id > %s ORDER BY id ASC LIMIT %s",
                (since_id, limit)
            )
            rows = cur.fetchall()
            alerts = [dict(r) for r in rows]
            last_id = alerts[-1]['id'] if alerts else since_id
            return {"alerts": alerts, "last_id": last_id}
    except Exception as e:
        logger.error(f"Error fetching realtime latest: {e}")
        return {"alerts": [], "last_id": since_id}
    finally:
        conn.close()


@app.get("/api/v1/realtime/stats")
def realtime_stats():
    """Returns rolling-window stats for live dashboard widgets."""
    conn = get_db_connection()
    empty: Dict[str, Any] = {
        "rate_per_minute": 0.0,
        "total_last_hour": 0,
        "attacks_last_hour": 0,
        "benign_last_hour": 0,
        "top_attack_type": "N/A",
        "avg_confidence_last_hour": 0.0,
        "by_type_last_hour": {},
        "by_minute": [],
    }
    if not conn:
        return empty
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT COUNT(*) as total, "
                "SUM(CASE WHEN LOWER(attack_type) NOT IN ('benign', 'normal') THEN 1 ELSE 0 END) as attacks, "
                "AVG(confidence) as avg_conf "
                "FROM alerts WHERE timestamp >= NOW() - INTERVAL '1 HOUR'"
            )
            row = cur.fetchone()
            total = int(row['total'] or 0)
            attacks = int(row['attacks'] or 0)
            avg_conf = float(row['avg_conf'] or 0.0)

            cur.execute(
                "SELECT COUNT(*) as cnt FROM alerts "
                "WHERE timestamp >= NOW() - INTERVAL '5 MINUTES'"
            )
            last5 = int(cur.fetchone()['cnt'] or 0)
            rate = round(last5 / 5.0, 2)

            cur.execute(
                "SELECT attack_type, COUNT(*) as count FROM alerts "
                "WHERE timestamp >= NOW() - INTERVAL '1 HOUR' "
                "GROUP BY attack_type ORDER BY count DESC LIMIT 10"
            )
            by_type = {r['attack_type']: int(r['count']) for r in cur.fetchall()}
            top_type = list(by_type.keys())[0] if by_type else "N/A"

            cur.execute(
                "SELECT TO_CHAR(DATE_TRUNC('minute', timestamp), 'HH24:MI') as minute, "
                "COUNT(*) as count FROM alerts "
                "WHERE timestamp >= NOW() - INTERVAL '30 MINUTES' "
                "GROUP BY DATE_TRUNC('minute', timestamp) ORDER BY minute"
            )
            by_minute = [{'minute': r['minute'], 'count': int(r['count'])} for r in cur.fetchall()]

            return {
                "rate_per_minute": rate,
                "total_last_hour": total,
                "attacks_last_hour": attacks,
                "benign_last_hour": total - attacks,
                "top_attack_type": top_type,
                "avg_confidence_last_hour": round(avg_conf, 4),
                "by_type_last_hour": by_type,
                "by_minute": by_minute,
            }
    except Exception as e:
        logger.error(f"Error in realtime_stats: {e}")
        return empty
    finally:
        conn.close()


@app.get("/api/v1/system/health")
def system_health():
    services = []

    # 1. API (self)
    services.append({"name": "api", "status": "healthy", "latency_ms": 0, "detail": "API running"})

    # 2. MLflow — /health endpoint exists in MLflow 2.x
    mlflow_base = os.environ.get('MLFLOW_TRACKING_URI', 'http://mlflow:5000')
    try:
        t0 = time.time()
        resp = requests.get(f"{mlflow_base}/health", timeout=3)
        lat = int((time.time() - t0) * 1000)
        services.append({
            "name": "mlflow",
            "status": "healthy" if resp.status_code == 200 else "degraded",
            "latency_ms": lat,
            "detail": f"HTTP {resp.status_code}"
        })
    except Exception as e:
        services.append({"name": "mlflow", "status": "unhealthy", "latency_ms": 0, "detail": str(e)[:80]})

    # 3. PostgreSQL
    try:
        t0 = time.time()
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            conn.close()
            lat = int((time.time() - t0) * 1000)
            services.append({"name": "postgres", "status": "healthy", "latency_ms": lat, "detail": "Connected"})
        else:
            services.append({"name": "postgres", "status": "unhealthy", "latency_ms": 0, "detail": "Connection failed"})
    except Exception as e:
        services.append({"name": "postgres", "status": "unhealthy", "latency_ms": 0, "detail": str(e)[:80]})

    # 4. Redpanda admin API
    redpanda_admin = os.environ.get("REDPANDA_ADMIN_URL", "http://redpanda:8081")
    try:
        t0 = time.time()
        resp = requests.get(f"{redpanda_admin}/v1/cluster/health", timeout=3)
        lat = int((time.time() - t0) * 1000)
        services.append({
            "name": "redpanda",
            "status": "healthy" if resp.status_code == 200 else "degraded",
            "latency_ms": lat,
            "detail": f"HTTP {resp.status_code}"
        })
    except Exception as e:
        services.append({"name": "redpanda", "status": "unhealthy", "latency_ms": 0, "detail": str(e)[:80]})

    # 5. Dagster — root path returns 200 HTML on the webserver
    dagster_host = os.environ.get("DAGSTER_HOST", "http://dagster_orchestrator:3000")
    try:
        t0 = time.time()
        resp = requests.get(f"{dagster_host}/", timeout=3)
        lat = int((time.time() - t0) * 1000)
        ok = resp.status_code in (200, 301, 302)
        services.append({
            "name": "dagster",
            "status": "healthy" if ok else "degraded",
            "latency_ms": lat,
            "detail": f"HTTP {resp.status_code}"
        })
    except Exception as e:
        services.append({"name": "dagster", "status": "unhealthy", "latency_ms": 0, "detail": str(e)[:80]})

    return {"services": services}


@app.get("/api/v1/model/info")
def model_info():
    default_info: Dict[str, Any] = {
        "model_name": "network-anomaly-detector",
        "model_version": "N/A",
        "f1_score": 0.0,
        "precision": 0.0,
        "recall": 0.0,
        "accuracy": 0.0,
        "roc_auc": 0.0,
        "training_date": None,
        "feature_count": 0,
        "best_model": "N/A",
        "n_train": 0,
        "n_test": 0,
        "cv_folds": 0,
        "status": "not_trained"
    }
    try:
        from mlflow.tracking import MlflowClient
        mlflow_uri = os.environ.get('MLFLOW_TRACKING_URI', 'http://mlflow:5000')
        client = MlflowClient(tracking_uri=mlflow_uri)

        # Look up registered model versions via registry (avoids child-run confusion)
        try:
            versions = client.get_latest_versions("network-anomaly-detector", stages=["Production"])
        except Exception:
            versions = []
        if not versions:
            try:
                versions = client.get_latest_versions("network-anomaly-detector")
            except Exception:
                versions = []
        if not versions:
            logger.warning("No registered model versions found.")
            return default_info

        latest = versions[0]
        run_id = latest.run_id

        # Fetch the actual parent training run to get test metrics
        run = client.get_run(run_id)
        metrics = run.data.metrics
        params = run.data.params

        training_date = None
        if latest.creation_timestamp:
            from datetime import datetime
            training_date = datetime.utcfromtimestamp(latest.creation_timestamp / 1000).isoformat()

        return {
            "model_name": "network-anomaly-detector",
            "model_version": str(latest.version),
            "f1_score": float(metrics.get("test_f1", 0.0)),
            "precision": float(metrics.get("test_precision", 0.0)),
            "recall": float(metrics.get("test_recall", 0.0)),
            "accuracy": float(metrics.get("test_accuracy", 0.0)),
            "roc_auc": float(metrics.get("test_roc_auc", 0.0)),
            "training_date": training_date,
            "feature_count": int(float(params.get("n_features", 78))),
            "best_model": params.get("best_model", "N/A"),
            "n_train": int(float(params.get("n_train", 0))),
            "n_test": int(float(params.get("n_test", 0))),
            "cv_folds": int(float(params.get("cv_folds", 5))),
            "status": "trained"
        }
    except Exception as e:
        logger.error(f"Error fetching model info: {e}")
        return default_info