"""
Batch embeddings via HTTP service.

- POST http://{EMBEDDINGS_HOST}:{EMBEDDINGS_PORT}/encode
- Body: {"texts": [ ... up to batch_size ... ]}
- Response: {"vectors": [[...], ...]}

Guarantees:
- Stable ordering (vectors[i] corresponds to texts[i]).
- Retries with backoff for transient errors.
"""

from __future__ import annotations
from typing import List
import time
import httpx

# For production, use a shared config package or pass via env
import os
EMBEDDINGS_HOST = os.getenv("EMBEDDINGS_HOST", "embeddings")
EMBEDDINGS_PORT = os.getenv("EMBEDDINGS_PORT", "8000")


def _embed_once(batch: List[str]) -> List[List[float]]:
    url = f"http://{EMBEDDINGS_HOST}:{EMBEDDINGS_PORT}/encode"
    with httpx.Client(timeout=5.0) as client:
        r = client.post(url, json={"texts": batch})
        r.raise_for_status()
        data = r.json()
        vecs = data.get("vectors") or []
        if len(vecs) != len(batch):
            raise RuntimeError("Embeddings length mismatch")
        return [[float(x) for x in v] for v in vecs]


def batch_embed(texts: List[str], batch_size: int = 32, retries: int = 2, backoff: float = 0.5) -> List[List[float]]:
    if not texts:
        return []
    out: List[List[float]] = []
    for i in range(0, len(texts), batch_size):
        chunk = texts[i : i + batch_size]
        attempt = 0
        while True:
            try:
                out.extend(_embed_once(chunk))
                break
            except Exception:
                if attempt >= retries:
                    raise
                attempt += 1
                time.sleep(backoff * attempt)
    return out
