# Phase 2 — Vector Store + Embeddings + LLM

## 1. Introduction
Phase 2 implements the core retrieval-augmented generation (RAG) loop for the Enterprise RAG POC. This phase wires together:
- Milvus client helpers for vector storage and search
- Retrieval utilities for embedding queries and fetching top-k results
- LLM answer generation grounded in retrieved context
- The `/chat` route that exposes the end-to-end workflow via a single API call

**Goal:** Demonstrate a minimal, robust RAG workflow that works even when dependencies (Milvus, embeddings, Ollama) are not running, ensuring the system is resilient and developer-friendly.

---

## 2. Files and Responsibilities

### `api/app/store/milvus_client.py`
- **Purpose:** Ensure collection, upsert embeddings, search top-k
- **Technology:** pymilvus
- **Why:** Milvus is the leading open-source vector DB; strong community; free to run locally
- **Key details:** schema, index type (IVF_FLAT or HNSW), metric (COSINE or IP)

### `api/app/rag/retrieval.py`
- **Purpose:** `embed_query` + `retrieve_topk`
- **Technology:** httpx to embeddings service + pymilvus search
- **Why:** Decouples embedding provider from retrieval logic
- **Key details:** timeout handling, distance→score mapping

### `api/app/rag/llm.py`
- **Purpose:** `generate_answer` grounded in retrieved context
- **Technology:** httpx to Ollama local model
- **Why:** Local and free; avoids cloud API costs
- **Key details:** Safe fallback ("I don’t know"), prompt structure

### `api/app/routes/chat.py`
- **Purpose:** POST `/chat` route
- **Technology:** FastAPI route with Pydantic validation
- **Why:** Clean separation of transport vs business logic
- **Key details:** Input schema, graceful handling of missing deps

### `api/app/tests/test_retrieval.py`
- **Purpose:** Ensure `/chat` returns the correct shape
- **Why:** CI/CD safety, even with deps offline

---

## 3. Alternatives Considered
- **Milvus vs Pinecone vs Weaviate:** Milvus is open-source, easy to run locally, and has strong community support. Pinecone and Weaviate are managed/cloud-first and may incur costs or require API keys.
- **Embeddings service vs in-process model:** Using a separate embeddings service allows for language/model flexibility and easier scaling. In-process models are simpler but less flexible.
- **Ollama vs cloud APIs:** Ollama is local and free, ideal for POC and privacy. Cloud APIs (OpenAI, Cohere, etc.) offer more models but require API keys and may incur costs.
- **Retrieval only vs retrieval + reranker:** This phase implements retrieval only for simplicity and speed. Rerankers can improve answer quality and will be considered in future phases.

---

## 4. Enterprise Alignment
- **Security:** All services run locally; no API keys or external calls required.
- **Portability:** All components are Dockerized for easy deployment and reproducibility.
- **Observability:** Structured logs and request IDs for traceability.
- **Resilience:** Graceful fallbacks and error handling when dependencies are down.

---

## 5. Benefits of Phase 2
- First working RAG loop
- `/chat` endpoint is demo-ready
- System is robust to missing dependencies
- Lays the foundation for the ingestion pipeline (Phase 3)

---

## 6. Updated System Diagram
```
[user/browser] --> [ui:3000] --> [api:8080/chat]
    |--> retrieval.py --> Milvus
    |--> retrieval.py --> embeddings service
    |--> llm.py --> Ollama
```

---

## 7. Acceptance Criteria
- Importing Milvus client works without Milvus running
- `retrieve_topk("hello",3)` returns list (empty is fine before ingest)
- `generate_answer()` returns string even if Ollama is down
- `POST /chat` returns JSON with keys `answer` and `contexts`

---

## 8. Practical Notes & Gotchas
- **pydantic-settings quirks:** For Pydantic v2, use `pydantic-settings` and ensure all list fields (like `CORS_ORIGINS`) are set as valid JSON arrays in `.env`.
- **CORS wildcard handling:** Pydantic will not accept `"*"` as a valid URL in a list. Use explicit origins or handle wildcards in FastAPI CORS middleware.
- **marshmallow/environs pinning:** Some Milvus dependencies require `marshmallow>=3.13,<4.0` for compatibility with `environs`.
- **Distance→score mapping:** Milvus returns cosine distance; we map to a user-friendly score as `score = 1 - distance`.
- **API-only dev mode:** The system is robust to missing dependencies; endpoints return valid responses even if Milvus, embeddings, or Ollama are offline.
- **Docker registry pull issues:** If you encounter image pull errors, check your network and Docker Hub rate limits.

---

## 9. Future Enhancements
- Hybrid retrieval (BM25+vector)
- Reranker for better answer quality
- Streaming responses
- Citations in answers
- Observability metrics
