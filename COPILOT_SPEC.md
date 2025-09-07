Awesome—let’s give you a single “Master Build Spec” you can follow end-to-end. Paste the block below into Copilot Chat at the repo root (or in a top-level `COPILOT_SPEC.md`). This sets expectations for what to build, how to build it, and when it’s “done.” After you acknowledges, we’ll start Phase 0.

---

# MASTER BUILD SPEC — Enterprise RAG POC (Local, Dockerized)

## 0) Context and Goal

Build a fully local, Dockerized **Retrieval-Augmented Generation (RAG)** proof-of-concept:

* **LLM**: Mistral-7B via **Ollama** (quantized)
* **Embeddings**: **BGE-Large-EN v1.5** via a lightweight HTTP embeddings service
* **Vector DB**: **Milvus**
* **Backend**: **FastAPI**
* **Frontend**: **Next.js** (simple chat UI)
* **Optional metadata DB**: **Postgres** (for feedback/logs later)
  Everything must run via **docker-compose** on a single machine, with **clear comments/docstrings** and **no emojis**.

## 1) Deliverables (end-to-end)

1. **Working ingestion pipeline**: load files (.pdf, .docx, .md, .txt) → chunk → embed → upsert to Milvus.
2. **Backend REST API**:

   * `/` → service banner JSON
   * `/health` → `{"status":"ok"}`
   * `/health/deps` → readiness of Milvus, Embeddings, Ollama
   * `/chat` (POST) → RAG flow: retrieve top-k, prompt LLM with context, return `{"answer":..., "contexts":[...]}`.
3. **Frontend** (Next.js):

   * Minimal chat page with input, send button, answer display, and expandable list of supporting contexts.
4. **Dockerized system**:

   * Containers: `milvus`, `postgres` (optional), `ollama`, `embeddings`, `api`, `ingest`, `ui`
   * `docker-compose.yml` wires networking, volumes, healthchecks, and ports.
5. **Scripts & Makefile**:

   * Bootstrap script to pull the LLM and wait for health.
   * Ingest script to process a mounted `/data` folder.
   * Makefile shortcuts for up/down/build/logs/test.
6. **Tests**:

   * API health test.
   * Retrieval unit test with mocks.
7. **Docs**:

   * `README.md` quickstart, troubleshooting, architecture overview.
   * `docs/architecture.md` and `docs/data_governance.md`.

## 2) Code style & constraints

* **No emojis.**
* Production-quality comments and docstrings in every file.
* Type hints everywhere (Python/TS).
* Environment variables only (no hardcoded secrets).
* Functions small and single-responsibility.
* Clear error handling and timeouts for all network calls.
* Pin dependencies (requirements.txt / package.json).
* Tests fast and deterministic.

## 3) Repository layout (must match exactly)

```
rag-enterprise/
  README.md
  docker-compose.yml
  .env.example
  .env            # local-only, untracked
  makefile

  docs/
    architecture.md
    data_governance.md
    screenshots/

  api/
    app/
      __init__.py
      main.py
      deps.py
      routes/
        health.py
        chat.py
        admin.py
      core/
        config.py
        logging.py
      rag/
        retrieval.py
        rerank.py
        llm.py
        schema.py
      store/
        milvus_client.py
        postgres_client.py
      tests/
        test_health.py
        test_retrieval.py
    requirements.txt
    Dockerfile
    pyproject.toml (optional) 
    uv.lock (optional)

  ingest/
    pipeline/
      loaders.py
      chunk.py
      embed.py
      upsert_milvus.py
    cli.py
    tests/
      test_chunk.py
      test_embed.py
    Dockerfile

  ui/
    app/
      page.tsx
      api.ts
      components/
        Chat.tsx
        Message.tsx
    next.config.js
    package.json
    Dockerfile

  milvus/
    README.md

  pg/
    init.sql

  scripts/
    dev_bootstrap.sh
    ingest_sample.sh
```

## 4) Environment variables (`.env.example`)

Define defaults and read them in code:

```
API_HOST=0.0.0.0
API_PORT=8080
CORS_ORIGINS=http://localhost:3000

MILVUS_HOST=milvus
MILVUS_PORT=19530
MILVUS_COLLECTION=enterprise_docs

EMBEDDINGS_HOST=embeddings
EMBEDDINGS_PORT=8000
EMBEDDINGS_MODEL=BAAI/bge-large-en-v1.5

LLM_HOST=ollama
LLM_PORT=11434
LLM_MODEL=mistral:7b-instruct-q4_K_M
LLM_MAX_TOKENS=512
LLM_TEMP=0.2

PG_HOST=postgres
PG_PORT=5432
PG_DB=ragdb
PG_USER=rag
PG_PASSWORD=ragpass

LOG_LEVEL=INFO
```

## 5) Services (compose) and ports

* **milvus**: 19530 (gRPC), 9091 (metrics); embedded etcd/minio for POC.
* **postgres**: 5432 (optional use).
* **ollama**: 11434; must pull `mistral:7b-instruct-q4_K_M`.
* **embeddings**: 8000; HTTP endpoint `/encode` with payload `{"texts":[...]} -> {"vectors":[...]}`.
* **api**: 8080; FastAPI + Uvicorn; CORS for `http://localhost:3000`.
* **ingest**: on-demand CLI container; mount `/data` for documents.
* **ui**: 3000; Next.js.

## 6) Backend specifics

