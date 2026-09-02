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

@app.on_event("startup")
def load_ml_model():
    global model
    try:
        from src.ml.predict import load_model
        model = load_model()
        logger.info("ML model loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load ML model: {e}")

@app.get("/health")
def health_check():
    return {"status": "ok", "model_loaded": model is not None}

@app.post("/api/v1/predict", response_model=PredictionResponse)
def predict(record: NetworkRecord):
    global model
    if model is None:
        raise HTTPException(status_code=503, detail="Model is not loaded")
    
    try:
        from src.ml.predict import predict_record
        data_dict = record.dict()
        score = predict_record(model, data_dict)
        is_attack = score > 0.5
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
    global model
    if model is None:
        raise HTTPException(status_code=503, detail="Model is not loaded")
        
    responses = []
    from src.ml.predict import predict_record
    
    for record in records:
        try:
            score = predict_record(model, record.dict())
            is_attack = score > 0.5
            responses.append(PredictionResponse(
                is_attack=is_attack,
                confidence=score,
                attack_type="Anomaly" if is_attack else "Benign"
            ))
        except Exception as e:
            responses.append(PredictionResponse(is_attack=False, confidence=0.0, attack_type="Error"))
            
    return responses