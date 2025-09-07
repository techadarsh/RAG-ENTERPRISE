"""
POST /chat endpoint: retrieval + generation.

Input:
{ "query": str, "top_k": int = 5 }

Output:
{ "answer": str, "contexts": [ {text, source, score} ] }
"""

from typing import List, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, conint

from app.rag.retrieval import retrieve_topk
from app.rag.llm import generate_answer

router = APIRouter()


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, description="User question")
    top_k: conint(ge=1, le=20) = 5


class ChatResponse(BaseModel):
    answer: str
    contexts: List[Dict]


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    try:
        contexts = retrieve_topk(req.query, k=req.top_k)
    except Exception as e:
        # Embeddings or Milvus may be down; handle gracefully for POC
        contexts = []

    try:
        answer = generate_answer(req.query, contexts)
    except Exception:
        answer = "I don't know"

    return ChatResponse(answer=answer, contexts=contexts)
