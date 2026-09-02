# Streaming Module

Handles real-time network traffic ingestion and inference using **Redpanda** (Kafka-compatible broker).

## Key Files

| File | Description |
|------|-------------|
| `producer.py` | Reads local CSV files and produces raw network flow records to a Kafka topic. |
| `cleaner.py` | Consumes raw records, sanitizes/normalizes them, and produces them to a clean topic. |
| `inference.py` | Consumes clean records, applies real-time anomaly detection, and produces alerts. |

## Topics

| Topic | Purpose |
|-------|---------|
| `network-logs-raw` | Raw incoming network flows from the producer. |
| `network-logs-clean` | Cleaned, normalized flows ready for inference or storage. |
| `app-errors` | Anomaly alerts detected by the inference model. |
