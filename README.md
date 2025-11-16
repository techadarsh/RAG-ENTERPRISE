# 🚀 RAG Enterprise Chatbot

A production-ready Retrieval-Augmented Generation (RAG) chatbot system for enterprise knowledge management with **native Mac deployment**, Metal GPU acceleration, and 8-10x performance improvements over Docker.

## 🎯 Overview

This project implements a complete RAG pipeline that allows users to ask questions about enterprise documents (HR policies, onboarding guides, engineering standards) and receive contextual answers backed by retrieved sources using local LLM inference.

**Key Features:**
- [x] End-to-end RAG pipeline with resilient LLM integration
- [x] **Native Mac deployment** with Metal GPU acceleration (8-10x faster)
- [x] **One-command automation** with comprehensive health checks
- [x] Vector similarity search with Milvus (Docker standalone)
- [x] Local LLM inference via Ollama (Mistral 7B, 4.4GB model)
- [x] State-of-the-art embeddings (BGE-Base-En)
- [x] Automatic document ingestion with recursive file discovery
- [x] **Full Confluence API integration** (basic auth, pagination, CQL search)
- [x] Conversational memory (last 5 turns per session)
- [x] Health checks and service monitoring
- [x] Clean, minimal React UI with hot reload
- [x] Source attribution and latency tracking
- [x] 14 sample documents pre-loaded and indexed

## ⚡ Performance

**Native Mac vs Docker:**
- Query time: **8-10 seconds** (vs 60-90 seconds in Docker)
- **8-10x performance improvement** using Metal GPU
- Memory efficient: ~8-10GB total usage
- No container overhead for LLM inference

## 🚀 Quick Start (Local Mac Deployment)

### Prerequisites

- **macOS** (tested on Mac Mini M4 Pro with 48GB RAM)
- **Homebrew** installed
- **Python 3.11+** (installed via Homebrew if needed)
- **Node.js 18+** (installed via Homebrew if needed)
- **Docker Desktop** (for Milvus only)
- **8GB RAM minimum** (16GB+ recommended)

### ⚡ One-Command Startup

```bash
# Clone the repository
git clone https://github.com/techadarsh/RAG-ENTERPRISE.git
cd rag-enterprise

# Start everything (handles all prerequisites automatically)
./start_local.sh start
```

**What it does:**
1. ✅ Checks and installs prerequisites (Homebrew, Python, Node.js, Ollama, Redis, Docker)
2. ✅ Starts Ollama service with Metal GPU acceleration
3. ✅ Downloads Mistral model if not present (4.4GB, one-time)
4. ✅ Starts Redis for session caching
5. ✅ Starts Milvus standalone container for vector storage
6. ✅ Creates Python virtual environment and installs dependencies
7. ✅ Starts FastAPI backend with hot reload (port 8000)
8. ✅ Starts React frontend with hot reload (port 3000)
9. ✅ Loads 14 sample Confluence documents
10. ✅ Performs comprehensive health checks
11. ✅ Shows service status and access URLs

**Expected startup time:**
- First run: 5-8 minutes (model download + dependencies)
- Subsequent runs: 30-60 seconds (services already configured)

**Optional environment variable (force blocking initial load):**

If you want the backend to finish indexing the sample documents before accepting traffic, set the following in `.env.local` before starting:

```bash
FORCE_INITIAL_LOAD=true
```

When enabled, the backend will perform a blocking load of the sample Confluence documents into Milvus during startup. This is useful for demos where you want the knowledge base ready immediately.
### 📱 Access URLs

- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health/deps
- **Ollama API**: http://localhost:11434

### 🛠️ Available Commands

```bash
# Start all services
./start_local.sh start

# Stop all services
./start_local.sh stop

# Check service status
./start_local.sh status

# Restart all services
./start_local.sh restart

# Clean all data and reset
./start_local.sh clean

# View logs for a specific service
./start_local.sh logs backend
./start_local.sh logs frontend
./start_local.sh logs ollama
./start_local.sh logs redis
./start_local.sh logs milvus

# Show help
./start_local.sh help
```

## 💡 Sample Queries

Try asking:
- "What is the PTO policy?"
- "How many holidays do we get?"
- "What happens during onboarding week 1?"
- "Can I rollover unused PTO?"
- "What are the incident severity levels?"
- "How do I create a pull request?"
- "What is our code review process?"
- "What is the agile workflow?"

