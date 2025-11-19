#!/usr/bin/env python3
"""
Local development server for Mac
Runs without Docker, using local services
"""
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Load local environment - override=True ensures .env.local takes precedence
from dotenv import load_dotenv
load_dotenv('.env.local', override=True)

# Create required directories
DATA_DIR = os.getenv("DATA_DIR", "./data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
CONFLUENCE_DIR = os.path.join(DATA_DIR, "sample_confluence_pages")
INCOMING_DIR = os.path.join(DATA_DIR, "incoming")

Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(CONFLUENCE_DIR).mkdir(parents=True, exist_ok=True)
Path(INCOMING_DIR).mkdir(parents=True, exist_ok=True)

import uvicorn

if __name__ == "__main__":
    print("🚀 Starting RAG Enterprise Backend (Local Mode)")
    print(f"📍 Ollama: http://localhost:11434")
    print(f"📍 Milvus: http://localhost:19530")
    print(f"📍 Redis: http://localhost:6379")
    print(f"📍 Backend: http://localhost:8000")
    print(f"📍 API Docs: http://localhost:8000/docs")
    print("")
    
    # Use the module path for reload to work properly
    uvicorn.run(
        "main:app",  # Use string import path instead of direct import
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
