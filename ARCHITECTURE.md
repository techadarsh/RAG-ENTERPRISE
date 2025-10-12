# System Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              React Frontend (Port 3000)                  │  │
│  │  • Chat Input Component                                  │  │
│  │  • Response Display                                      │  │
│  │  • Source Attribution                                    │  │
│  │  • Latency Metrics                                       │  │
│  └────────────────────────┬─────────────────────────────────┘  │
└───────────────────────────┼─────────────────────────────────────┘
                            │ HTTP/REST
                            │ POST /ask
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND SERVICE                            │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            FastAPI Application (Port 8000)               │  │
│  │                                                          │  │
│  │  Endpoints:                                              │  │
│  │  • GET  /health    → Health check                       │  │
│  │  • POST /ask       → Query processing                    │  │
│  │  • GET  /          → API info                           │  │
│  │  • GET  /docs      → Swagger UI                         │  │
│  └────────────────────────┬─────────────────────────────────┘  │
│                           │                                     │
│  ┌────────────────────────▼─────────────────────────────────┐  │
│  │                 RAG Pipeline Orchestrator                │  │
│  │                                                          │  │
│  │  1. Query Reception                                      │  │
│  │  2. Embedding Generation                                 │  │
│  │  3. Vector Search                                        │  │
│  │  4. Context Assembly                                     │  │
│  │  5. LLM Invocation                                       │  │
│  │  6. Response Formatting                                  │  │
│  └──────────┬─────────────┬─────────────┬──────────────────┘  │
└─────────────┼─────────────┼─────────────┼──────────────────────┘
              │             │             │
              ▼             ▼             ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │  Embeddings │ │   Milvus    │ │ LLM Client  │
    │   Module    │ │  Vector DB  │ │   Module    │
    └─────────────┘ └─────────────┘ └─────────────┘
```

## Component Details

### 1. Frontend Layer (React)

**Technology**: React 18 + Axios + CSS3

**Responsibilities**:
- User interface rendering
- Query input handling
- HTTP request management
- Response visualization
- Source citation display
- Performance metrics (latency)

**Files**:
- `frontend/src/App.js` - Main chat component
- `frontend/src/App.css` - Styling and animations
- `frontend/src/index.js` - React entry point

### 2. Backend Layer (FastAPI)

**Technology**: FastAPI + Uvicorn + Python 3.10

**Responsibilities**:
- REST API endpoints
- Request validation (Pydantic)
- CORS handling
- Error management
- Logging and monitoring
- Orchestration of RAG components

**Files**:
- `backend/main.py` - API server and endpoints
- `backend/rag_pipeline.py` - RAG workflow orchestration

### 3. Embedding Component

**Technology**: sentence-transformers + BGE-Large-En

**Specifications**:
- Model: BAAI/bge-large-en
- Dimension: 1024
- Normalization: L2 normalized vectors
- Performance: ~50-100ms per query

**Responsibilities**:
- Text → Vector transformation
- Query embedding
- Document embedding (startup)
- Batch processing support

**Files**:
- `backend/embeddings.py`

### 4. Vector Database (Milvus)

**Technology**: Milvus 2.3.3 Standalone

**Configuration**:
- Collection: `enterprise_docs`
- Index Type: IVF_FLAT
- Metric: Inner Product (IP)
- Storage: etcd + MinIO

**Responsibilities**:
- Vector storage and indexing
- Similarity search (ANN)
- Metadata storage (title, text)
- Scalable retrieval

**Files**:
- `backend/milvus_client.py`

**Supporting Services**:
- **etcd**: Metadata storage and coordination
- **MinIO**: Object storage for Milvus data

### 5. LLM Component

**Technology**: Mistral API / Mock Mode

**Modes**:

1. **Mock Mode** (Default - Demo)
   - Returns template responses
   - No API calls required
   - Instant responses
   - Perfect for testing

2. **API Mode** (Production)
   - Calls Mistral API
   - Real answer generation
   - Configurable model
   - Context-aware responses

**Responsibilities**:
- Answer generation
- Context interpretation
- Prompt engineering
- API communication (if enabled)

**Files**:
- `backend/llm_client.py`

## Data Flow

### Startup Sequence

```
1. Docker Compose starts all services
   ├─ etcd (metadata store)
   ├─ MinIO (object storage)
   └─ Milvus (vector DB)
        └─ Waits for etcd + MinIO