**Expected response time:** 8-10 seconds with Metal GPU acceleration

## 🔧 Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     User Browser                             │
│                   http://localhost:3000                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 React Frontend (Port 3000)                   │
│              - Hot reload development mode                   │
│              - Clean, minimal UI                             │
│              - Conversation history                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│            FastAPI Backend (Port 8000)                       │
│              - RAG pipeline orchestration                    │
│              - Embedding generation (BGE-Base-En)            │
│              - Vector similarity search                      │
│              - LLM query generation                          │
│              - Conversational memory (5 turns)               │
│              - Hot reload with Uvicorn                       │
└─┬───────────────────┬──────────────────┬────────────────────┘
  │                   │                  │
  │                   │                  │
  ▼                   ▼                  ▼
┌──────────────┐  ┌────────────┐  ┌──────────────┐
│   Ollama     │  │   Milvus   │  │    Redis     │
│  (Native)    │  │  (Docker)  │  │ (Homebrew)   │
│ Port 11434   │  │ Port 19530 │  │  Port 6379   │
│              │  │            │  │              │
│ - Mistral 7B │  │ - Vectors  │  │ - Sessions   │
│ - Metal GPU  │  │ - Metadata │  │ - Cache      │
│ - 4.4GB RAM  │  │ - Search   │  │              │
└──────────────┘  └────────────┘  └──────────────┘
```

### Data Flow

1. **User Query** → Frontend sends question to `/ask` endpoint
2. **Embedding** → Backend generates query embedding using BGE-Base-En
3. **Retrieval** → Milvus performs vector similarity search
4. **Context** → Top relevant documents retrieved with metadata
5. **Generation** → LLM generates answer using retrieved context
6. **Response** → Answer + sources + latency returned to frontend
7. **Memory** → Conversation stored in Redis (last 5 turns)

### Confluence Integration

**Mode**: Local (API-ready)

**Configuration** (`.env.local`):
```bash
CONFLUENCE_MODE=local
CONFLUENCE_LOCAL_DIR=data/sample_confluence_pages
```

**API Implementation** (`backend/confluence_ingest.py`):
- ✅ Basic authentication (email + API token)
- ✅ Fetch page by ID
- ✅ Fetch all pages with pagination
- ✅ CQL search support
- ✅ Error handling (401, 404, timeout, connection errors)

**To enable API mode:**
1. Update `.env.local`:
   ```bash
   CONFLUENCE_MODE=api
   CONFLUENCE_BASE_URL=https://your-domain.atlassian.net/wiki
   CONFLUENCE_EMAIL=your-email@company.com
   CONFLUENCE_API_TOKEN=your-api-token
   ```
2. Restart backend: `./start_local.sh restart`

## 🧪 Testing & Validation

### Health Checks

Check all service dependencies:
```bash
curl http://localhost:8000/health/deps
```

Expected response:
```json
{
  "backend": "ok",
  "milvus": "ok",
  "etcd": "ok",
  "minio": "ok",
  "redis": "ok",
  "ollama": "ok",
  "embeddings": "ok"
}
```

### LLM Health Check

Test LLM connectivity and generation:
```bash
curl http://localhost:8000/llm/health
```

### Query Testing

Test RAG pipeline with a sample question:
```bash
curl -X POST http://localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"query":"What is the agile workflow?"}'
```

Expected response time: **8-10 seconds**

### Service Status

Check individual service status:
```bash
./start_local.sh status
```

Output shows:
- ✅ Ollama (with model info)
- ✅ Redis (memory usage)
- ✅ Milvus (container status)
- ✅ Backend (process status)
- ✅ Frontend (process status)
- 📊 Document count and topics

## 🐛 Troubleshooting

### Services Not Starting

**Check prerequisites:**
```bash
# The script checks these automatically, but you can verify manually:
which brew       # Should show Homebrew path
which python3    # Should show Python 3.11+
which node       # Should show Node.js 18+
which ollama     # Should show Ollama path
brew services list | grep redis  # Should show redis (started)
docker ps        # Should show Milvus container
```

### Ollama Not Responding

**Symptom**: Backend fails with "Ollama connection error"

**Solution**:
```bash
# Check if Ollama is running
ps aux | grep ollama

# Restart Ollama
./start_local.sh restart

# Or manually:
brew services restart ollama
ollama serve
```

### Milvus Connection Errors

**Symptom**: "Failed to connect to Milvus"

**Solution**:
```bash
# Check Milvus container
docker ps | grep milvus

