from __future__ import annotations
import os
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

# Allow CORS for the webapp
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
    
    # Check MLflow for new version
    try:
        from mlflow.tracking import MlflowClient
        client = MlflowClient(tracking_uri=os.environ.get('MLFLOW_TRACKING_URI', 'http://mlflow:5000'))
        
        versions = client.get_latest_versions("network-anomaly-detector", stages=["Production"])
        if not versions:
            versions = client.get_latest_versions("network-anomaly-detector")
            
        if versions:
            latest_version = versions[0].version
            if current_model_version != latest_version:
                logger.info(f"New model version {latest_version} detected in MLflow. Loading...")
                from src.ml.predict import load_model
                loaded_model, loaded_scaler = load_model()
                if loaded_model is not None:
                    model, scaler = loaded_model, loaded_scaler
                    current_model_version = latest_version
                    logger.info(f"ML model version {latest_version} dynamically loaded successfully.")
    except Exception as e:
        logger.error(f"Error checking MLflow model version: {e}")

    # Fallback if never loaded
    if model is None:
        try:
            from src.ml.predict import load_model
            loaded_model, loaded_scaler = load_model()
            if loaded_model is not None:
                model, scaler = loaded_model, loaded_scaler
                logger.info("ML model dynamically loaded successfully as fallback.")
        except Exception as e:
            logger.error(f"Error during dynamic model loading fallback: {e}")
            
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
            logger.warning("ML model not found yet. It will load automatically once trained via Dagster.")
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
        raise HTTPException(status_code=404, detail="Model artifacts not found yet. Run training in Dagster first.")
    return {"status": "success", "message": "Model reloaded successfully."}

@app.post("/api/v1/predict", response_model=PredictionResponse)
def predict_endpoint(record: NetworkRecord):
    m, s = get_or_load_model()
    if m is None:
        raise HTTPException(
            status_code=503, 
            detail="Model is not trained yet. Please launch the training pipeline in Dagster (http://komodo.s3.fsbm.ma:4301)."
        )
    
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
        raise HTTPException(
            status_code=503, 
            detail="Model is not trained yet. Please launch the training pipeline in Dagster (http://komodo.s3.fsbm.ma:4301)."
        )
        
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
        except Exception as e:
            responses.append(PredictionResponse(is_attack=False, confidence=0.0, attack_type="Error"))
            
    return responses

@app.get("/api/v1/alerts")
def get_alerts(limit: int = Query(100), offset: int = Query(0), attack_type: Optional[str] = Query(None), min_confidence: float = Query(0.0)):
    conn = get_db_connection()
    if not conn:
        logger.warning("Database connection failed, returning empty alerts list.")
        return []
        
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            query = "SELECT id, timestamp, attack_type, destination_port, flow_duration, confidence FROM alerts WHERE confidence >= %s"
            params = [min_confidence]
            
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
    if not conn:
        logger.warning("Database connection failed, returning default stats.")
        return {
            "total_alerts": 0,
            "alerts_24h": 0,
            "by_type": {},
            "by_hour": [],
            "avg_confidence": 0.0,
            "top_ports": []
        }
        
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            stats = {}
            
            cur.execute("SELECT COUNT(*) as count FROM alerts")
            stats['total_alerts'] = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as count FROM alerts WHERE timestamp >= NOW() - INTERVAL '24 HOURS'")
            stats['alerts_24h'] = cur.fetchone()['count']
            
            cur.execute("SELECT attack_type, COUNT(*) as count FROM alerts GROUP BY attack_type ORDER BY count DESC LIMIT 10")
            stats['by_type'] = {r['attack_type']: r['count'] for r in cur.fetchall()}
            
            cur.execute("SELECT TO_CHAR(DATE_TRUNC('hour', timestamp), 'YYYY-MM-DD HH24:00') as hour, COUNT(*) as count FROM alerts WHERE timestamp >= NOW() - INTERVAL '24 HOURS' GROUP BY DATE_TRUNC('hour', timestamp) ORDER BY hour")
            stats['by_hour'] = [{'hour': r['hour'], 'count': r['count']} for r in cur.fetchall()]
            
            cur.execute("SELECT AVG(confidence) as avg FROM alerts")
            avg_conf = cur.fetchone()['avg']
            stats['avg_confidence'] = float(avg_conf) if avg_conf else 0.0
            
            cur.execute("SELECT destination_port as port, COUNT(*) as count FROM alerts GROUP BY destination_port ORDER BY count DESC LIMIT 10")
            stats['top_ports'] = [{'port': r['port'], 'count': r['count']} for r in cur.fetchall()]
            
            return stats
    except Exception as e:
        logger.error(f"Error fetching alerts stats: {e}")
        return {
            "total_alerts": 0,
            "alerts_24h": 0,
            "by_type": {},
            "by_hour": [],
            "avg_confidence": 0.0,
            "top_ports": []
        }
    finally:
        conn.close()

