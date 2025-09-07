# Minimal embeddings HTTP service using sentence-transformers (free/local).
from typing import List
from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

app = FastAPI(title="Embeddings Service")

# Small model for fast POC; downloads on first run and is cached.
_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

class EncodeIn(BaseModel):
    texts: List[str]

class EncodeOut(BaseModel):
    vectors: List[List[float]]

@app.get("/health")
def health():
    return {"status": "ok", "model": "all-MiniLM-L6-v2"}

@app.post("/encode", response_model=EncodeOut)
def encode(inp: EncodeIn):
    vecs = _model.encode(inp.texts, convert_to_numpy=True).tolist()
    return EncodeOut(vectors=vecs)