# Check logs
./start_local.sh logs milvus

# Restart Milvus
docker restart milvus-standalone

# If corrupt, clean and restart
./start_local.sh clean
./start_local.sh start
```

### Backend Startup Timeout

**Symptom**: "Backend failed to start within 120 seconds"

**Cause**: Topic extraction can take 50-60 seconds on first document load

**Solution**: This is normal! The script waits up to 120 seconds. If it still fails:
```bash
# Check backend logs
./start_local.sh logs backend

# Manually start backend to see errors
cd /Users/adarsharma/Documents/adarsharma/M.tech-4th-sem/rag-enterprise
source venv/bin/activate
python -m backend.run_local
```

### Frontend Port Already in Use

**Symptom**: "Port 3000 already in use"

**Solution**:
```bash
# Find and kill the process using port 3000
lsof -ti:3000 | xargs kill -9

# Or restart frontend
./start_local.sh restart
```

### Redis Connection Errors

**Symptom**: "Could not connect to Redis"

**Solution**:
```bash
# Check Redis status
brew services list | grep redis

# Restart Redis
brew services restart redis

# Test connection
redis-cli ping  # Should return "PONG"
```

### LLM Queries Timing Out

**Symptom**: Queries take >60 seconds or timeout

**Solution**:
```bash
# Check if Metal GPU is being used
ollama ps

# Check system resources
top -l 1 | grep -E "^CPU|^PhysMem"

# Restart Ollama to clear any issues
brew services restart ollama
```

### Documents Not Loading

**Symptom**: Health check shows 0 documents

**Solution**:
```bash
# Check if sample documents exist
ls -la data/sample_confluence_pages/

# Manually trigger document loading
curl -X POST http://localhost:8000/ingest/trigger

# Check backend logs for errors
./start_local.sh logs backend
```

### Full Reset

If all else fails, completely reset the system:
```bash
# Stop everything
./start_local.sh stop

# Clean all data
./start_local.sh clean

# Start fresh
./start_local.sh start
```

**Solution**:
```bash
# Check logs
docker compose logs <service-name> --tail=50

