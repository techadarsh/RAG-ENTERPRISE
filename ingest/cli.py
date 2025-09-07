"""
Ingestion CLI (Typer).

Subcommands (sequential, but individually callable):
- load  --path <folder>                    -> writes .cache/loaded.json
- chunk --size 800 --overlap 150           -> writes .cache/chunked.json
- embed --batch 32                         -> writes .cache/embedded.json
- upsert                                   -> reads embedded json and upserts

All intermediate artifacts stored under .cache to keep runs deterministic and debuggable.
"""

from __future__ import annotations
import json
from pathlib import Path
import typer

from pipeline.loaders import load_folder
from pipeline.chunk import chunk_texts
from pipeline.embed import batch_embed
from pipeline.upsert_milvus import upsert

app = typer.Typer(help="Enterprise RAG ingestion CLI")
CACHE = Path(".cache")
CACHE.mkdir(exist_ok=True)

@app.command()
def load(path: str):
    items = load_folder(path)
    (CACHE / "loaded.json").write_text(json.dumps(items, ensure_ascii=False, indent=2))
    typer.echo(f"Loaded: {len(items)} items -> {CACHE/'loaded.json'}")

@app.command()
def chunk(size: int = 800, overlap: int = 150):
    data = json.loads((CACHE / "loaded.json").read_text())
    parts = chunk_texts(data, size=size, overlap=overlap)
    (CACHE / "chunked.json").write_text(json.dumps(parts, ensure_ascii=False, indent=2))
    typer.echo(f"Chunked: {len(parts)} parts -> {CACHE/'chunked.json'}")

@app.command()
def embed(batch: int = 32):
    parts = json.loads((CACHE / "chunked.json").read_text())
    texts = [p["text"] for p in parts]
    vecs = batch_embed(texts, batch_size=batch)
    assert len(vecs) == len(parts)
    for i, v in enumerate(vecs):
        parts[i]["embedding"] = v
    (CACHE / "embedded.json").write_text(json.dumps(parts, ensure_ascii=False, indent=2))
    typer.echo(f"Embedded: {len(parts)} vectors -> {CACHE/'embedded.json'}")

@app.command()
def upsert_milvus():
    parts = json.loads((CACHE / "embedded.json").read_text())
    # Reduce payload into minimal records for upsert
    recs = [{"text": p["text"], "source": p["source"], "embedding": p["embedding"]} for p in parts]
    upsert(recs)
    typer.echo(f"Upserted {len(recs)} records into Milvus")

if __name__ == "__main__":
    app()
