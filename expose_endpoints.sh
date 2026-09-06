#!/bin/bash
# Expose MLSecOps Platform via Cloudflare Quick Tunnels
# This script bypasses inbound firewalls by creating outbound tunnels.

echo "=========================================="
echo " Setting up Public URLs for your Apps..."
echo "=========================================="

# 1. Install Cloudflared if not present
if ! command -v cloudflared &> /dev/null
then
    echo "[+] Installing cloudflared..."
    curl -sL --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
    dpkg -i cloudflared.deb > /dev/null 2>&1
    rm cloudflared.deb
fi

# 2. Kill any existing tunnels to prevent conflicts
pkill cloudflared

echo "[+] Starting tunnels in the background..."
# Dagster is running on port 3000 inside THIS container
cloudflared tunnel --url http://localhost:3000 > dagster_tunnel.log 2>&1 &
# MLflow is running on port 5000 in the mlflow_server container
cloudflared tunnel --url http://mlflow_server:5000 > mlflow_tunnel.log 2>&1 &
# API is running on port 8000 in the mlsecops_api container
cloudflared tunnel --url http://mlsecops_api:8000 > api_tunnel.log 2>&1 &
# WebApp is running on port 3000 in the mlsecops_webapp container
cloudflared tunnel --url http://mlsecops_webapp:3000 > webapp_tunnel.log 2>&1 &

# Wait for tunnels to establish
echo "[+] Waiting for Cloudflare to generate public URLs (10 seconds)..."
sleep 10

echo "=========================================="
echo "🎉 SUCCESS! Access your apps from ANY network:"
echo "=========================================="

echo -n "🟢 Dagster UI : "
grep -o 'https://[a-zA-Z0-9-]*\.trycloudflare\.com' dagster_tunnel.log | head -1

echo -n "🟢 MLflow UI  : "
grep -o 'https://[a-zA-Z0-9-]*\.trycloudflare\.com' mlflow_tunnel.log | head -1

echo -n "🟢 FastAPI    : "
grep -o 'https://[a-zA-Z0-9-]*\.trycloudflare\.com' api_tunnel.log | head -1

echo -n "🟢 WebApp     : "
grep -o 'https://[a-zA-Z0-9-]*\.trycloudflare\.com' webapp_tunnel.log | head -1

echo "=========================================="
echo "Note: These links will stay active as long as this container runs."
echo "To stop them later, run: pkill cloudflared"
