##############################################
# Stage 1: Install deps (CPU-only PyTorch via uv.lock)
##############################################
FROM python:3.12-slim AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN touch README.md

# Install all deps from lockfile (CPU-only torch + spaCy model via [tool.uv.sources])
RUN uv sync --frozen --no-dev

# Pre-download sentence-transformers model
RUN .venv/bin/python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

##############################################
# Stage 2: Clean runtime image
##############################################
FROM python:3.12-slim

WORKDIR /app

# Copy only the clean venv and HF model cache
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface

# Copy application code
COPY src/ src/
COPY ui/ ui/
COPY config/ config/
COPY entrypoint.sh .

ENV DATABASE_PATH=":memory:" \
    API_URL="http://localhost:8000" \
    GCS_BUCKET="" \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

EXPOSE 8501

ENTRYPOINT ["./entrypoint.sh"]
