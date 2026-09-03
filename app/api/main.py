from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
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

def get_or_load_model():
    global model, scaler
    if model is None:
        try:
            from src.ml.predict import load_model
            loaded_model, loaded_scaler = load_model()
            if loaded_model is not None:
                model, scaler = loaded_model, loaded_scaler
                logger.info("ML model dynamically loaded successfully.")
        except Exception as e:
            logger.error(f"Error during dynamic model loading: {e}")
    return model, scaler

@app.on_event("startup")
def load_ml_model():
    global model, scaler
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