* **`core/config.py`**: Pydantic settings reading all envs; singleton `settings`.
* **`core/logging.py`**: JSON logs to stdout; request-id middleware; configurable log level.
* **`routes/health.py`**:

  * `GET /health` → `{"status":"ok"}`
  * `GET /health/deps` → probe Milvus, Embeddings, Ollama with fast timeouts; return status map.
* **`rag/retrieval.py`**:

  * `embed_query(query: str) -> list[float]` using embeddings HTTP service with timeouts/retries.
  * `retrieve_topk(query: str, k: int = 5) -> list[dict]` using Milvus; ensure collection exists; return `{text, source, score}`.
* **`store/milvus_client.py`**:

  * `ensure_collection(collection_name, dim)`: create with id (auto pk), vector (FLOAT\_VECTOR), text/source (VARCHAR). Create index (cosine/IP) and consistency level suitable for POC.
  * `upsert_texts([...])`: insert vectors + metadata.
  * `search_embeddings(embedding, k)`: top-k with distances mapped to scores.
* **`rag/llm.py`**:

  * `generate_answer(user_query, contexts) -> str`: build grounded prompt with context bullets; call Ollama `/api/generate`; strict “answer from context or say I don't know”.

## 7) Ingestion pipeline

* **`loaders.py`**: walk a folder recursively, read `.pdf` (pdfminer.six), `.docx` (python-docx), `.md`, `.txt`; return list of `{"text","source"}`. Clean whitespace; skip very short fragments.
* **`chunk.py`**: `chunk_texts(records, size=800, overlap=150)` char-approx tokenization; return chunked items with `chunk_id`.
* **`embed.py`**: `batch_embed(texts, batch_size=32)` calls embeddings HTTP endpoint; retries/backoff; order preserved.
* **`upsert_milvus.py`**: `upsert(records)` ensures collection (correct dim), embeds in batches, then upserts into Milvus.
* **`cli.py`**: Click/Typer CLI with subcommands:

  * `load --path <folder>`
  * `chunk --size 800 --overlap 150`
  * `embed --batch 32`
  * `upsert --collection enterprise_docs`
    Uses a `.cache/` directory for intermediate JSON artifacts.

## 8) Frontend (Next.js)

* **`ui/app/api.ts`**: `postChat(query: string, topK=5)` → calls `NEXT_PUBLIC_API_BASE + /chat`; returns `{answer, contexts}` with error handling.
* **`ui/app/components/Message.tsx`**: stateless message view for user/assistant.
* **`ui/app/components/Chat.tsx`**: form input, submit; shows answer and expandable list of contexts (source + excerpt).
* **`ui/app/page.tsx`**: render `<Chat/>` with a heading “Enterprise RAG POC”.

## 9) Dockerfiles

* **`api/Dockerfile`**: Python 3.11 slim; install pinned `requirements.txt`; copy app; expose 8080; `CMD uvicorn app.main:app --host 0.0.0.0 --port 8080`.
* **`ingest/Dockerfile`**: Python 3.11; same base libs; entrypoint `["python","-m","pipeline.cli"]` (we will run via `docker exec` in POC).
* **`ui/Dockerfile`**: Node 20 multi-stage; install deps, build, `next start`; expose 3000.

## 10) docker-compose.yml

* Define all 7 services with:

  * Containers’ names, images/build contexts.
  * Ports mapping.
  * Volumes for Milvus, Postgres, Ollama models.
  * `env_file: .env` for `api` and `ingest`.
  * Healthchecks for Ollama and API.
  * Comments explaining each service and why.

## 11) Scripts & Makefile

* **`scripts/dev_bootstrap.sh`**:

  * Pull mistral model inside `ollama` container.
  * Wait for `api /health` and Milvus readiness.
  * Print summary table of statuses.
* **`scripts/ingest_sample.sh`**:

  * Run `load -> chunk -> embed -> upsert` against `/data` mount.
  * Print Milvus collection stats.
* **`makefile`**:

  * `up`, `down`, `rebuild`, `logs`, `api-shell`, `ingest-shell`, `pull-models`, `test`.

## 12) Tests

* **`api/app/tests/test_health.py`**: FastAPI test client; assert `/health` returns status ok.
* **`api/app/tests/test_retrieval.py`**: mock embeddings+Milvus; ensure `retrieve_topk()` returns a list of dicts with required keys.

## 13) Documentation

* **`README.md`**:

  * Overview, architecture ASCII diagram, quickstart, ingest example, chat example, troubleshooting (Milvus index, Ollama model).
* **`docs/architecture.md`**: short narrative of flow and components.
* **`docs/data_governance.md`**: note POC-only data handling, no public exposure.

## 14) Definition of Done (acceptance)

* `docker compose up -d --build` brings up all services without errors.
* `curl localhost:8080/health` → `{"status":"ok"}`
* `scripts/dev_bootstrap.sh` pulls the model and prints healthy statuses.
* `scripts/ingest_sample.sh` successfully loads a small mounted folder of docs and upserts to Milvus.
* POST `/chat` with a query about ingested docs returns an answer and non-empty contexts.
* `pytest` in the API container passes the included tests.
* `README.md` instructions reproduce the above on a clean machine.

---

Please start generating files **phase-wise**. Each file must include clear comments/docstrings and pinned dependencies. Do not skip Docker or healthchecks. After scaffolding, ensure compose stands up cleanly before moving to ingestion and UI.

---