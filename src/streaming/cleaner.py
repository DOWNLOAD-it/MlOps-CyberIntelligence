import os
import json
import logging
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
                os.getenv("KAFKA_RAW_TOPIC", "raw-logs"),
                bootstrap_servers=[bootstrap_servers],
                group_id="cleaner-group",
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            producer = KafkaProducer(
                bootstrap_servers=[bootstrap_servers],
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
            )
            # quick check
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

def clean_record(record):
    """
    Simule une fonction de nettoyage : 
    - Formate les colonnes
    - Supprime ou remplace les valeurs invalides
    """
    cleaned = {}
    for k, v in record.items():
        # Standardisation des noms de colonnes (minuscules, sans espaces)
        new_key = str(k).strip().lower().replace(" ", "_")
        
        # Filtrage basique (ex: on force le port en entier, on remplace les None par 0)
        if v is None:
            v = 0
        cleaned[new_key] = v
        
    return cleaned

def get_project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))


def run_cleaner(max_messages=1000):
    """
    Consomme un micro-batch de messages depuis 'raw-logs', les nettoie, 
    et les republie dans 'cleaned-logs'.
    """
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
    cleaned_topic = os.getenv("KAFKA_CLEANED_TOPIC", "cleaned-logs")
    
    export_dir = os.path.join(get_project_root(), "data", "exports")
    os.makedirs(export_dir, exist_ok=True)
    export_path = os.path.join(export_dir, "cleaned_logs.jsonl")

    consumer, producer = get_kafka_clients(bootstrap_servers)
    
    logging.info("Attente de messages bruts à nettoyer...")
    
    messages_processed = 0
    # Consomme un lot (timeout de 2000ms si plus de messages)
    raw_msgs = consumer.poll(timeout_ms=2000)

    with open(export_path, "w", encoding="utf-8") as export_file:
        for tp, messages in raw_msgs.items():
            for msg in messages:
                if messages_processed >= max_messages:
                    break
                    
                raw_data = msg.value
                cleaned_data = clean_record(raw_data)
                
                producer.send(cleaned_topic, value=cleaned_data)
                export_file.write(json.dumps(cleaned_data, default=str) + "\n")
                messages_processed += 1
                
    if messages_processed > 0:
        producer.flush()
        logging.info(f"Nettoyage terminé : {messages_processed} événements publiés sur {cleaned_topic}.")
        logging.info(f"Fichier exporté : {export_path}")
    else:
        logging.info("Aucun message brut à traiter.")
        logging.info(f"Fichier d'export créé (vide si aucun message) : {export_path}")
        
    consumer.close()
    producer.close()
    
    return messages_processed

if __name__ == "__main__":
    run_cleaner()
