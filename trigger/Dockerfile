# Trigger Service Dockerfile
# Lightweight container for folder watcher and S3 listener

FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy trigger service modules
COPY watcher.py .
COPY s3_listener.py .
COPY main.py .

# Create necessary directories
RUN mkdir -p /app/data/incoming /app/data/s3_downloads

# Set Python to unbuffered mode for real-time logs
ENV PYTHONUNBUFFERED=1

# Default command - run main orchestrator
CMD ["python", "main.py"]
