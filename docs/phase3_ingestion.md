# Phase 3 — Ingestion Pipeline

## 1. Introduction
Phase 3 implements the ingestion pipeline for the Enterprise RAG POC, enabling the transformation of raw documents into vectorized, searchable chunks in Milvus. The flow consists of four deterministic, auditable steps: load documents, chunk text, embed in batches, and upsert to Milvus. Each step produces intermediate `.cache` artifacts for reproducibility, debugging, and auditability. The pipeline is designed for robustness, stable ordering, and graceful error handling, ensuring that ingestion is reliable and easy to debug in enterprise settings.

---

## 2. Files and Responsibilities

### `ingest/pipeline/loaders.py`
- **Purpose:** Recursively loads documents from a folder, supporting `.pdf` (via pdfminer.six), `.docx` (via python-docx), `.md`, and `.txt` (plain UTF-8 text).
- **Technology Choices:**
  - `pdfminer.six` for robust PDF extraction (widely used, handles most PDFs).
  - `python-docx` for .docx files (standard for Word documents).
  - Built-in text decoding for `.md` and `.txt`.
- **Why:** These libraries are open-source, well-maintained, and provide reliable extraction for the most common enterprise document formats.
- **Normalization:** All text is cleaned (collapsed whitespace, stripped nulls), and fragments under 20 characters are skipped to avoid noise.
- **Deterministic Ordering:** Files are loaded in sorted order for reproducibility, ensuring that repeated runs produce the same outputs.

### `ingest/pipeline/chunk.py`
- **Purpose:** Splits loaded documents into overlapping character-based chunks for embedding and retrieval.
- **Rationale:** Character-based chunking is fast, deterministic, and approximates token boundaries well enough for a POC, without requiring heavy tokenizer dependencies.
- **size/overlap Semantics:** Each chunk is of length `size` (default 800), with `overlap` (default 150) characters shared between adjacent chunks. This ensures context continuity and stable chunk boundaries.
- **Stability:** The chunking logic is deterministic and produces stable chunk IDs for traceability.

### `ingest/pipeline/embed.py`
- **Purpose:** Batches text chunks and sends them to the embeddings service via HTTP for vectorization.
- **Technology:** Uses `httpx` for HTTP calls, with configurable batch size, retries, and backoff for transient errors.
- **Why:** HTTP batching is efficient and decouples the embedding model from the pipeline, allowing for easy upgrades or swaps.
- **Stable Ordering Guarantee:** The output vectors are guaranteed to correspond to the input texts, preserving order for downstream upsert.
- **Timeouts and Retries:** Short timeouts and exponential backoff ensure the pipeline is robust to slow or flaky embedding services.

### `ingest/pipeline/upsert_milvus.py`
- **Purpose:** Ensures the Milvus collection exists and upserts the embedded chunks with source metadata.
- **Technology:** Reuses the API's Milvus client helpers for schema and index consistency, or minimally duplicates logic if needed for container isolation.
- **Why:** Centralizing Milvus logic ensures schema alignment and reduces maintenance overhead.
- **Trade-offs:** Reusing API helpers avoids duplication but may require shared config or code; minimal duplication is acceptable for container independence.

### `ingest/cli.py`
- **Purpose:** Provides a Typer-based CLI to orchestrate the ingestion pipeline, with subcommands for each step.
- **.cache Intermediates:** All intermediate artifacts are written to `.cache/` for reproducibility and debugging.
- **How to Run:** Each step can be run independently or in sequence. Example:
  - **Mount some local docs into ingest container via compose (e.g., ./data -> /data)**
  - `docker compose exec ingest python -m pipeline.cli load --path /data`
  - `docker compose exec ingest python -m pipeline.cli chunk --size 800 --overlap 150`
  - `docker compose exec ingest python -m pipeline.cli embed --batch 16`
  - `docker compose exec ingest python -m pipeline.cli upsert-milvus`


---

## 3. Alternatives Considered
- **Token-aware chunking (tiktoken) vs char-based:** Token-aware chunking provides more accurate context windows but requires additional dependencies and is slower. Char-based chunking is fast, simple, and sufficient for a POC.
- **LangChain ingestion vs custom thin pipeline:** LangChain offers a rich ingestion framework but adds complexity and less control. A custom pipeline is lightweight, auditable, and easier to debug.
- **Staging to RDBMS then upsert vs direct to Milvus:** Staging in a relational DB allows for richer metadata and deduplication but adds operational overhead. Direct upsert is simpler and faster for a POC.

---

## 4. Enterprise Alignment
- **Deterministic Artifacts:** All intermediate outputs are written to `.cache/`, supporting audits, debugging, and reproducibility.
- **Separation of Steps:** Each pipeline stage is modular, enabling parallelization, scaling, and easier troubleshooting.
- **Resilience:** Short timeouts, retries, and graceful error handling ensure the pipeline is robust to transient failures and partial outages.

---

## 5. Acceptance Criteria
- The CLI `--help` command works inside the container and lists all subcommands.
- Running the full pipeline (`load` → `chunk` → `embed` → `upsert-milvus`) on sample documents completes without exceptions and produces `.cache` outputs at each stage.
- Upserted records are visible in Milvus and can be retrieved via the API (as verified in Phase 2 tests).

---

## 6. Practical Notes & Gotchas
- **Where to mount `/data`:** Ensure your Docker Compose mounts a local folder (e.g., `./data`) to `/data` in the ingest container for document loading.
- **Env reuse between API and Ingest containers:** Share environment variables or config files to ensure both containers use the same Milvus and embeddings endpoints.
- **Handling PDFs that extract poorly:** Some PDFs may yield poor or empty text; consider manual review or fallback strategies for critical documents.
- **Batching parameters and retry strategy:** Tune batch size and retry/backoff settings for your embedding service and hardware.
- **Index/metric alignment with Phase 2 retrieval:** Ensure the Milvus index and metric type match those used in the retrieval pipeline for consistent results.

---

## 7. Future Enhancements
- Token-aware chunking and language detection for better context windows.
- Deduplication and richer source-level metadata for improved search quality.
- Incremental re-indexing and upsert deduplication to support ongoing document updates.
- Quality gates (minimum length, stopword filters) to filter out low-value chunks before embedding.
