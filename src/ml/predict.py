"""Prediction module for network anomaly detection.

Loads trained model and scaler to predict anomalies in network traffic.
"""

import os
import logging
import numpy as np
import joblib
from typing import Tuple, Optional, Any, Dict

from src.ml.features import extract_features, preprocess_features

logger = logging.getLogger(__name__)

def get_project_root() -> str:
    """Get the root directory of the project."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(current_dir))

def load_model(model_path: Optional[str] = None, scaler_path: Optional[str] = None) -> Tuple[Any, Any]:
    """Load model and scaler from MLflow or local files.
    
    Args:
        model_path: Optional path to local model.
        scaler_path: Optional path to local scaler.
        
    Returns:
        Tuple of (model, scaler) or (None, None) if not found.
    """
    model = None
    scaler = None
    
    # Try MLflow first if possible
    try:
        import mlflow
        # Assume tracking URI is set properly via environment variable or default
        tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")
        mlflow.set_tracking_uri(tracking_uri)
        
        # Try to load production model
        model_uri = "models:/network-anomaly-detector/Production"
        try:
            model = mlflow.sklearn.load_model(model_uri)
            logger.info(f"Loaded model directly from MLflow Registry: {model_uri}")
        except Exception:
            # Fall back to latest version if Production not found
            model_uri = "models:/network-anomaly-detector/latest"
            try:
                model = mlflow.sklearn.load_model(model_uri)
                logger.info(f"Loaded model directly from MLflow Registry: {model_uri}")
            except Exception as e:
                logger.error(f"Could not load model from MLflow registry: {e}")
                
        # To fetch the scaler, we need to download it from the run's artifacts
        if model is not None:
            try:
                from mlflow.tracking import MlflowClient
                client = MlflowClient()
                versions = client.get_latest_versions("network-anomaly-detector", stages=["Production"])
                if not versions:
                    versions = client.get_latest_versions("network-anomaly-detector")
                
                if versions:
                    run_id = versions[0].run_id
                    # Download scaler artifact
                    local_scaler_path = client.download_artifacts(run_id, "scaler/scaler.joblib")
                    if os.path.exists(local_scaler_path):
                        scaler = joblib.load(local_scaler_path)
                        logger.info(f"Loaded scaler directly from MLflow artifacts for run {run_id}")
            except Exception as e:
                logger.error(f"Failed to fetch scaler from MLflow: {e}")
                
    except ImportError:
        logger.error("MLflow not available.")
    except Exception as e:
        logger.error(f"Error accessing MLflow: {e}")

    if model is None:
        logger.warning("No model found in MLflow. Returning None.")
            
    return model, scaler

def predict(record: Dict, model: Any = None, scaler: Any = None) -> Tuple[bool, float]:
    """Predict if a single record is an anomaly.
    
    Args:
        record: Dictionary containing network flow features.
        model: IsolationForest model.
        scaler: StandardScaler used during training.
        
    Returns:
        Tuple of (is_anomaly (bool), confidence score (float [0, 1]))
    """
    if model is None:
        return False, 0.0
        
    try:
        # Extract features (returns DataFrame with 1 row)
        df_features = extract_features([record])
        
        # Scale if scaler is provided
        if scaler is not None:
            X_scaled, _ = preprocess_features(df_features, scaler=scaler, fit=False)
        else:
            X_scaled = df_features.values
            
        # Check if model has predict_proba (like RandomForestClassifier)
        if hasattr(model, 'predict_proba'):
            proba = model.predict_proba(X_scaled)[0]
            # Assuming class 1 is the anomaly/attack class
            confidence = float(proba[1]) if len(proba) > 1 else float(proba[0])
            pred = model.predict(X_scaled)[0]
            is_anomaly = bool(pred == 1)
        else:
            # Fallback for IsolationForest
            score = model.decision_function(X_scaled)[0]
            pred = model.predict(X_scaled)[0]
            is_anomaly = bool(pred == -1)
            confidence = float(1 / (1 + np.exp(score)))
        
        return is_anomaly, confidence
        
    except Exception as e:
        logger.error(f"Error during prediction: {e}")
        return False, 0.0
