# 🤖 RAG Enterprise Chatbot

A production-ready Retrieval-Augmented Generation (RAG) chatbot system for enterprise knowledge management with on-premise LLM support, automatic document ingestion, and resilient service architecture.

## Overview

This project implements a complete RAG pipeline that allows users to ask questions about enterprise documents (HR policies, onboarding guides, engineering standards) and receive contextual answers backed by retrieved sources using local LLM inference.

**Key Features:**
- ✅ End-to-end RAG pipeline with resilient LLM integration
- ✅ Vector similarity search with Milvus
- ✅ Local LLM inference via Ollama (Mistral 7B)
- ✅ State-of-the-art embeddings (BGE-Base-En)
- ✅ Automatic document ingestion via folder watcher
- ✅ Confluence integration (POC mode with API-ready architecture)
- ✅ **Conversational memory** — remembers last 5 turns per chat session
- ✅ Health checks and service monitoring
- ✅ Reboot-stable architecture with automatic model loading
- ✅ Clean, minimal React UI
- ✅ One-command deployment with Docker Compose
- ✅ Source attribution and latency tracking

## Quick Start

### Prerequisites
- Docker Desktop (with Docker Compose)
- 12GB RAM minimum (for LLM model + embeddings)
- Ports 3000, 8000, 11434, 19530 available

### 🚀 Stable Startup (Recommended)

Use the development startup script for reliable initialization:

```bash
# Clone or navigate to the project directory
cd rag-enterprise

# Run the dev startup script (handles model download, health checks)
./scripts/dev-up.sh
```

**What it does:**
1. Starts all Docker services
2. Waits for Ollama container to be ready
3. Downloads Mistral model if not present (~4.4GB, one-time)
4. Waits for all services to be healthy
5. Displays access URLs and quick test commands

**Expected startup time:**
- First run: 5-10 minutes (model download + service initialization)
- Subsequent runs: 1-2 minutes (services already configured)

### Alternative: Manual Startup

```bash
# Start all services
docker compose up -d

# Manually pull Mistral model (if needed)
docker exec rag-ollama ollama pull mistral

# Check health status
curl http://localhost:8000/health/deps
```

### Access URLs

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health/deps
- **LLM Health**: http://localhost:8000/llm/health
- **Ollama API**: http://localhost:11434

### Using Host Ollama (Optional)

By default, the system uses the dockerized Ollama service. To use a host-installed Ollama:

1. Edit `.env`:
   ```bash
   LLM_HOST=host.docker.internal
   ```

2. Ensure Ollama is running on your host:
   ```bash
   ollama serve
   ```

3. Restart backend:
   ```bash
   docker compose restart backend
   ```

## Reboot-Stable Architecture

This system is designed to work reliably after machine reboots:

- **Dockerized Ollama**: No dependency on host services
- **Automatic model loading**: Models persist in Docker volumes
- **Health checks**: Services wait for dependencies before starting
- **Fallback endpoints**: Multiple connection attempts with graceful degradation
- **Environment-based config**: Single source of truth in `.env`

### After Reboot

Simply run:
```bash
./scripts/dev-up.sh
```

Or manually:
```bash
docker compose up -d
```

Services will automatically restore from persistent volumes.

### First Query Example

Try asking:
- "What is the PTO policy?"
- "How many holidays do we get?"
- "What happens during onboarding week 1?"
- "Can I rollover unused PTO?"
- "What are the incident severity levels?"
- "How do I create a pull request?"
- "What is our code review process?"

## Testing & Validation

### Health Checks

Check all service dependencies:
```bash
curl http://localhost:8000/health/deps
```

Expected response:
```json
{
  "milvus": "ok",
  "ollama": "ok",
  "redis": "ok"
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
  -d '{"query":"What is the sprint duration?"}'
```

## Troubleshooting

### LLM 404 Error

**Symptom**: `/ask` endpoint returns 404 error or "LLM generation service appears unreachable"

## Troubleshooting

### rag-ollama Container Unhealthy

**Symptom**: `docker compose ps` shows rag-ollama as "unhealthy"

**Solution**:
- Confirm the healthcheck uses `ollama list` (not curl) in docker-compose.yml
- Ensure `LLM_HOST=rag-ollama` in .env matches the service name
- Check logs: `docker compose logs rag-ollama --tail=50`
- Restart if needed: `docker compose restart rag-ollama`

### LLM 404 Error

**Symptom**: `/ask` endpoint returns 404 error or "LLM generation service appears unreachable"

**Solution**:
```bash
# 1. Check if Ollama container is running
docker ps | grep rag-ollama

# 2. Check if model is downloaded
docker exec rag-ollama ollama list

# 3. If model missing, download it
docker exec rag-ollama ollama pull mistral

# 4. Restart backend
```

### Service Dependencies Not Healthy

**Solution**:
```bash
# Check logs
docker compose logs <service-name> --tail=50

# Full restart
docker compose down && docker compose up -d
```

## Project Structure

