#!/bin/bash
set -e

# Start Prefect Server in the background
prefect server start & 
PREFECT_PID=$!

# Wait for Prefect Server to be ready
while ! curl -s http://localhost:4200/api/health >/dev/null; do
    sleep 1
done

# Set the Prefect API URL
export PREFECT_API_URL="http://localhost:4200/api"

# Run Prefect flow script in background
python prefect/prefect_flow.py &
FLOW_PID=$!

# Start FastAPI
exec python -m uvicorn fastapi_app:app --host 0.0.0.0 --reload

# Cleanup in case of shutdown
trap 'kill $PREFECT_PID $FLOW_PID' EXIT