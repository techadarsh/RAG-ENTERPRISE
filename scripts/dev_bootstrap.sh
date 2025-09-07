#!/usr/bin/env bash
# FILE CONTRACT (KEEP THIS COMMENT)
# See COPILOT_SPEC.md for full build and style requirements.

# dev_bootstrap.sh: Prepare local RAG POC stack for development
# - Ensures Mistral model is pulled in Ollama container (idempotent)
# - Waits for API health endpoint to be ready
# - Prints status summary for API, Ollama, and Milvus

set -euo pipefail

MODEL="mistral:7b-instruct-q4_K_M"

# Pull Mistral model in Ollama (idempotent)
echo "[dev_bootstrap] Ensuring Mistral model is present in Ollama..."
docker exec -it ollama ollama pull "$MODEL"

echo "[dev_bootstrap] Waiting for API health endpoint to be ready..."
RETRIES=30
for i in $(seq 1 $RETRIES); do
  if curl -sf http://localhost:8080/health | grep -q '"status":"ok"'; then
    echo "[dev_bootstrap] API is healthy."
    break
  fi
  echo "[dev_bootstrap] Waiting for API... ($i/$RETRIES)"
  sleep 3
done

# Print status summary for API, Ollama, Milvus
print_status() {
  local name="$1" url="$2"
  if curl -sf "$url" > /dev/null; then
    printf "%-10s | UP\n" "$name"
  else
    printf "%-10s | DOWN\n" "$name"
  fi
}

echo "\nService Status Summary:"
echo "SERVICE    | STATUS"
echo "-----------|-------"
print_status "API"     "http://localhost:8080/health"
print_status "Ollama"  "http://localhost:11434/api/tags"
print_status "Milvus"  "http://localhost:9091/metrics"

echo "[dev_bootstrap] Done."
