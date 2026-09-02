# Streaming Module — Redpanda / Kafka

Handles real-time network traffic ingestion and inference via Redpanda (Kafka-compatible).

## Key Files
| File | Description |
|------|-------------|
| producer.py | Produces network flow records to Redpanda topics |
| cleaner.py | Cleans and normalizes raw records from the stream |
| inference.py | Consumes cleaned records and runs anomaly detection in real-time |

## Topics
| Topic | Purpose |
|-------|---------|
| 
etwork-logs-raw | Raw incoming network flows |
| 
etwork-logs-clean | Cleaned, normalized flows ready for inference |
