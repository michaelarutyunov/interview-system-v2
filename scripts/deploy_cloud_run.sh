#!/usr/bin/env bash
# Deploy interview-system-v2 to Google Cloud Run.
#
# Prerequisites:
#   - gcloud CLI installed and authenticated (`gcloud auth login`)
#   - Docker running (Docker Desktop or native)
#   - Secrets created in Secret Manager (see README section below)
#
# Usage:
#   ./scripts/deploy_cloud_run.sh [PROJECT_ID] [REGION]
#
# Defaults:
#   PROJECT_ID — taken from `gcloud config get project`
#   REGION     — us-central1
set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
PROJECT_ID="${1:-$(gcloud config get project 2>/dev/null)}"
REGION="${2:-us-central1}"
REPO="interview-system"
IMAGE="interview-app"
TAG=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
SERVICE_NAME="interview-system"

AR_HOST="${REGION}-docker.pkg.dev"
IMAGE_URI="${AR_HOST}/${PROJECT_ID}/${REPO}/${IMAGE}:${TAG}"
# ─────────────────────────────────────────────────────────────────────────────

if [[ -z "$PROJECT_ID" ]]; then
  echo "ERROR: No GCP project set. Run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

echo "Project:  ${PROJECT_ID}"
echo "Region:   ${REGION}"
echo "Image:    ${IMAGE_URI}"
echo ""

# Step 1: Ensure Artifact Registry repo exists
echo "==> Creating Artifact Registry repository (if it doesn't exist)..."
gcloud artifacts repositories describe "${REPO}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}" &>/dev/null \
  || gcloud artifacts repositories create "${REPO}" \
       --repository-format=docker \
       --location="${REGION}" \
       --project="${PROJECT_ID}"

# Step 2: Configure Docker auth for Artifact Registry
echo "==> Configuring Docker authentication..."
gcloud auth configure-docker "${AR_HOST}" --quiet

# Step 3: Build image
echo "==> Building Docker image..."
docker build -t "${IMAGE_URI}" .

# Step 4: Push to Artifact Registry
echo "==> Pushing image to Artifact Registry..."
docker push "${IMAGE_URI}"

# Step 5: Deploy to Cloud Run
echo "==> Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image="${IMAGE_URI}" \
  --region="${REGION}" \
  --platform=managed \
  --port=8501 \
  --memory=4Gi \
  --cpu=2 \
  --concurrency=10 \
  --min-instances=0 \
  --max-instances=3 \
  --timeout=300 \
  --no-cpu-throttling \
  --cpu-boost \
  --set-secrets="ANTHROPIC_API_KEY=anthropic-api-key:latest,KIMI_API_KEY=kimi-api-key:latest" \
  --allow-unauthenticated \
  --project="${PROJECT_ID}"

# Step 6: Print service URL
echo ""
echo "==> Deployed! Service URL:"
gcloud run services describe "${SERVICE_NAME}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(status.url)"
