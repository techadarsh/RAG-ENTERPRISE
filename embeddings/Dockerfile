FROM python:3.11-slim

# System deps for torch wheels (CPU only)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

# Install runtime deps
RUN pip install --no-cache-dir fastapi uvicorn sentence-transformers

COPY server.py /srv/server.py

EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