```
rag-enterprise/
├── backend/                 # FastAPI backend service
│   ├── main.py             # API endpoints (/health, /ask)
│   ├── rag_pipeline.py     # Orchestrates RAG workflow
│   ├── milvus_client.py    # Vector database operations
│   ├── embeddings.py       # Hash-based embedding model
│   ├── llm_client.py       # LLM integration (mock/API)
│   ├── confluence_ingest.py # Confluence document ingestion
│   ├── requirements.txt    # Python dependencies
│   ├── Dockerfile          # Backend container config
│   └── .env.example        # Configuration template
├── frontend/               # React frontend service
│   ├── src/
│   │   ├── App.js         # Main chat component
│   │   ├── App.css        # Styling
│   │   └── index.js       # React entry point
│   ├── public/
│   ├── Dockerfile         # Frontend container config
│   ├── nginx.conf         # Nginx configuration
│   └── package.json       # Node dependencies
├── data/                  # Sample enterprise documents
│   ├── hr_policy.txt     # HR policies and benefits
│   ├── onboarding.txt    # Onboarding guide
│   ├── leave_policy.txt  # Leave and PTO policies
│   └── sample_confluence_pages/  # Confluence POC documents
│       ├── engineering_standards.txt
│       ├── agile_workflow.txt
│       ├── incident_management.txt
│       └── api_documentation.txt
├── docker-compose.yml    # Multi-service orchestration
├── .env.example          # Environment configuration template
└── README.md            # This file
```

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
                        📂 Local files         ☁️  Bucket events    🔔 Page updates
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

#### 📂 Folder Watcher
1. User drops file in `data/incoming/` directory
2. Watcher detects new/modified file
3. Job automatically enqueued to Redis
4. Worker processes file → embeds → stores in Milvus

#### ☁️ S3/MinIO Listener
1. File uploaded to S3/MinIO bucket (`incoming/` prefix)
2. Listener receives bucket notification event
3. File downloaded to temporary location
4. Job automatically enqueued to Redis
5. Worker processes file → embeds → stores in Milvus

#### 🔔 Confluence Webhook
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

## 🔧 Configuration

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
- ✅ Working POC without external dependencies
- ✅ Architecturally sound for production extension
- ✅ Can truthfully claim Confluence integration capability
- ✅ Sample docs demonstrate handling of real enterprise content

### LLM Backend Options

The system supports **4 different LLM backends** with automatic detection. Choose based on your needs:

#### 1. **Mock Mode** (Default - Best for Development)
```bash
LLM_MODE=mock
```
- ✅ No dependencies, instant responses
- ✅ Perfect for testing/demos
- ✅ Returns template with context snippets
- 📝 Emoji indicator: 📝

#### 2. **Ollama** (Local Inference - Best for Privacy)
```bash
LLM_MODE=api
MISTRAL_API_URL=http://host.docker.internal:11434/api/generate
MISTRAL_MODEL=mistral
```
- ✅ Fast local inference
- ✅ Completely private, no data leaves your machine
- ✅ Free (after initial setup)
- 🦙 Emoji indicator: 🦙
- 📦 Requires: [Ollama installed](https://ollama.ai)

#### 3. **HuggingFace Inference API** (Cloud - Best for Quick Start)
```bash
LLM_MODE=api
MISTRAL_API_URL=https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2
MISTRAL_API_KEY=hf_YOUR_TOKEN_HERE
MISTRAL_MODEL=mistralai/Mistral-7B-Instruct-v0.2
```
- ✅ No local setup required
- ✅ Free tier available
- ✅ Access to many models
- 🤗 Emoji indicator: 🤗
- 🔑 Requires: [HuggingFace API token](https://huggingface.co/settings/tokens)

#### 4. **Mistral AI Official API** (Cloud - Best for Production)
```bash
LLM_MODE=api
MISTRAL_API_URL=https://api.mistral.ai/v1/chat/completions
MISTRAL_API_KEY=your_mistral_api_key
MISTRAL_MODEL=mistral-small-latest
```
- ✅ Enterprise-grade support
- ✅ High performance
- 🌟 Emoji indicator: 🌟
- 💳 Requires: [Mistral API key](https://console.mistral.ai) (paid)

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
    "message": "✅ Successfully ingested: document.txt"
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
- ✅ Asynchronous processing (non-blocking)
- ✅ Redis queue for job management  
- ✅ Scalable workers (can run multiple)
- ✅ Job status tracking
- ✅ Automatic chunking and embedding
- ✅ Supports .txt and .md files

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

**📖 Complete Guide:** See [TRIGGER_SERVICE_GUIDE.md](./TRIGGER_SERVICE_GUIDE.md) for:
- Detailed setup instructions
- Configuration reference
- Troubleshooting guide
- Security best practices
- Testing procedures

### POST `/ask`
**⚠️ Deprecated:** Use `/api/query` instead.

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

- ✅ Quantitative performance metrics
- ✅ System configuration details
- ✅ Comparison baseline data
- ✅ Markdown format (easy to convert to LaTeX/Word)

## Performance Notes

- **Cold start**: ~2-3 minutes (model loading)
- **Query latency**: 200-500ms (mock mode)
- **Embedding time**: ~50-100ms per query
- **Vector search**: <10ms (3 documents)

## Limitations (PoC)

This is a minimal proof-of-concept. For production:
- ❌ No authentication/authorization
- ❌ No query history or conversation memory
- ❌ No document versioning
- ❌ No monitoring/alerting
- ❌ Single-node Milvus (use cluster for scale)
- ❌ No caching layer
- ❌ Basic error handling

## Future Enhancements

- [ ] Add conversation history and memory
- [ ] Implement user authentication
- [ ] Support PDF, Word, and other document formats
- [ ] Add query refinement and follow-up questions
- [ ] Implement feedback mechanism for answers
- [ ] Add monitoring with Prometheus/Grafana
- [ ] Scale Milvus to cluster mode
- [ ] Implement semantic caching
- [ ] Add multi-language support

## License

This project is for educational/dissertation purposes.

## Contributing

This is a proof-of-concept project. Feel free to fork and adapt for your needs.

## Contact

For questions about this implementation, please refer to the code comments and documentation.

---

**Built with ❤️ for enterprise knowledge management**

*Last updated: October 2025*