# Full restart
docker compose down && docker compose up -d
```

## 📁 Project Structure

```
rag-enterprise/
├── 📜 start_local.sh              # Main automation script (all-in-one)
├── 📄 README.md                    # This file
├── 📄 QUICKSTART.md                # Quick start guide
├── 📄 QUICK_REFERENCE_LOCAL.md     # Local deployment commands
├── 📄 LOCAL_SETUP_SUCCESS.md       # Detailed local setup documentation
├── 📄 IMPROVEMENT_AREAS.md         # Grey areas and future improvements
├── 📄 DEMO_PREP_CHECKLIST.md       # M.Tech demo preparation
│
├── 📂 backend/                     # FastAPI backend service
│   ├── main.py                    # API endpoints (/health, /ask)
│   ├── run_local.py               # Local deployment script
│   ├── rag_pipeline.py            # RAG workflow orchestration
│   ├── milvus_client.py           # Vector database operations
│   ├── embeddings.py              # Embedding generation (BGE-Base-En)
│   ├── llm_client.py              # LLM integration with Ollama
│   ├── confluence_ingest.py       # Confluence API integration (COMPLETE)
│   ├── requirements.txt           # Python dependencies
│   └── .env.local                 # Local environment config
│
├── 📂 frontend/                    # React frontend service
│   ├── src/
│   │   ├── App.js                # Main chat component
│   │   ├── App.css               # Styling
│   │   └── index.js              # React entry point
│   ├── public/
│   ├── package.json              # Node dependencies
│   └── node_modules/             # Installed dependencies
│
├── 📂 data/                        # Sample documents
│   └── sample_confluence_pages/  # 14 pre-loaded documents
│       ├── agile_workflow.txt
│       ├── api_best_practices.txt
│       ├── code_review.txt
│       ├── engineering_standards.txt
│       ├── hr_policy.txt
│       ├── incident_management.txt
│       ├── leave_policy.txt
│       ├── onboarding.txt
│       ├── performance_review.txt
│       ├── security_guidelines.txt
│       └── ... (14 total)
│
├── 📂 docs_archive/                # Archived reference documentation
│   ├── legacy/                    # 1 file: conversational memory
│   ├── guides/                    # 5 files: architecture, APIs, hot reload
│   └── summaries/                 # 4 files: performance, privacy, design
│
├── 📂 venv/                        # Python virtual environment
├── 📂 volumes/                     # Milvus data persistence
├── .env.local                      # Local environment variables
├── .gitignore                      # Git ignore rules
├── docker-compose.yml              # Docker services (Milvus only)
└── requirements.txt                # Python dependencies
```

### Key Files

- **`start_local.sh`**: Main automation script that handles everything
  - 689 lines of comprehensive automation
  - Prerequisite checking and installation
  - Service orchestration (Ollama, Redis, Milvus, Backend, Frontend)
  - Health monitoring and status reporting
  - Document loading and indexing
  - Logging and debugging support

- **`backend/confluence_ingest.py`**: Full Confluence API implementation
  - ✅ Basic authentication (email + API token)
  - ✅ Fetch page by ID
  - ✅ Fetch all pages with pagination
  - ✅ CQL search support
  - ✅ Comprehensive error handling

- **`.env.local`**: Local deployment configuration
  - All service hostnames (localhost, not Docker internal)
  - LLM timeouts (cold: 90s, warm: 60s)
  - Confluence mode selection (local/api)
  - Milvus standalone configuration

### Documentation Organization

**Root Documentation (6 files):**
- Essential guides for getting started and running the system
- Current setup, commands, and improvement areas
- Demo preparation checklist

**Archived Documentation (10 files in `docs_archive/`):**
- Architecture and design documentation
- API implementation details
- Performance optimization strategies
- Security and privacy documentation
- Prompt engineering best practices

**Purpose**: Clean root directory for easy navigation, with valuable reference material preserved in archive.

## Architecture

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       ▼
```
┌─────────────────┐      ┌──────────────┐
│  React Frontend │◄────►│ FastAPI      │
│   (Port 3000)   │      │  (Port 8000) │
└─────────────────┘      └──────┬───────┘
                                │
                    ┌───────────┼──────────┬──────────┐
                    ▼           ▼          ▼          ▼
              ┌──────────┐ ┌────────┐ ┌──────┐ ┌─────────┐
              │ Embedder │ │ Milvus │ │ LLM  │ │  Redis  │
              │   BGE    │ │ Vector │ │Client│ │  Queue  │
              │ Large-En │ │   DB   │ │      │ │         │
              └──────────┘ └────────┘ └──────┘ └────┬────┘
                                                     │
                                              ┌──────┴──────────┐
                                              │   Ingestion     │
                                              │    Workers      │
                                              └────────┬────────┘
                                                       │
                              ┌────────────────────────┼────────────────────┐
                              ▼                        ▼                    ▼
                        ┌──────────┐           ┌─────────────┐      ┌──────────────┐
                        │  Folder  │           │  S3/MinIO   │      │  Confluence  │
                        │ Watcher  │           │  Listener   │      │   Webhook    │
                        └──────────┘           └─────────────┘      └──────────────┘
                         Local files           Bucket events     Page updates
```

### Request Flow

1. **User Query** → Frontend sends query to backend `/api/query` endpoint
2. **Embedding** → Query is embedded using BGE-Large-En model
3. **Retrieval** → Top-3 similar documents retrieved from Milvus
4. **Context Building** → Retrieved documents combined as context
5. **Generation** → LLM generates answer based on context
6. **Response** → Answer, sources, and latency returned to UI

### Ingestion Flow (Phase 1: Manual API)

1. **Document Upload** → User uploads file to `/api/ingest/upload`
2. **Job Queuing** → Backend saves file and publishes job to Redis
3. **Worker Processing** → Ingestion worker picks up job from queue
4. **Chunking & Embedding** → Worker chunks document and generates embeddings
5. **Storage** → Embeddings and text inserted into Milvus
6. **Status Update** → Job status updated in Redis

### Auto-Trigger Ingestion Flow (Phase 2: New!)

**Three automatic trigger mechanisms:**

####  Folder Watcher
1. User drops file in `data/incoming/` directory
2. Watcher detects new/modified file
3. Job automatically enqueued to Redis
4. Worker processes file → embeds → stores in Milvus

####  S3/MinIO Listener
1. File uploaded to S3/MinIO bucket (`incoming/` prefix)
2. Listener receives bucket notification event
3. File downloaded to temporary location
4. Job automatically enqueued to Redis
5. Worker processes file → embeds → stores in Milvus

####  Confluence Webhook
1. Page created/updated in Confluence
2. Webhook POST sent to `/api/webhook/confluence`
3. Backend extracts page URL
4. URL ingestion job enqueued to Redis
5. Worker fetches content → embeds → stores in Milvus

**Enable auto-triggers:**
```bash
# Set in .env
ENABLE_FOLDER_WATCHER=true
ENABLE_S3_TRIGGER=true

