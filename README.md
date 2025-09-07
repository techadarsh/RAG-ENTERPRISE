# Enterprise RAG POC (Local, Dockerized)

## Purpose
A fully local, Dockerized Retrieval-Augmented Generation (RAG) proof-of-concept for enterprise document Q&A and chat.

## Stack
- LLM: Mistral-7B via Ollama
- Embeddings: BGE-Large-EN v1.5 (HTTP service)
- Vector DB: Milvus
- Backend: FastAPI (Python 3.11)
- Frontend: Next.js (Node 20)
- Optional metadata DB: Postgres
- Orchestration: docker-compose

## Quickstart
```sh
docker compose up --build
./scripts/dev_bootstrap.sh
./scripts/ingest_sample.sh
# Access chat UI at http://localhost:3000
# Test chat endpoint:
curl -X POST http://localhost:8080/chat -H 'Content-Type: application/json' -d '{"query": "<your question>"}'
```

## Repository Layout
```
rag-enterprise/
  README.md
  docker-compose.yml
  .env.example
  .env
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
    pyproject.toml
    uv.lock
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

## Running Tests

You can run tests for the backend and ingestion pipeline using `pytest`. Make sure dependencies are installed (see Quickstart above) and the relevant containers are up if needed.

### API Backend Tests
```sh
cd api
pytest
```

### Ingestion Pipeline Tests
```sh
cd ingest
pytest
```

> All test files are located in their respective `tests/` subdirectories. Tests are designed to run in isolation and use mocks for external dependencies where possible.

## Note
All services are local-only for POC and not intended for production or public exposure.
