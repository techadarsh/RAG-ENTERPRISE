# FILE CONTRACT (KEEP THIS COMMENT)
# See COPILOT_SPEC.md for full build and style requirements.

# Dockerfile for ingestion CLI (ingest)
# - Uses python:3.11-slim for minimal base image
# - Installs same dependencies as api for consistency
# - ENTRYPOINT runs CLI; in POC, we use `docker exec` to run subcommands interactively

FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ../api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY pipeline ./pipeline
COPY cli.py .

ENTRYPOINT ["python", "-m", "pipeline.cli"]
