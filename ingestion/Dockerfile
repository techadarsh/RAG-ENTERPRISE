# Ingestion Worker Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements first (for caching)
COPY ingestion/requirements.txt /app/ingestion/requirements.txt
RUN pip install --no-cache-dir -r /app/ingestion/requirements.txt

# Copy shared backend modules
COPY backend/embeddings.py /app/backend/embeddings.py
COPY backend/milvus_client.py /app/backend/milvus_client.py

# Copy ingestion service code
COPY ingestion/ /app/ingestion/

# Set Python path to include backend modules
ENV PYTHONPATH=/app

WORKDIR /app/ingestion

# Run the RQ worker
CMD ["python", "worker.py"]
