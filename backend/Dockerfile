# Backend Dockerfile for Apple Silicon (ARM64)
# Force ARM64 platform to ensure compatible wheels
FROM --platform=linux/arm64/v8 python:3.10-slim

WORKDIR /app

# Install system dependencies for ARM64 PyTorch
# libopenblas-dev: ARM64-optimized BLAS for matrix operations
# libomp-dev: OpenMP support for parallel CPU operations
# g++: Required for some native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopenblas-dev \
    libomp-dev \
    g++ \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install ARM64-compatible PyTorch FIRST (before other deps)
# This ensures sentence-transformers uses the correct torch wheel
RUN pip install --no-cache-dir \
    torch==2.3.0 \
    torchvision==0.18.0 \
    torchaudio==2.3.0

# Copy requirements and install remaining dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create .env from example if it doesn't exist
RUN if [ ! -f .env ]; then cp .env.example .env; fi

# Environment optimizations for Apple Silicon ARM64
ENV OMP_NUM_THREADS=8
ENV TOKENIZERS_PARALLELISM=false
ENV PYTORCH_ENABLE_MPS_FALLBACK=1

# Expose port
EXPOSE 8000

# Run the application with extended timeouts for model loading
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "300"]
