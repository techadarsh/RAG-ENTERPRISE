"""
Upsert pipeline into Milvus.

Steps:
- Ensure collection (with given dimension).
- Insert texts + embeddings + source metadata.

For POC simplicity, we import the same helpers used by API if available,
or reproduce the minimal client logic here to avoid cross-container coupling.
"""

from __future__ import annotations
from typing import List, Dict
from app.core.config import settings
from app.store.milvus_client import ensure_collection  # reuse API helper
from pymilvus import connections, Collection  # lazy usage in functions

def upsert(records: List[Dict]) -> None:
    """
    Each record must include:
      {"text": str, "source": str, "embedding": list[float]}
    """
    if not records:
        return

    dim = len(records[0]["embedding"])
    for r in records:
        if len(r["embedding"]) != dim:
            raise ValueError("All embeddings must share the same dimension")

    # Connect and ensure collection
    connections.connect(alias="default", host=settings.MILVUS_HOST, port=settings.MILVUS_PORT, timeout=2.0)
    ensure_collection(settings.MILVUS_COLLECTION, dim=dim)
    col = Collection(name=settings.MILVUS_COLLECTION)

    vectors = [r["embedding"] for r in records]
    texts = [r["text"] for r in records]
    sources = [r["source"] for r in records]

    col.insert([vectors, texts, sources])
    col.flush()
