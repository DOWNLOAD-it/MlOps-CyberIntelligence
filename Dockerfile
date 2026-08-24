FROM python:3.10-slim

# Prevent Python from writing .pyc files & enable unbuffered logging for Docker logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Upgrade pip and install dependencies first (caches layer if requirements don't change)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code and files
COPY . .

# Run as a non-root user for security best practices
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "src/ingestion/ingest.py"]
