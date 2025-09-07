"""
LLM generation via local Ollama.

- Build a grounded prompt: system role + bullet-point contexts.
- Instruct to answer strictly from context; else say "I don't know".
- Call http://{LLM_HOST}:{LLM_PORT}/api/generate with model=settings.LLM_MODEL
- Short timeouts, robust error handling.
"""

from typing import List, Dict
import httpx
from app.core.config import settings


def _build_prompt(user_query: str, contexts: List[Dict]) -> str:
    bullets = []
    for c in contexts:
        src = str(c.get("source", ""))
        txt = str(c.get("text", ""))[:800]
        bullets.append(f"- Source: {src} | Excerpt: {txt}")
    ctx_block = "\n".join(bullets) if bullets else "- No context available."

    return (
        "You are an enterprise RAG assistant. Answer ONLY from the provided context. "
        'If the context is insufficient, reply exactly with: "I don\'t know".\n\n'
        "Context:\n"
        f"{ctx_block}\n\n"
        f"User question: {user_query}\n\n"
        "Answer:"
    )


def generate_answer(user_query: str, contexts: List[Dict]) -> str:
    """
    Call Ollama's /api/generate endpoint and return the model's text.

    Returns
    -------
    str
        Assistant answer text (may be "I don't know" per instructions).
    """
    prompt = _build_prompt(user_query, contexts)
    url = f"http://{settings.LLM_HOST}:{settings.LLM_PORT}/api/generate"
    payload = {
        "model": settings.LLM_MODEL,
        "prompt": prompt,
        "options": {"temperature": settings.LLM_TEMP},
        # non-stream for simplicity
        "stream": False,
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
            text = data.get("response") or data.get("text") or ""
            return str(text).strip()
    except Exception as e:
        # For POC: return a graceful message rather than raising.
        return "I don't know, at this moment !"
