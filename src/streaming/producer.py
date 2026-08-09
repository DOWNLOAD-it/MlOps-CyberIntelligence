import os
import glob
import json
import logging
import pandas as pd
import time
from kafka import KafkaProducer
from kafka.errors import KafkaError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def get_kafka_producer(bootstrap_servers="redpanda:9092", timeout_s: int = 60):
    """
    Create a KafkaProducer with retries and exponential backoff until `timeout_s` seconds.
    This helps when the broker container is still initializing at startup.
    """
    end_time = time.time() + timeout_s
    attempt = 0
    while True:
        try:
            attempt += 1
            logging.info(f"Creating KafkaProducer (attempt={attempt}) to {bootstrap_servers}")
            producer = KafkaProducer(
                bootstrap_servers=[bootstrap_servers],
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
            )
            # perform a quick metadata request to ensure bootstrap succeeded
            producer.bootstrap_connected()
            logging.info("KafkaProducer bootstrap succeeded")
            return producer
        except KafkaError as e:
            remaining = end_time - time.time()
            logging.warning(f"Kafka bootstrap attempt {attempt} failed: {e}; retrying, {max(0,int(remaining))}s left")
            if remaining <= 0:
                logging.error("Kafka bootstrap timed out")
                raise
            sleep = min(5 * (2 ** (attempt - 1)), remaining, 10)
            time.sleep(sleep)

def get_project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))


def run_producer(batch_size=1000):
    """
    Lit les fichiers CSV dans data/raw/ et les publie dans le topic 'raw-logs'
    simulant ainsi un flux d'ingestion en temps réel.
    """
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
    topic = os.getenv("KAFKA_RAW_TOPIC", "raw-logs")
    data_dir = os.path.join(get_project_root(), "data", "raw")
    
    producer = get_kafka_producer(bootstrap_servers)
    
    csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
    if not csv_files:
        logging.warning("Aucun fichier CSV trouvé pour l'ingestion.")
        return 0

    total_published = 0
    
    for filepath in csv_files:
        logging.info(f"Lecture du fichier: {filepath}")
        
        # Lecture par chunks pour ne pas saturer la mémoire et simuler un flux
        for chunk in pd.read_csv(filepath, chunksize=batch_size, keep_default_na=False):
            # Remplacement des éventuelles valeurs infinies générées par pandas
            chunk = chunk.replace([float('inf'), float('-inf')], None)
            records = chunk.to_dict(orient="records")
            
            for record in records:
                producer.send(topic, value=record)
                total_published += 1
                
            producer.flush()
            logging.info(f"Publié {len(records)} événements sur {topic}.")
            break # Dans le cadre du micro-batching, on traite un chunk à la fois pour la démo
            
    producer.close()
    return total_published

if __name__ == "__main__":
    run_producer()
