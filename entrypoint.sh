#!/bin/bash
# Start both FastAPI backend and Streamlit frontend in a single container.
# FastAPI runs on port 8000 (internal), Streamlit on port 8501 (exposed to Cloud Run).

# Add /app to PYTHONPATH so absolute imports work (e.g., "from ui.api_client import ...")
export PYTHONPATH="/app:$PYTHONPATH"

# Start uvicorn in the background (single worker for in-memory SQLite)
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 1 &

# Wait briefly for backend to start
sleep 2

# Start streamlit in the foreground
exec streamlit run ui/streamlit_app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false \
    --server.enableWebsocketCompression=false \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false