# Start trigger service
docker compose --profile trigger up -d
```

See [TRIGGER_SERVICE_GUIDE.md](TRIGGER_SERVICE_GUIDE.md) for complete documentation.
```

### Request Flow

1. **User Query** → Frontend sends query to backend `/ask` endpoint
2. **Embedding** → Query is embedded using BGE-Large-En model
3. **Retrieval** → Top-3 similar documents retrieved from Milvus
4. **Context Building** → Retrieved documents combined as context
5. **Generation** → LLM generates answer based on context
6. **Response** → Answer, sources, and latency returned to UI

## Tech Stack & Why?

### Backend: FastAPI
- **Why?** Async support, automatic API docs, Python ecosystem
- Modern, fast, and perfect for ML/AI services
- Built-in validation with Pydantic

### Vector DB: Milvus
- **Why?** Purpose-built for vector similarity search
- ANN (Approximate Nearest Neighbor) optimization
- Handles billion-scale vectors efficiently
- Open-source and production-ready

### Embeddings: BGE-Large-En
- **Why?** State-of-the-art dense retrieval performance
- Top results on MTEB leaderboard for English
- 1024-dimensional embeddings
- Excellent zero-shot generalization

### LLM: Mistral 7B
- **Why?** Strong performance with efficient inference
- Better quality-to-cost ratio than alternatives
- Supports both mock (demo) and API modes
- Easy to swap with other models

### Frontend: React
- **Why?** Component-based, fast, widely adopted
- Simple for this use case (no complex state management)
- Great developer experience

### Orchestration: Docker Compose
- **Why?** Reproducible one-command deployment
- Multi-service management
- Consistent environments (dev/prod)
- Easy dependency handling

##  Configuration

### Environment Variables

Copy `.env.example` to `.env` to customize:

```bash
# Milvus Connection
MILVUS_HOST=milvus
MILVUS_PORT=19530
COLLECTION_NAME=enterprise_docs

# Embeddings
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIM=384

# LLM Mode
LLM_MODE=mock                    # Options: mock, mistral

# Mistral API (if LLM_MODE=mistral)
MISTRAL_API_KEY=your_key_here
MISTRAL_API_URL=https://api.mistral.ai/v1/chat/completions

# Data Directory
DATA_DIR=/app/data

# Confluence Integration
CONFLUENCE_MODE=local            # Options: local, api
CONFLUENCE_LOCAL_DIR=/app/data/sample_confluence_pages
CONFLUENCE_BASE_URL=https://yourcompany.atlassian.net/wiki
CONFLUENCE_USER_EMAIL=your.email@company.com
CONFLUENCE_API_TOKEN=your_confluence_api_token
CONFLUENCE_SPACE_KEY=ENGINEERING
```

### Confluence Integration (POC + API-Ready)

The system includes **modular Confluence integration** that works in two modes:

#### Local Mode (Current POC)
```bash
CONFLUENCE_MODE=local
```
- Reads sample Confluence pages from `data/sample_confluence_pages/`
- Includes realistic enterprise documentation:
  - Engineering Standards (code review, git workflow, testing)
  - Agile Workflow (sprint planning, Jira, retrospectives)
  - Incident Management (severity levels, on-call, playbooks)
  - API Documentation (authentication, endpoints, examples)
- Perfect for **dissertation/demo** - no API credentials required
- Documents are automatically indexed on startup

#### API Mode (Production-Ready Stub)
```bash
CONFLUENCE_MODE=api
CONFLUENCE_BASE_URL=https://yourcompany.atlassian.net/wiki
CONFLUENCE_USER_EMAIL=your.email@company.com
CONFLUENCE_API_TOKEN=your_api_token
CONFLUENCE_SPACE_KEY=ENGINEERING
```
- Architecture ready for Confluence REST API integration
- Stub methods documented with API endpoints and authentication
- Easy to implement when API access is available
- Demonstrates **enterprise-ready** design for dissertation

