# Phase 0 — Project Scaffolding & Setup

## 1. Introduction

Phase 0 of the Enterprise RAG POC establishes the foundational scaffolding and configuration required for a robust, maintainable, and reproducible local development environment. The goal is to ensure that all team members and stakeholders can reliably build, run, and extend the system using Docker, with clear boundaries between services and deterministic dependency management. This groundwork is essential for the rapid, error-free development of subsequent phases.


## 2. Hygiene & Config Files (Detailed)

### .gitignore
**Purpose:**  Prevents accidental commits of files that are machine-specific, sensitive, or generated during builds and tests.
**What it excludes:**
- Python caches (`__pycache__`, `.pyc`, `.pytest_cache/`, `.mypy_cache/`)
- Node.js build and dependency folders (`node_modules/`, `.next/`, `.turbo/`, `.pnpm-store/`)
- Local environment and secret files (`.env`, `.env.local`)
- Docker volumes and logs (`docker-data/`, `volumes/`, `*.log`)
- Editor and OS-specific files (`.vscode/`, `.idea/`, `.DS_Store`)
**Why:**  Keeps the repository clean, secure, and portable. Prevents “works on my machine” issues and accidental leakage of secrets.

### .editorconfig
**Purpose:**  Enforces consistent code formatting across all editors and IDEs.
**What it does:**
- Sets UTF-8 encoding, LF line endings, and consistent indentation (4 spaces for Python, 2 for JS/TS/MD).
**Why:**  Reduces merge conflicts, ensures codebase consistency, and makes collaboration seamless regardless of editor.

### README.md
**Purpose:**  Provides a high-level overview of the project, its stack, quickstart instructions, and repository layout.
**Why:**  Essential for onboarding, sharing with stakeholders, and as a reference for contributors.
**Technology:**  Markdown is the universal standard for project documentation.


## 3. Dependency Manifests (Detailed)

### api/requirements.txt
**Purpose:**  Pins all Python dependencies for the backend and ingestion pipeline.
**Key Technologies:**
- **FastAPI:** Modern, high-performance Python web framework for APIs. Chosen for its async support, speed, and type safety.
- **Uvicorn:** Lightning-fast ASGI server, ideal for FastAPI.
- **Pydantic:** Industry-standard for data validation and settings management.
- **PyMilvus:** Official Milvus client, best for vector DB integration.
- **pdfminer.six, python-docx:** Best-in-class for PDF and DOCX parsing.
- **pytest, pytest-asyncio:** Gold standard for Python testing.
**Why:**  Pinning ensures deterministic builds and avoids “dependency hell.” All libraries are widely adopted, well-maintained, and best-in-class for their roles.

### ui/package.json
**Purpose:**  Pins all Node.js dependencies for the frontend.
**Key Technologies:**
- **Next.js:** The leading React meta-framework for production apps, with SSR and static export.
- **React:** The most popular UI library for web apps.
- **TypeScript:** Adds type safety to JavaScript, improving maintainability.
- **ESLint:** Industry standard for code linting.
**Why:**  Pinned versions ensure reproducible builds. Next.js and React are the most widely used and supported frontend stack for modern web apps.


## 4. Docker Setup (Detailed)

### api/Dockerfile
**Purpose:**  Defines a reproducible, minimal, and secure environment for the FastAPI backend.
**Technology:**
- **python:3.11-slim:** Official, minimal Python image for security and speed.
- **System deps:** Installs only what’s needed for document parsing.
- **Layer caching:** Installs requirements before copying code for faster rebuilds.
**Why:**  Ensures the backend runs identically everywhere, with a small attack surface and fast build times.

### ingest/Dockerfile
**Purpose:**  Provides a separate container for the ingestion CLI, decoupled from the API.
**Technology:**
- **python:3.11-slim:** Same as API for consistency.
- **ENTRYPOINT:** Runs CLI for modular, on-demand ingestion.
**Why:**  Separation of concerns: ingestion can be run independently, scaled, or debugged without affecting the API.

### ui/Dockerfile
**Purpose:**  Multi-stage build for the Next.js frontend, producing a minimal production image.
**Technology:**
- **Node 20:** Latest LTS, best for Next.js 14.
- **npm ci:** Clean, reproducible dependency install.
- **Multi-stage:** Only production files in final image.
**Why:**  Reduces image size, improves security, and ensures fast, reliable deployments.

### docker-compose.yml
**Purpose:**  Orchestrates all services for local development and testing.
**Services:**
- **milvus:** Best-in-class open-source vector DB for semantic search.
- **postgres:** Industry-standard relational DB for metadata.
- **ollama:** Containerized LLM runner for Mistral-7B.
- **embeddings:** Lightweight HTTP service for BGE-Large-EN embeddings.
- **api:** FastAPI backend.
- **ingest:** Ingestion CLI.
- **ui:** Next.js frontend.
**Why:**  Compose is the de facto standard for local multi-service orchestration. Healthchecks, volumes, and comments ensure maintainability and reliability.


