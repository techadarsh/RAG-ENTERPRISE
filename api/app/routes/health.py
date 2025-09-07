
"""
FILE CONTRACT: health.py

Goal: Provide liveness and dependency health endpoints.
Requirements:
- GET /health -> {"status":"ok"}
- GET /health/deps -> check reachability of Milvus, Embeddings, Ollama
   * Each check should attempt a fast connection with timeout.
   * Return dict: {"milvus":"ok/fail", "embeddings":"ok/fail", "ollama":"ok/fail"}
- Use httpx for embeddings/ollama; pymilvus for Milvus.
- Defensive error handling; short timeouts (1s).
- Add comments explaining why each dependency is critical.
"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.core.config import settings
import httpx
from pymilvus import connections

router = APIRouter()

@router.get("", status_code=status.HTTP_200_OK)
def health() -> dict:
    """
    Liveness probe endpoint.
    Returns a simple status message to indicate the API is running.
    """
    return {"status": "ok"}

@router.get("/deps", status_code=status.HTTP_200_OK)
async def health_deps() -> JSONResponse:
    """
    Readiness probe endpoint.
    Checks connectivity to Milvus (vector DB), Embeddings service, and Ollama LLM.
    Each is critical for RAG: Milvus for retrieval, Embeddings for vectorization, Ollama for LLM answers.
    Returns a status map for each dependency.
    """
    results = {}
    # --- Milvus check (vector DB, critical for retrieval) ---
    try:
        # Attempt a fast connection to Milvus with a 1s timeout
        connections.connect(alias="default", host=settings.MILVUS_HOST, port=settings.MILVUS_PORT, timeout=1)
        results["milvus"] = "ok"
    except Exception:
        results["milvus"] = "fail"
    finally:
        try:
            connections.disconnect(alias="default")
        except Exception:
            pass
    # --- Embeddings check (critical for query/document vectorization) ---
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            r = await client.post(f"http://{settings.EMBEDDINGS_HOST}:{settings.EMBEDDINGS_PORT}/encode", json={"texts": ["ping"]})
            results["embeddings"] = "ok" if r.status_code == 200 else "fail"
    except Exception:
        results["embeddings"] = "fail"
    # --- Ollama check (critical for LLM answers) ---
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            r = await client.get(f"http://{settings.LLM_HOST}:{settings.LLM_PORT}/api/tags")
            results["ollama"] = "ok" if r.status_code == 200 else "fail"
    except Exception:
        results["ollama"] = "fail"
    return JSONResponse(content=results)
