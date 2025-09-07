"""
Simple character-based chunking (token-agnostic).

Rationale:
- For a POC, char-length approximates tokens well enough.
- Avoids heavy tokenizer deps; is deterministic and fast.

Contract:
- chunk_texts(records, size=800, overlap=150) -> list[dict]
  Input: [{"text": str, "source": str}]
  Output: [{"text": chunk, "source": source, "chunk_id": "source#i"}]
"""

from __future__ import annotations
from typing import List, Dict

def chunk_texts(records: List[Dict], size: int = 800, overlap: int = 150) -> List[Dict]:
    if not records:
        return []

    size = max(1, int(size))
    overlap = max(0, min(int(overlap), size - 1))

    chunks: List[Dict] = []
    for rec in records:
        text = rec.get("text", "") or ""
        source = rec.get("source", "") or ""
        n = len(text)
        if n <= size:
            chunks.append({"text": text, "source": source, "chunk_id": f"{source}#0"})
            continue

        start = 0
        i = 0
        step = size - overlap
        while start < n:
            end = min(start + size, n)
            chunk = text[start:end]
            chunks.append({"text": chunk, "source": source, "chunk_id": f"{source}#{i}"})
            if end == n:
                break
            start += step
            i += 1

    return chunks