@app.get("/api/v1/system/health")
def system_health():
    services = []
    
    # API
    services.append({"name": "api", "status": "healthy", "latency_ms": 0, "detail": "API is running"})
    
    # MLflow
    try:
        start_time = time.time()
        resp = requests.get("http://mlflow:5000/health", timeout=2)
        latency = int((time.time() - start_time) * 1000)
        services.append({"name": "mlflow", "status": "healthy" if resp.status_code == 200 else "degraded", "latency_ms": latency, "detail": f"Status {resp.status_code}"})
    except Exception as e:
        services.append({"name": "mlflow", "status": "unhealthy", "latency_ms": 0, "detail": str(e)})

    # Postgres
    try:
        start_time = time.time()
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            conn.close()
            latency = int((time.time() - start_time) * 1000)
            services.append({"name": "postgres", "status": "healthy", "latency_ms": latency, "detail": "Connected"})
        else:
            services.append({"name": "postgres", "status": "unhealthy", "latency_ms": 0, "detail": "Connection failed"})
    except Exception as e:
        services.append({"name": "postgres", "status": "unhealthy", "latency_ms": 0, "detail": str(e)})
        
    # Redpanda
    redpanda_url = os.environ.get("REDPANDA_URL", "http://redpanda:8081/v1/cluster/health")
    try:
        start_time = time.time()
        resp = requests.get(redpanda_url, timeout=2)
        latency = int((time.time() - start_time) * 1000)
        services.append({"name": "redpanda", "status": "healthy" if resp.status_code == 200 else "degraded", "latency_ms": latency, "detail": f"Status {resp.status_code}"})
    except Exception as e:
        services.append({"name": "redpanda", "status": "unhealthy", "latency_ms": 0, "detail": str(e)})

    # Dagster
    dagster_url = os.environ.get("DAGSTER_URL", "http://dagster_orchestrator:3000/health")
    try:
        start_time = time.time()
        resp = requests.get(dagster_url, timeout=2)
        latency = int((time.time() - start_time) * 1000)
        services.append({"name": "dagster", "status": "healthy" if resp.status_code == 200 else "degraded", "latency_ms": latency, "detail": f"Status {resp.status_code}"})
    except Exception as e:
        services.append({"name": "dagster", "status": "unhealthy", "latency_ms": 0, "detail": str(e)})
        
    return {"services": services}

@app.get("/api/v1/model/info")
def model_info():
    default_info = {
        "model_name": "unknown",
        "model_version": "unknown",
        "f1_score": 0.0,
        "precision": 0.0,
        "recall": 0.0,
        "accuracy": 0.0,
        "training_date": None,
        "feature_count": 0,
        "status": "not_trained"
    }
    try:
        mlflow_uri = os.environ.get('MLFLOW_TRACKING_URI', 'http://mlflow:5000')
        mlflow.set_tracking_uri(mlflow_uri)
        runs = mlflow.search_runs(experiment_names=['mlsecops-anomaly-detection'], max_results=1, order_by=["start_time DESC"])
        if runs.empty:
            return default_info
            
        run = runs.iloc[0]
        return {
            "model_name": run.get("params.best_model", "network-anomaly-detector"),
            "model_version": run.get("run_id", "unknown"),
            "f1_score": float(run.get("metrics.f1_score", 0.0)) if "metrics.f1_score" in run else 0.0,
            "precision": float(run.get("metrics.precision", 0.0)) if "metrics.precision" in run else 0.0,
            "recall": float(run.get("metrics.recall", 0.0)) if "metrics.recall" in run else 0.0,
            "accuracy": float(run.get("metrics.accuracy", 0.0)) if "metrics.accuracy" in run else 0.0,
            "training_date": str(run.get("start_time", "")),
            "feature_count": 78,
            "status": "trained"
        }
    except Exception as e:
        logger.error(f"Error fetching model info from MLflow: {e}")
        return default_info