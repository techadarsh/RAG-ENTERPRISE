"""
Milvus client helpers for the Enterprise RAG POC.

Design goals:
- Do NOT connect at import time. All connections are made inside functions with short timeouts.
- Keep the API narrow and testable: ensure_collection, upsert_texts, search_embeddings.
- Work with cosine similarity (or inner product) and explain the choice in comments.
- Return plain dicts from public functions to make FastAPI responses trivial.

Environment:
- MILVUS_HOST, MILVUS_PORT, MILVUS_COLLECTION from settings.

Schema:
- id: Auto-increment primary key (INT64, auto_id=True, primary_key=True)
- vector: FLOAT_VECTOR(dim)
- text: VARCHAR(2048)
- source: VARCHAR(512)

Index:
- HNSW or IVF_FLAT with metric_type 'IP' or 'COSINE'. For the POC, choose one with sensible defaults and document it.
"""

from typing import List, Dict, Any, Optional
from app.core.config import settings

# Pymilvus imports must be inside functions to avoid startup crashes when Milvus isn't running.

DEFAULT_DIMENSION = 1024  # Fallback if we don't know the embedding dim yet.


def ensure_collection(collection_name: Optional[str] = None, dim: int = DEFAULT_DIMENSION) -> None:
    """
    Ensure a Milvus collection exists with the expected schema and index.

    - Creates the collection if missing.
    - Creates an index on the vector field if missing.
    - Enables dynamic fields off for predictable schema.

    Parameters
    ----------
    collection_name : str | None
        Target collection; defaults to settings.MILVUS_COLLECTION.
    dim : int
        Embedding dimension; must match the embeddings model output.

    Raises
    ------
    Exception
        Propagates any pymilvus error with a short, readable message.
    """
    from pymilvus import (
        connections, utility, FieldSchema, CollectionSchema, DataType, Collection, Index
    )

    name = collection_name or settings.MILVUS_COLLECTION
    connections.connect(alias="default", host=settings.MILVUS_HOST, port=settings.MILVUS_PORT, timeout=2.0)

    if not utility.has_collection(name):
        id_field = FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True)
        vec_field = FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dim)
        text_field = FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=2048)
        src_field = FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=512)

        schema = CollectionSchema(
            fields=[id_field, vec_field, text_field, src_field],
            description="Enterprise RAG POC chunks",
            enable_dynamic_field=False,
        )
        _ = Collection(name=name, schema=schema)

    col = Collection(name=name)

    # Choose an index suited for small-to-medium POC data:
    # - IVF_FLAT: simple, stable, OK for small datasets.
    # - HNSW: great recall/speed trade-off; slightly more config.
    # We'll use IVF_FLAT with COSINE (or IP); documentation explains trade-offs.
    existing_indexes = [idx.params.get("index_type") for idx in col.indexes] if col.indexes else []
    if not existing_indexes:
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "COSINE",
            "params": {"nlist": 1024},
        }
        col.create_index(field_name="vector", index_params=index_params)

    # Load into memory for searches (no-op if already loaded)
    col.load()


def upsert_texts(texts: List[Dict[str, Any]], collection_name: Optional[str] = None) -> None:
    """
    Insert (text, source, embedding) rows into Milvus.

    Each item in `texts` must include:
    {
        "text": str,
        "source": str,
        "embedding": List[float]
    }

    Notes:
    - Validates that all embeddings share the same dimension.
    - Uses insert; Milvus assigns auto id.
    """
    if not texts:
        return

    from pymilvus import connections, Collection

    name = collection_name or settings.MILVUS_COLLECTION
    connections.connect(alias="default", host=settings.MILVUS_HOST, port=settings.MILVUS_PORT, timeout=2.0)

    # Dimension sanity check
    first_dim = len(texts[0]["embedding"])
    for item in texts:
        if len(item["embedding"]) != first_dim:
            raise ValueError("All embeddings must share the same dimension")

    ensure_collection(name, dim=first_dim)
    col = Collection(name=name)

    vectors = [t["embedding"] for t in texts]
    txts = [str(t["text"]) for t in texts]
    srcs = [str(t["source"]) for t in texts]

    col.insert([vectors, txts, srcs])
    col.flush()


def search_embeddings(query_embedding: List[float], k: int = 5, collection_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search top-k most similar vectors and return a list of dicts:
    [{ "text": str, "source": str, "distance": float }]

    Uses COSINE distance by index configuration. If the index uses IP,
    document how scores relate (e.g., higher is more similar).
    """
    from pymilvus import connections, Collection

    name = collection_name or settings.MILVUS_COLLECTION
    connections.connect(alias="default", host=settings.MILVUS_HOST, port=settings.MILVUS_PORT, timeout=2.0)

    ensure_collection(name, dim=len(query_embedding))
    col = Collection(name=name)

    search_params = {"metric_type": "COSINE", "params": {"nprobe": 16}}
    res = col.search(
        data=[query_embedding],
        anns_field="vector",
        param=search_params,
        limit=max(1, int(k)),
        output_fields=["text", "source"],
    )

    out: List[Dict[str, Any]] = []
    for hit in res[0]:
        # hit.distance is COSINE distance; convert to a "score" if desired later.
        out.append({"text": hit.entity.get("text"), "source": hit.entity.get("source"), "distance": float(hit.distance)})
    return out
