import os
import json
import logging
import random
import time
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def get_kafka_clients(bootstrap_servers, timeout_s: int = 60):
    """Create consumer and producer with retries until broker is available."""
    end_time = time.time() + timeout_s
    attempt = 0
    while True:
        try:
            attempt += 1
            logging.info(f"Creating Kafka consumer/producer (attempt={attempt}) to {bootstrap_servers}")
            consumer = KafkaConsumer(
                os.getenv("KAFKA_CLEANED_TOPIC", "cleaned-logs"),
                bootstrap_servers=[bootstrap_servers],
                group_id="inference-group",
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            producer = KafkaProducer(
                bootstrap_servers=[bootstrap_servers],
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
            )
            producer.bootstrap_connected()
            logging.info("Kafka consumer/producer bootstrap succeeded")
            return consumer, producer
        except KafkaError as e:
            remaining = end_time - time.time()
            logging.warning(f"Kafka client attempt {attempt} failed: {e}; retrying, {max(0,int(remaining))}s left")
            if remaining <= 0:
                logging.error("Kafka client bootstrap timed out")
                raise
            sleep = min(5 * (2 ** (attempt - 1)), remaining, 10)
            time.sleep(sleep)

def mock_predict_anomaly(record):
    """
    Simule un modèle de Machine Learning (ex: Isolation Forest, XGBoost).
    Si l'événement a is_attack = 1 dans les données, on lui donne une probabilité
    élevée d'être détecté. Sinon, probabilité très faible.
    """
    # Dans un vrai système, on utiliserait: model.predict_proba([features])
    
    is_attack = int(record.get("is_attack", 0))
    if is_attack == 1:
        # Probabilité entre 85% et 99%
        confidence = random.uniform(0.85, 0.99)
    else:
        # Probabilité entre 1% et 10%
        confidence = random.uniform(0.01, 0.10)
        
    # Seuil d'anomalie
    return confidence > 0.80, confidence

def get_project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))


def run_inference(max_messages=1000):
    """
    Consomme les messages nettoyés, réalise l'inférence, 
    et pousse les anomalies vers 'app-errors' pour alertement.
    """
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
    alert_topic = os.getenv("KAFKA_ALERT_TOPIC", "app-errors")

    export_dir = os.path.join(get_project_root(), "data", "exports")
    os.makedirs(export_dir, exist_ok=True)
    export_path = os.path.join(export_dir, "app_errors.jsonl")
    
    consumer, producer = get_kafka_clients(bootstrap_servers)
    
    logging.info("Attente de données propres pour l'inférence ML...")
    
    messages_processed = 0
    anomalies_detected = 0
    
    # Consomme un lot (timeout de 2000ms)
    clean_msgs = consumer.poll(timeout_ms=2000)

    with open(export_path, "w", encoding="utf-8") as export_file:
        for tp, messages in clean_msgs.items():
            for msg in messages:
                if messages_processed >= max_messages:
                    break
                    
                record = msg.value
                
                # Inférence ML
                is_anomaly, confidence = mock_predict_anomaly(record)
                
                if is_anomaly:
                    # Ajoute les métadonnées ML au log avant de l'envoyer à l'alerte
                    record["ml_confidence_score"] = round(confidence, 4)
                    record["ml_model_version"] = "v1.2.0-isolation-forest"
                    producer.send(alert_topic, value=record)
                    export_file.write(json.dumps(record, default=str) + "\n")
                    anomalies_detected += 1
                
                messages_processed += 1
                
    if messages_processed > 0:
        producer.flush()
        logging.info(f"Inférence terminée : {messages_processed} événements analysés. {anomalies_detected} anomalies envoyées vers {alert_topic}.")
        logging.info(f"Fichier exporté : {export_path}")
    else:
        logging.info("Aucune donnée propre à analyser.")
        logging.info(f"Fichier d'export créé (vide si aucune anomalie) : {export_path}")
        
    consumer.close()
    producer.close()
    
    return anomalies_detected

if __name__ == "__main__":
    run_inference()
