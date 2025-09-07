#!/usr/bin/env bash
# FILE CONTRACT (KEEP THIS COMMENT)
# See COPILOT_SPEC.md for full build and style requirements.

# ingest_sample.sh: Run full ingestion pipeline on sample docs
# - Assumes ./sample_docs is mounted to /data in ingest container
# - Runs CLI subcommands: load -> chunk -> embed -> upsert
# - Prints number of inserted chunks at the end

set -euo pipefail

DATA_PATH="${1:-/data}"

# Run each pipeline step in the ingest container
run_step() {
  local step="$1"
  echo "[ingest_sample] Running: $step"
  docker exec -it ingest python -m pipeline.cli $step --path "$DATA_PATH"
}

run_step load
run_step chunk
run_step embed
run_step upsert

# Print number of inserted chunks (assumes upsert prints this info)
echo "[ingest_sample] Ingestion complete. See logs above for chunk count."