2. Backend starts
   ├─ Loads environment variables
   ├─ Initializes embedding model (BGE-Large-En)
   ├─ Connects to Milvus
   └─ Checks if collection is empty
        └─ If empty: Indexes documents from /data

3. Frontend starts
   └─ Serves React app via Nginx
```

### Query Processing Flow

```
User Query: "What is the PTO policy?"
    │
    ▼
[Frontend] Capture input
    │
    ▼
[Frontend] POST to /ask endpoint
    │
    ▼
[Backend] Receive request
    │
    ▼
[RAG Pipeline] Start timer
    │
    ▼
[Embeddings] Generate query vector
    │ Input: "What is the PTO policy?"
    │ Output: [0.23, -0.45, 0.67, ..., 0.12] (1024-dim)
    ▼
[Milvus] Search similar vectors
    │ Input: Query vector + top_k=3
    │ Search: Compute similarity scores
    │ Output: Top 3 documents with scores
    ▼
[RAG Pipeline] Build context
    │ Combine: Document 1 + Document 2 + Document 3
    │ Format: "[Document 1: title]\ntext\n\n[Document 2: title]\ntext..."
    ▼
[LLM Client] Generate answer
    │ Input: Context + Query
    │ Process: (Mock: template / API: Mistral)
    │ Output: Generated answer text
    ▼
[RAG Pipeline] Format response
    │ Package: {answer, sources[], latency_ms}
    ▼
[Backend] Return JSON response
    │
    ▼
[Frontend] Display results
    └─ Answer + Sources + Latency
```

## Scalability Considerations

### Current Setup (PoC)
- Single-node Milvus
- In-memory processing
- Local document storage
- Synchronous LLM calls

### Production Enhancements
- Milvus cluster mode
- Redis caching layer
- S3/Cloud document storage
- Async LLM processing
- Load balancing (multiple backends)
- Connection pooling
- Rate limiting

## Security Architecture

### Current Implementation
- CORS enabled (all origins)
- No authentication
- No input sanitization
- Public endpoints

### Production Requirements
- [ ] JWT-based authentication
- [ ] Role-based access control
- [ ] Input validation and sanitization
- [ ] Rate limiting per user
- [ ] API key management
- [ ] Audit logging
- [ ] HTTPS/TLS encryption

## Performance Metrics

### Target Latencies
- Embedding: 50-100ms
- Vector Search: <10ms
- LLM (Mock): <5ms
- LLM (API): 500-2000ms
- **Total (Mock)**: 200-500ms
- **Total (API)**: 800-2500ms

### Resource Requirements
- RAM: 8GB minimum (4GB for model)
- CPU: 4+ cores recommended
- Disk: 10GB for models + data
- Network: Required for Mistral API

## Technology Justification

### Why FastAPI?
✅ Native async support
✅ Automatic API documentation
✅ Fast development with Python
✅ Built-in validation (Pydantic)
✅ Great for ML/AI services

### Why Milvus?
✅ Purpose-built for vectors
✅ ANN algorithms (fast search)
✅ Handles billions of vectors
✅ Open-source and active
✅ Production-ready

### Why BGE-Large-En?
✅ SOTA performance (MTEB)
✅ 1024-dim embeddings
✅ Excellent for English
✅ Fast inference
✅ Good generalization

### Why Mistral?
✅ Strong performance
✅ Cost-effective
✅ Good API reliability
✅ Easy integration
✅ Comparable to GPT-3.5

### Why Docker Compose?
✅ One-command deployment
✅ Service orchestration
✅ Consistent environments
✅ Easy dependency management
✅ Portable and reproducible

## Deployment Architecture

```
Development:
  localhost:3000 (Frontend)
  localhost:8000 (Backend)
  localhost:19530 (Milvus)

Production (Example):
  https://chat.company.com → Frontend (Nginx/CloudFront)
  https://api.company.com → Backend (Load Balancer)
  internal:19530 → Milvus Cluster (Private Network)
```

## Monitoring Points

### Application Metrics
- Query latency (p50, p95, p99)
- Error rates
- API success/failure counts
- Active connections

### Infrastructure Metrics
- CPU/Memory usage
- Milvus index size
- Document count
- Vector search performance

### Business Metrics
- Queries per user
- Most asked questions
- Answer satisfaction
- Source relevance scores

---

**Version**: 1.0.0  
**Last Updated**: October 2025
