# Docker Deployment

> **Purpose**: Architectural decisions, rationale, and update procedures for the single-container Cloud Run deployment.
> For the *what* (architecture summary, env var table, deploy command), see `docs/SYSTEM_DESIGN.md` → "Container Deployment".

---

## Key Files

| File | Role |
|------|------|
| `Dockerfile` | Multi-stage build (builder → runtime) |
| `entrypoint.sh` | Starts FastAPI (background) + Streamlit (foreground) |
| `.dockerignore` | Excludes dev/test/docs from build context |
| `scripts/deploy_cloud_run.sh` | Build → push → deploy to Cloud Run |
| `pyproject.toml` | CPU-only PyTorch index configuration |

---

## Architectural Decisions

### Single-container (FastAPI + Streamlit)

**Decision**: Both services in one container, not separate Cloud Run services.

**Why**: Cloud Run bills per-container-minute with a minimum of 1 instance when `min-instances > 0`. Two services would double the baseline cost for a low-traffic interview tool. The single-container approach trades horizontal scalability (can't scale backend independently) for cost efficiency. At concurrency=10 and max-instances=3, the bottleneck is LLM API latency, not CPU.

**Trade-off**: If the backend ever needs to handle heavy API traffic independently (e.g., batch processing), split into two Cloud Run services. The `API_URL` env var already supports cross-service routing.

### Multi-stage build

**Decision**: Builder stage installs deps, runtime stage copies only `.venv` and HF cache.

**Why**: `uv sync` pulls ~1.5 GB of packages (PyTorch, spaCy, sentence-transformers). Without multi-stage, the build tools and pip cache bloat the final image. The builder discards everything except the clean venv. Result: 2.64 GB vs. ~5 GB single-stage.

### CPU-only PyTorch

**Decision**: `pyproject.toml` configures a custom PyTorch index for CPU-only wheels.

**Why**: Default `pip install torch` pulls CUDA runtime, cuDNN, and NVIDIA libs (~10 GB). The interview system only uses sentence-transformers for similarity scoring — no GPU needed. This is the single largest image-size optimization: 13.2 GB → 2.64 GB.

**How it works** (`pyproject.toml`):
```toml
[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
explicit = true

[tool.uv.sources]
torch = [{ index = "pytorch-cpu" }]
```

When updating: verify the PyTorch CPU index URL is still valid after a version bump.

### File-based SQLite (`/tmp/interview.db`)

**Decision**: Not `:memory:`.

**Why**: `aiosqlite.connect(":memory:")` creates a *separate* in-memory database per connection. Since the code opens multiple connections (pipeline stages, API routes), writes on one connection were invisible to reads on another. This caused silent data loss — sessions appeared empty after creation.

**Trade-off**: `/tmp` is ephemeral on Cloud Run — data is lost when the container stops. This is acceptable because session data is exported to GCS on completion, and the system is designed for single-session interviews, not persistent storage.

### Single Uvicorn worker

**Decision**: `--workers 1` in entrypoint.sh.

**Why**: SQLite doesn't support concurrent writes. Multiple workers would cause `database is locked` errors under load. At concurrency=10 (Cloud Run setting), the single worker is sufficient because each request is I/O-bound (waiting for LLM APIs).

### Streamlit WebSocket flags

**Decision**: `--server.enableWebsocketCompression=false`, `--server.enableCORS=false`, `--server.enableXsrfProtection=false`.

**Why**: Cloud Run's load balancer doesn't handle WebSocket per-message compression correctly. With compression enabled, Streamlit's `st.rerun()` hangs indefinitely — the browser sends a compressed frame that the load balancer doesn't forward properly. CORS and XSRF are disabled because Cloud Run handles TLS termination and authentication at the infrastructure level.

### Pre-cached ML model

**Decision**: `RUN .venv/bin/python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"` in builder stage.

**Why**: First import of sentence-transformers triggers a model download (~90 MB). On Cloud Run cold starts, this download adds ~15 seconds and fails if HuggingFace Hub is slow. Baking it into the image eliminates cold-start latency and removes a runtime network dependency.

---

## Cloud Run Configuration

| Setting | Value | Rationale |
|---------|-------|-----------|
| Memory | 4Gi | PyTorch + spaCy + sentence-transformers need ~2.5 GB at rest |
| CPU | 2 | Dual services (FastAPI + Streamlit) share the container |
| Concurrency | 10 | Low-traffic tool; LLM API latency is the bottleneck |
| Min instances | 0 | Scale to zero when idle — cost savings |
| Max instances | 3 | Prevents runaway scaling from abuse |
| Timeout | 300s | Long interviews can have slow LLM responses |
| CPU boost | Yes | Faster cold starts |
| No CPU throttling | Yes | Prevents Streamlit WebSocket timeouts during idle periods |
| Port | 8501 | Streamlit's default; Cloud Run routes external traffic here |

---

## Update Procedure

### 1. Update dependencies

```bash
# If adding/upgrading packages:
uv add <package>          # or uv lock --upgrade <package>
uv sync                   # Verify locally
uv run pytest             # Ensure nothing breaks
```

### 2. Rebuild and test locally

```bash
docker build -t interview-test .
docker run -p 8501:8501 \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -e KIMI_API_KEY="$KIMI_API_KEY" \
  interview-test
```

Verify:
- Streamlit UI loads at `http://localhost:8501`
- API responds at `http://localhost:8000/health`
- Run a short interview to confirm end-to-end flow

### 3. Deploy

```bash
./scripts/deploy_cloud_run.sh [PROJECT_ID] [REGION]
```

The script:
1. Creates Artifact Registry repo (idempotent)
2. Authenticates Docker to Artifact Registry
3. Builds image tagged with git SHA
4. Pushes to Artifact Registry
5. Deploys to Cloud Run with the configuration above
6. Prints the service URL

### 4. Verify deployment

```bash
# Get the service URL
gcloud run services describe interview-system \
  --region=us-central1 \
  --format="value(status.url)"

# Check logs
gcloud run services logs read interview-system \
  --region=us-central1 \
  --limit=50
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `st.rerun()` hangs | WebSocket compression re-enabled | Check `entrypoint.sh` has `--server.enableWebsocketCompression=false` |
| Sessions empty after creation | SQLite `:memory:` mode | Verify `DATABASE_PATH` points to a file path, not `:memory:` |
| Image > 5 GB | CUDA PyTorch pulled | Check `pyproject.toml` has CPU-only index; run `docker build --no-cache` |
| Cold start > 30s | HF model not cached | Check builder stage pre-downloads `all-MiniLM-L6-v2` |
| `database is locked` | Multiple Uvicorn workers | Check `entrypoint.sh` uses `--workers 1` |
| Cloud Run 503 errors | Memory exceeded | Increase `--memory` or reduce concurrency |

---

## Adding New API Keys

When adding a new LLM provider:

1. Add the key to Secret Manager:
   ```bash
   echo -n "your-key" | gcloud secrets create new-api-key --data-file=-
   ```

2. Update `deploy_cloud_run.sh` `--set-secrets` flag to include it

3. Add the env var to `Dockerfile` `ENV` block if it needs a default

4. Update the env var table in `docs/SYSTEM_DESIGN.md`

5. Update this doc's troubleshooting section if the provider has quirks
