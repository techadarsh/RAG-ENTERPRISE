# FILE CONTRACT (KEEP THIS COMMENT)
# See COPILOT_SPEC.md for full build and style requirements.

# Dockerfile for FastAPI backend (api)
# - Uses python:3.11-slim for minimal base image
# - Installs system dependencies for pdfminer.six and other libs
# - Leverages Docker layer caching: requirements installed before source code
# - Avoids running as root for security (not shown here for brevity, but recommended for prod)

FROM python:3.11-slim

# Install system dependencies for pdfminer.six and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONPATH=/app

# Install Python dependencies first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app ./app
COPY pytest.ini /app/pytest.ini

EXPOSE 8080

# Run FastAPI app with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
