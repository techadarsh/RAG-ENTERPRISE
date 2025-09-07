# Enterprise RAG POC — Build Checklist

> Tick items as you complete them. Each checkbox should correspond to one commit.

## Phase 0 — Scaffolding & Setup
- ✅ `.gitignore`, `.editorconfig`, scaffold `README.md`
- ✅ Pinned deps: `api/requirements.txt`, `ui/package.json`
- ✅ Dockerfiles: `api/`, `ingest/`, `ui/`
- ✅ `docker-compose.yml` with services, volumes, healthchecks
- ✅ `makefile`, `scripts/dev_bootstrap.sh`, `scripts/ingest_sample.sh`
- ✅ `docs/phase0_setup.md` detailed rationale

## Phase 1 — Backend Core (config, logging, health)
- ✅ `api/app/core/config.py` (Pydantic Settings)
- ✅ `api/app/core/logging.py` (JSON/logfmt, request-id middleware)
- ✅ `api/app/main.py` (FastAPI entrypoint + CORS + root)
- ✅ `api/app/routes/health.py` (`/health`, `/health/deps`)
- ✅ `api/app/deps.py` (stubs)
- ✅ `api/app/tests/test_health.py` (pytest)
- ✅ `docs/phase1_backend.md` (detailed write-up)

## Phase 2 — Vector Store + Embeddings + LLM
- ✅ `api/app/store/milvus_client.py` (ensure, upsert, search)
- ✅ `api/app/rag/retrieval.py` (embed_query, retrieve_topk)
- ✅ `api/app/rag/llm.py` (generate_answer with grounded prompt)
- ✅ `api/app/routes/chat.py` (POST /chat)
- ✅ `api/app/tests/test_retrieval.py` (mocked)
- ✅ `docs/phase2_vector_llm.md` (detailed write-up)

## Phase 3 — Ingestion Pipeline
- ✅ `ingest/pipeline/loaders.py` (pdf/docx/md/txt)
- ✅ `ingest/pipeline/chunk.py` (size+overlap)
- ✅ `ingest/pipeline/embed.py` (batch HTTP embeddings)
- ✅ `ingest/pipeline/upsert_milvus.py` (ensure + upsert)
- ✅ `ingest/cli.py` (Typer/Click with cache)
- ✅ `docs/phase3_ingestion.md` (detailed write-up)

## Phase 4 — Frontend (Next.js Chat UI)
- [ ] `ui/app/api.ts` (postChat)
- [ ] `ui/app/components/Message.tsx`
- [ ] `ui/app/components/Chat.tsx`
- [ ] `ui/app/page.tsx`
- [ ] `docs/phase4_ui.md` (detailed write-up)

## Phase 5 — Docker & Run
- [ ] Polish `api/`, `ingest/`, `ui/` Dockerfiles
- [ ] Finalize `docker-compose.yml`
- [ ] `make up` + scripts verified end-to-end
- [ ] `docs/phase5_docker_run.md`

## Phase 6 — Compose, Scripts, Smoke Tests
- [ ] Smoke tests pass locally (`/health`, `/chat`)
- [ ] `scripts/dev_bootstrap.sh` stable, idempotent
- [ ] `scripts/ingest_sample.sh` runs full pipeline
- [ ] `docs/phase6_smoke_tests.md`

## Phase 7 — Minimal Tests & QA
- [ ] `api/app/tests/` expanded (retrieval, ingestion mocks)
- [ ] Optional simple UI e2e smoke (manual steps OK)
- [ ] `docs/phase7_testing.md`

## Phase 8 — README & Final Docs
- [ ] Final `README.md` (diagram, quickstart, troubleshooting, security notes)
- [ ] All phase docs complete with screenshots in `docs/screenshots/`
- [ ] Tag release `phase-midsem`