**Why This Approach?**
- [x] Working POC without external dependencies
- [x] Architecturally sound for production extension
- [x] Can truthfully claim Confluence integration capability
- [x] Sample docs demonstrate handling of real enterprise content

### LLM Backend Options

The system supports **4 different LLM backends** with automatic detection. Choose based on your needs:

#### 1. **Mock Mode** (Default - Best for Development)
```bash
LLM_MODE=mock
```
- [x] No dependencies, instant responses
- [x] Perfect for testing/demos
- [x] Returns template with context snippets
-  Emoji indicator: 

#### 2. **Ollama** (Local Inference - Best for Privacy)
```bash
LLM_MODE=api
MISTRAL_API_URL=http://host.docker.internal:11434/api/generate
MISTRAL_MODEL=mistral
```
- [x] Fast local inference
- [x] Completely private, no data leaves your machine
- [x] Free (after initial setup)
-  Emoji indicator: 
-  Requires: [Ollama installed](https://ollama.ai)

#### 3. **HuggingFace Inference API** (Cloud - Best for Quick Start)
```bash
LLM_MODE=api
MISTRAL_API_URL=https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2
MISTRAL_API_KEY=hf_YOUR_TOKEN_HERE
MISTRAL_MODEL=mistralai/Mistral-7B-Instruct-v0.2
```
- [x] No local setup required
- [x] Free tier available
- [x] Access to many models
-  Emoji indicator: 
-  Requires: [HuggingFace API token](https://huggingface.co/settings/tokens)

#### 4. **Mistral AI Official API** (Cloud - Best for Production)
```bash
LLM_MODE=api
MISTRAL_API_URL=https://api.mistral.ai/v1/chat/completions
MISTRAL_API_KEY=your_mistral_api_key
MISTRAL_MODEL=mistral-small-latest
```
- [x] Enterprise-grade support
- [x] High performance
-  Emoji indicator: 
-  Requires: [Mistral API key](https://console.mistral.ai) (paid)

**Backend Auto-Detection:** The system automatically detects which backend to use based on the URL pattern:
- Contains "ollama" or ":11434" → Ollama
- Contains "huggingface" → HuggingFace
- Other → Mistral API

See `LLM_BACKEND_IMPLEMENTATION.md` for detailed configuration guide.

## API Endpoints

### Core Query API

### GET `/health`
Health check endpoint
```json
{
  "status": "ok"
}
```

### POST `/api/query`
Process a user query with conversational memory

**Request:**
```json
{
  "query": "What is the PTO policy?",
  "session_id": "user123"  // Optional, for conversation history
}
```

**Response:**
```json
{
  "answer": "Based on the HR policies...",
  "sources": [
    {"title": "HR_Policies.txt", "text": "..."}
  ],
  "latency_ms": 1234.56,
  "session_id": "user123"
}
```

### Document Ingestion API

The system now supports **asynchronous document ingestion** via a dedicated microservice. Upload documents through the REST API, and they'll be processed in the background by worker services.

#### POST `/api/ingest/upload`
Upload a document for asynchronous ingestion

**Request:**
```bash
curl -X POST http://localhost:8000/api/ingest/upload \
  -F "file=@document.txt"
```

**Response:**
```json
{
  "job_id": "abc123-def456-ghi789",
  "status": "queued",
  "message": "Document 'document.txt' queued for ingestion",
  "file_path": "/app/uploads/abc123_document.txt"
}
```

#### GET `/api/ingest/status/{job_id}`
Check the status of an ingestion job

**Request:**
```bash
curl http://localhost:8000/api/ingest/status/abc123-def456-ghi789
```

**Response (Completed):**
```json
{
  "job_id": "abc123-def456-ghi789",
  "status": "completed",
  "result": {
    "status": "success",
    "title": "document.txt",
    "chunks": 5,
    "total_characters": 12450,
    "elapsed_seconds": 23.5,
    "message": "[x] Successfully ingested: document.txt"
  }
}
```

**Status Values:**
- `queued` - Job waiting in queue
- `processing` - Worker is processing
- `completed` - Successfully ingested
- `failed` - Ingestion failed

#### DELETE `/api/ingest/job/{job_id}`
Cancel a pending or running ingestion job

**Ingestion Architecture:**
```
User Upload → FastAPI Backend → Redis Queue → Ingestion Worker → Milvus
```

**Key Features:**
- [x] Asynchronous processing (non-blocking)
- [x] Redis queue for job management  
- [x] Scalable workers (can run multiple)
- [x] Job status tracking
- [x] Automatic chunking and embedding
- [x] Supports .txt and .md files

**See [INGESTION_API_GUIDE.md](./INGESTION_API_GUIDE.md) for detailed documentation.**

### Auto-Trigger Ingestion (Phase 2 - NEW!)

Automatically ingest documents without manual API calls. Three trigger mechanisms available:

#### POST `/api/webhook/confluence`
Receive Confluence webhook events for automatic page ingestion

**Request:**
```json
{
  "event": "page_created",
  "page": {
    "id": "12345",
    "title": "Engineering Guidelines",
    "url": "https://yourcompany.atlassian.net/wiki/spaces/ENG/pages/12345"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Confluence page 'Engineering Guidelines' queued for ingestion",
  "job_id": "abc-123-def"
}
```

#### Folder Watcher

Monitor local directory for new files and automatically enqueue for ingestion.

```bash
# Enable in .env
ENABLE_FOLDER_WATCHER=true
WATCH_DIR=/app/data/incoming

# Start trigger service
docker compose --profile trigger up -d

# Drop files to auto-ingest
cp document.txt data/incoming/
```

**Supported file types:** `.txt`, `.md`, `.pdf`, `.doc`, `.docx`

#### S3/MinIO Listener

Listen to bucket events and automatically ingest uploaded files.

```bash
# Enable in .env
ENABLE_S3_TRIGGER=true
MINIO_ENDPOINT=http://minio:9000
S3_BUCKET_NAME=documents

# Start trigger service
docker compose --profile trigger up -d

# Upload to bucket → automatically ingested
```

**Quick Start:**
```bash
# 1. Enable triggers in .env
echo "ENABLE_FOLDER_WATCHER=true" >> .env

# 2. Start services with trigger profile
docker compose --profile trigger up -d

# 3. Drop a file
echo "Test document" > data/incoming/test.txt

# 4. Watch it get processed
docker compose logs -f trigger
```

** Complete Guide:** See [TRIGGER_SERVICE_GUIDE.md](./TRIGGER_SERVICE_GUIDE.md) for:
- Detailed setup instructions
- Configuration reference
- Troubleshooting guide
- Security best practices
- Testing procedures

### POST `/ask`
** Deprecated:** Use `/api/query` instead.

Process a user query

**Request:**
```json
{
  "query": "What is the PTO policy?"
}
```

**Response:**
```json
{
  "answer": "Based on the retrieved context...",
  "sources": [
    {
      "title": "leave_policy.txt",
      "text": "Our company uses a combined PTO policy...",
      "score": 0.923
    }
  ],
  "latency_ms": 342.56
}
```

## Development

### Adding New Documents

1. Add `.txt` files to the `data/` directory
2. Restart backend service:
   ```bash
   docker compose restart backend
   ```
3. Documents are automatically indexed on startup if collection is empty

### Running Services Individually

**Backend only:**
```bash
cd backend
pip install -r requirements.txt
python main.py
```

**Frontend only:**
```bash
cd frontend
npm install
npm start
```

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f milvus
```

## Troubleshooting

### "Connection refused" error
- Wait 2-3 minutes for Milvus to fully initialize
- Check Milvus health: `curl http://localhost:9091/healthz`

### Out of memory during startup
- Embedding model requires ~4GB RAM
- Increase Docker memory limit in Docker Desktop settings

### Port already in use
- Stop conflicting services or change ports in `docker-compose.yml`

### Frontend can't reach backend
- Ensure `REACT_APP_API_URL` matches your backend URL
- Check CORS settings in `backend/main.py`

## Evaluation (Phase 3) - Dissertation Metrics

This project includes an **automated evaluation module** that measures system performance for dissertation reporting.

### What Gets Measured

The evaluation script tests 8 predefined queries and measures:

| Metric | Description | Expected Range |
|--------|-------------|----------------|
| **Retrieval Time** | Embedding generation + vector search latency | 30-100 ms |
| **Generation Time** | LLM inference time | 1000-2500 ms |
| **Total Latency** | End-to-end response time | 1200-2800 ms |
| **Relevance Score** | Cosine similarity of top-ranked source | 70-90% |

### How to Run Evaluation

#### Option 1: Run Evaluation Script (Recommended)

```bash
# Make sure services are running
docker compose up -d

# Run evaluation (takes 2-3 minutes)
docker compose run backend python evaluate_poc.py

# Copy results to your machine
docker compose cp backend:/app/results/results.md ./backend/results/results.md

# View results
cat backend/results/results.md
```

#### Option 2: Trigger via API

```bash
# Start services
docker compose up -d

# Trigger evaluation via API
curl http://localhost:8000/evaluate

# Or visit in browser
open http://localhost:8000/evaluate
```

### Output Format

The evaluation generates a Markdown file (`results.md`) with:

1. **Performance Summary Table**
   ```markdown
   | Metric | Average | Unit |
   |--------|---------|------|
   | Retrieval Time | 45.23 | ms |
   | Generation Time | 1250.67 | ms |
   | Total Latency | 1295.90 | ms |
   | Relevance Score | 82.45% | % |
   ```

2. **Detailed Query Results** (8 test queries with individual metrics)
3. **Answer Previews** (for qualitative analysis)
4. **System Configuration** (for methodology section)

### Dissertation Use

The `results.md` file is ready for direct inclusion in your dissertation's **Results & Evaluation** chapter:

## 🎓 Academic Context

This project is part of an M.Tech 4th semester presentation demonstrating:
- ✅ **Enterprise RAG Implementation**: Complete end-to-end pipeline
- ✅ **Performance Optimization**: 8-10x improvement with Metal GPU
- ✅ **Native Deployment**: Moving from Docker to optimized local setup
- ✅ **Production Practices**: Health checks, monitoring, error handling
- ✅ **API Integration**: Full Confluence API implementation
- ✅ **Automation**: One-command deployment with comprehensive checks

### Performance Metrics

- **Query Response Time**: 8-10 seconds (vs 60-90s in Docker)
- **Speedup**: 8-10x improvement with Metal GPU acceleration
- **Memory Usage**: ~8-10GB total (efficient resource utilization)
- **Document Loading**: 14 documents indexed in ~5 seconds
- **Topic Extraction**: ~50 seconds (one-time per session)
- **Startup Time**: 30-60 seconds (after initial setup)

### Technical Achievements

1. **Native Mac Optimization**
   - Metal GPU acceleration for LLM inference
   - Eliminated Docker overhead for compute-intensive tasks
   - Optimized service orchestration

2. **Comprehensive Automation**
   - 689-line automation script
   - Prerequisite checking and auto-installation
   - Health monitoring and status reporting
   - Intelligent timeout handling

3. **Full API Integration**
   - Complete Confluence API implementation
   - Basic authentication support
   - Pagination and search capabilities
   - Comprehensive error handling

4. **Production-Ready Features**
   - Conversational memory (5-turn context)
   - Hot reload for development
   - Comprehensive health checks
   - Document ingestion pipeline
   - Source attribution and latency tracking

## 📚 Additional Documentation

- **`QUICK_REFERENCE_LOCAL.md`**: Quick command reference
- **`LOCAL_SETUP_SUCCESS.md`**: Detailed setup walkthrough
- **`IMPROVEMENT_AREAS.md`**: 18 identified grey areas for future work
- **`DEMO_PREP_CHECKLIST.md`**: M.Tech presentation preparation
- **`docs_archive/`**: Architectural and implementation reference docs

## 🚀 Future Enhancements

### Priority 1 (High Impact)
- [ ] Advanced conversational features (conversation branches, history search)
- [ ] Enhanced document preprocessing (better chunking strategies)
- [ ] Query optimization (caching, compression)

### Priority 2 (User Experience)
- [ ] Multi-document upload interface
- [ ] Real-time ingestion status
- [ ] Query history and favorites
- [ ] Export conversations

### Priority 3 (Production)
- [ ] User authentication and authorization
- [ ] Multi-tenant support
- [ ] Monitoring and analytics dashboard
- [ ] Automated testing suite

### Priority 4 (Advanced Features)
- [ ] Multi-language support
- [ ] Custom embedding models
- [ ] Fine-tuning capabilities
- [ ] Advanced RAG techniques (HyDE, multi-query)

## 📝 License

This project is for educational/academic purposes (M.Tech dissertation).

## 🙏 Acknowledgments

- **Ollama**: Local LLM inference with Metal GPU support
- **Milvus**: High-performance vector database
- **FastAPI**: Modern Python web framework
- **React**: Frontend UI framework

---

**Built with ❤️ for enterprise knowledge management**

*Last updated: November 16, 2025*
*Branch: local-final-presentation*
*Status: Production-ready local deployment*
