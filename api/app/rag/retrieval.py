"""
Retrieval utilities: query embedding + top-k search.

Design:
- HTTP call to embeddings service at http://{EMBEDDINGS_HOST}:{EMBEDDINGS_PORT}/encode
- JSON body: {"texts": [<string>]}
- Response: {"vectors": [[...]]}
- Short timeouts and clear errors.
- Map Milvus distance to a user-friendly 'score' (1 - distance for cosine).

We avoid import-time deps; everything happens inside functions.
"""

from typing import List, Dict, Any
import httpx

from app.core.config import settings
from app.store.milvus_client import ensure_collection, search_embeddings


def embed_query(query: str) -> List[float]:
    """
    Get a single query embedding from the embeddings service.

    Returns
    -------
    List[float]
        The embedding vector for the query.

    Raises
    ------
    RuntimeError
        If the embeddings service returns a non-200 or malformed response.
    """
    url = f"http://{settings.EMBEDDINGS_HOST}:{settings.EMBEDDINGS_PORT}/encode"
    payload = {"texts": [query]}
    try:
        with httpx.Client(timeout=3.0) as client:
            r = client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
            vectors = data.get("vectors") or []
            if not vectors or not isinstance(vectors, list) or not vectors[0]:
                raise RuntimeError("Embeddings service returned empty vectors")
            vec = vectors[0]
            if not isinstance(vec, list) or not all(isinstance(x, (int, float)) for x in vec):
                raise RuntimeError("Embeddings service returned invalid vector format")
            return [float(x) for x in vec]
    except Exception as e:
        raise RuntimeError(f"Failed to embed query: {e}") from e


def retrieve_topk(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    End-to-end retrieval:
    1) Embed the query.
    2) Ensure Milvus collection exists with matching dim.
    3) Search top-k vectors and return normalized scores.

    Returns
    -------
    List[Dict[str, Any]]
        Each item: {"text": str, "source": str, "score": float}
    """
    vec = embed_query(query)
    ensure_collection(settings.MILVUS_COLLECTION, dim=len(vec))

    hits = search_embeddings(vec, k=k, collection_name=settings.MILVUS_COLLECTION)

    # Convert COSINE distance to a more intuitive "score": 1 - distance.
    # If you switch to IP, adjust this formula accordingly (score = distance).
    out: List[Dict[str, Any]] = []
    for h in hits:
        dist = float(h.get("distance", 0.0))
        score = max(0.0, min(1.0, 1.0 - dist))
        out.append({"text": h.get("text", ""), "source": h.get("source", ""), "score": score})
    return out
