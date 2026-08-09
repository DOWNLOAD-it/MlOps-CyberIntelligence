from dagster import asset, AssetExecutionContext
from src.streaming.producer import run_producer
from src.streaming.cleaner import run_cleaner
from src.streaming.inference import run_inference
import json

@asset(
    group_name="streaming_pipeline",
    compute_kind="python",
    description="Simule le flux réseau en temps réel en envoyant les CSV locaux vers Redpanda (raw-logs)."
)
def streaming_ingestion_asset(context: AssetExecutionContext):
    context.log.info("Lancement de l'ingestion temps réel vers Kafka/Redpanda...")
    events_published = run_producer(batch_size=1500)
    context.log.info(f"{events_published} événements poussés dans le flux brut.")
    # Structured materialization metadata for easier debugging and plotting
    context.log.info("materialization", extra={"events_published": events_published})
    return events_published

@asset(
    deps=[streaming_ingestion_asset],
    group_name="streaming_pipeline",
    compute_kind="python",
    description="Consomme le flux brut, le nettoie et le publie sur cleaned-logs."
)
def streaming_cleaning_asset(context: AssetExecutionContext):
    context.log.info("Lancement du processeur de nettoyage de flux...")
    cleaned = run_cleaner(max_messages=1500)
    context.log.info(f"{cleaned} événements nettoyés et publiés.")
    context.log.info("materialization", extra={"events_cleaned": cleaned})
    return cleaned

@asset(
    deps=[streaming_cleaning_asset],
    group_name="streaming_pipeline",
    compute_kind="machine_learning",
    description="Applique le modèle d'IA en temps réel et alerte sur le topic app-errors."
)
def model_inference_asset(context: AssetExecutionContext):
    context.log.info("Lancement de l'inférence du Modèle ML sur le flux propre...")
    anomalies = run_inference(max_messages=1500)
    context.log.info(f"{anomalies} cyber-attaques détectées et envoyées au système d'alerte.")
    context.log.info("materialization", extra={"anomalies_detected": anomalies})
    return anomalies
