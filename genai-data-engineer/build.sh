#!/usr/bin/env bash
set -e

PROJECT_ID="${PROJECT_ID}"
REGION="us-central1"
REPO="data-dept-dev"
IMAGE_NAME="agentic-data-dept"
TAG="$(date +%Y%m%d-%H%M%S)"
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${IMAGE_NAME}:latest"

echo "🔧 Building image: ${IMAGE_URI}"

gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

docker build  --platform linux/amd64 -t "${IMAGE_URI}" .

docker push "${IMAGE_URI}"

echo "✅ Image pushed:"
echo "${IMAGE_URI}"