## 5. Automation (Detailed)

### makefile
**Purpose:**  Provides developer-friendly shortcuts for common Docker Compose operations.
**Why:**  Reduces manual errors, speeds up workflows, and standardizes commands across the team.

### scripts/dev_bootstrap.sh
**Purpose:**  Automates model pulling, health checks, and service status reporting.
**Why:**  Saves setup time, ensures all dependencies are ready, and provides clear feedback to the user.

### scripts/ingest_sample.sh
**Purpose:**  Automates the full ingestion pipeline for sample documents.
**Why:**  Ensures ingestion steps are run in the correct order, simplifies testing, and provides a repeatable workflow.


## 6. Benefits of Phase 0 Choices (Expanded)

- **Docker-first:** Guarantees isolation, reproducibility, and “it just works” for all contributors.
- **Pinned dependencies:** Prevents breakage from upstream changes, ensuring stable builds.
- **Environment-driven config:** Secure, portable, and production-ready.
- **Service separation:** Modular, scalable, and easier to test and maintain.
- **Best-in-class technologies:** Every major component (FastAPI, Next.js, Milvus, etc.) is widely adopted, well-documented, and proven in production.


## 7. How Phase 0 Prepares for Next Phase (Expanded)

- **Backend:** Ready for config, logging, and health endpoints in a robust container.
- **Ingestion:** Modular pipeline can be developed and tested independently.
- **Frontend:** Modern UI stack is ready for rapid prototyping and iteration.
- **Compose:** Ensures all services are networked and can be tested end-to-end locally.

Phase 0 provides a solid, professional foundation for the Enterprise RAG POC, enabling efficient, reliable progress in all subsequent phases.


## 8. Alternatives Considered (and Why Rejected)

For each major technology choice, alternatives were evaluated for suitability, maturity, and alignment with project goals:

- **FastAPI vs Flask vs Django:**
	- *Chosen:* FastAPI for its async support, modern design, and type safety. Flask is synchronous and less type-safe; Django is heavyweight for an API-first microservice.
- **Milvus vs Pinecone vs Weaviate:**
	- *Chosen:* Milvus for being open-source, free, and having an active community. Pinecone is commercial/SaaS; Weaviate is good but Milvus is more widely adopted in open-source RAG.
- **Ollama vs OpenAI API vs Hugging Face Inference API:**
	- *Chosen:* Ollama for free, local, and secure LLM inference. OpenAI/Hugging Face require cloud, incur cost, and may raise data privacy concerns.
- **Next.js vs plain React vs Angular:**
	- *Chosen:* Next.js for server-side rendering, production readiness, and best-in-class React developer experience. Plain React lacks SSR; Angular is less common for modern data-centric UIs.

This critical evaluation ensures the stack is robust, future-proof, and cost-effective for a local POC.

## 9. How Phase 0 Aligns with Enterprise Standards

- **Security:** All secrets and credentials are managed via `.env` files, never hardcoded, reducing risk of accidental leakage.
- **Portability:** Docker ensures the stack runs identically on any OS, eliminating “works on my machine” issues.
- **Scalability Path:** The separation of services mirrors production microservices, making it easy to scale or migrate to cloud-native deployments in the future.

## 10. Architecture Diagram

Below is a simple ASCII diagram showing how services are wired together in Docker Compose:

```
[user/browser] --> [ui:3000] --> [api:8080] --> [milvus:19530]
																 |--> [ollama:11434]
																 |--> [embeddings:8000]
																 |--> [postgres:5432]
```

This illustrates the flow from user to UI, through the API, and out to the supporting services.

## 11. Contribution Guidelines (Mini)

- New contributors should add dependencies only via `requirements.txt` (Python) or `package.json` (Node).
- Always write docstrings and comments in every file to maintain code quality and clarity.
- Run `make test` before pushing to ensure all tests pass and the stack remains stable.

These guidelines help maintain a high standard of code quality and project hygiene.

## 12. Future Extension Hooks

- `docs/screenshots/`: For adding screenshots to support documentation and mid-semester submissions.
- `api/app/tests/`: Placeholder for more unit and integration tests as the system grows.
- `pg/init.sql`: Schema migration and initialization for metadata logging and future analytics.
- `scripts/`: Room for more automation scripts, e.g., for CI/CD, dataset refresh, or monitoring.

This structure anticipates future needs and makes it easy to extend the project in later phases.

## 13. Why This Matters for Mid-Semester Report

Phase 0 demonstrates:
- The ability to set up a cloud-native, microservices-inspired architecture locally using best-in-class open-source tools.
- Consideration of security, portability, and reproducibility from the outset.
- A solid, professional baseline for demonstration and further development, even before core features are implemented.

This scaffolding is not just technical overhead—it is proof of engineering discipline, readiness for rapid iteration, and a foundation for a successful mid-semester submission and beyond.
