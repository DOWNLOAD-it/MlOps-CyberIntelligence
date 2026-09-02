# Streaming & Real-time Inference

Manages real-time data flow using **Redpanda / Kafka** (Ports: 4303-4306).
- Processes incoming network traffic streams.
- Runs inference using the active ML model.
- Writes alerts and predictions to the **PostgreSQL** database for real-time monitoring via Grafana and the FastAPI backend.
