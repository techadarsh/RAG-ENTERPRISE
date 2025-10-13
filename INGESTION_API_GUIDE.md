# Document Ingestion API Guide

##  Overview

The RAG Enterprise System now supports **asynchronous document ingestion** through a dedicated microservice architecture. Documents are uploaded via REST API, queued in Redis, and processed by background workers.

---

##  Architecture

```
┌──────────────────────────────────────────────────────────┐
│               Client / Frontend                           │
│   Uploads documents via /api/ingest/upload                │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│             Backend (FastAPI)                             │
│  • Receives file uploads                                  │
│  • Validates and saves files                              │
│  • Publishes jobs to Redis queue                          │
│  • Provides job status tracking                           │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│            Redis Queue (Message Broker)                   │
│  • Queue: 'ingestion'                                     │
│  • Persistent job storage                                 │
│  • Job status tracking                                    │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│         Ingestion Worker (RQ Worker)                      │
│  • Consumes jobs from queue                               │
│  • Reads uploaded files                                   │
│  • Chunks documents (3000 chars, 500 overlap)             │
│  • Generates embeddings (BAAI/bge-base-en)                │
│  • Inserts into Milvus vector database                    │
│  • Updates job status                                     │
└──────────────────────────────────────────────────────────┘
```

---

##  Quick Start

### **1. Start All Services**

```bash
# From project root
docker compose up -d

# Check all services are running
docker compose ps
```

Expected services:
- [x] `rag-backend` - REST API (port 8000)
- [x] `rag-ingestion` - Worker service
- [x] `rag-redis` - Message queue (port 6379)
- [x] `milvus-standalone` - Vector database
- [x] `rag-frontend` - UI (port 3000)
- [x] `rag-ollama` - LLM service

### **2. Upload a Document**

```bash
# Upload a text file
curl -X POST http://localhost:8000/api/ingest/upload \
  -F "file=@/path/to/your/document.txt"
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

### **3. Check Job Status**

```bash
# Check processing status
curl http://localhost:8000/api/ingest/status/abc123-def456-ghi789
```

**Response (Processing):**
```json
{
  "job_id": "abc123-def456-ghi789",
  "status": "processing",
  "result": null,
  "error": null
}
```

**Response (Completed):**
```json
{
  "job_id": "abc123-def456-ghi789",
  "status": "completed",
  "result": {
    "status": "success",
    "file_path": "/app/uploads/abc123_document.txt",
    "title": "document.txt",
    "chunks": 5,
    "total_characters": 12450,
    "elapsed_seconds": 23.5,
    "message": "[x] Successfully ingested: document.txt"
  },
  "error": null
}
```

### **4. Query the Ingested Document**

```bash
# Ask questions about the ingested document
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the main topic of this document?",
    "session_id": "test-session"
  }'
```

---

##  API Endpoints

### **POST /api/ingest/upload**

Upload a document for asynchronous processing.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: Form field `file` with the document

**Supported File Types:**
- `.txt` - Plain text
- `.md` - Markdown
- `.text` - Text files

**Example (curl):**
```bash
curl -X POST http://localhost:8000/api/ingest/upload \
  -F "file=@document.txt"
```

**Example (Python):**
```python
import requests

with open('document.txt', 'rb') as f:
    files = {'file': f}
    response = requests.post(
        'http://localhost:8000/api/ingest/upload',
        files=files
    )
    print(response.json())
```

**Example (JavaScript):**
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('http://localhost:8000/api/ingest/upload', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```

**Response:**
```json
{
  "job_id": "string",
  "status": "queued",
  "message": "string",
  "file_path": "string"
}
```

---

### **GET /api/ingest/status/{job_id}**

Check the status of an ingestion job.

**Request:**
- Method: `GET`
- Path Parameter: `job_id`

**Example:**
```bash
curl http://localhost:8000/api/ingest/status/abc123-def456-ghi789
```

**Response (Queued):**
```json
{
  "job_id": "abc123-def456-ghi789",
  "status": "queued",
  "result": null,
  "error": null
}
```

**Response (Processing):**
```json
{
  "job_id": "abc123-def456-ghi789",
  "status": "processing",
  "result": null,
  "error": null
}
```

**Response (Completed):**
```json
{
  "job_id": "abc123-def456-ghi789",
  "status": "completed",
  "result": {
    "status": "success",
    "file_path": "/app/uploads/abc123_document.txt",
    "title": "document.txt",
    "chunks": 8,
    "total_characters": 24500,
    "elapsed_seconds": 45.2,
    "message": "[x] Successfully ingested: document.txt"
  },
  "error": null
}
```

**Response (Failed):**
```json
{
  "job_id": "abc123-def456-ghi789",
  "status": "failed",
  "result": null,
  "error": "File format not supported"
}
```

**Status Values:**
- `queued` - Job is waiting in queue
- `processing` - Worker is processing the document
- `completed` - Ingestion successful
- `failed` - Ingestion failed (see error field)
- `canceled` - Job was canceled
- `stopped` - Worker stopped unexpectedly

---

### **DELETE /api/ingest/job/{job_id}**

Cancel a pending or running ingestion job.

**Request:**
- Method: `DELETE`
- Path Parameter: `job_id`

**Example:**
```bash
curl -X DELETE http://localhost:8000/api/ingest/job/abc123-def456-ghi789
```

**Response:**
```json
{
  "status": "cancelled",
  "message": "Job abc123-def456-ghi789 cancelled"
}
```

---

##  Configuration

### **Environment Variables**

#### Backend Service:
```bash
# Redis Configuration
REDIS_HOST=redis                 # Redis hostname
REDIS_PORT=6379                   # Redis port
REDIS_DB=0                        # Redis database number

# Milvus Configuration
MILVUS_HOST=milvus
MILVUS_PORT=19530
COLLECTION_NAME=enterprise_docs

# Embedding Configuration
EMBEDDING_MODEL=BAAI/bge-base-en
EMBEDDING_DIM=768
```

#### Ingestion Worker:
```bash
# Same as backend, plus:
# (Worker automatically inherits configuration)
```

---

##  Monitoring

### **View Worker Logs**

```bash
# Real-time logs
docker compose logs -f ingestion

# Last 100 lines
docker compose logs --tail 100 ingestion
```

**Expected Log Output:**
```
 Starting RQ worker for ingestion queue...
 Connected to Redis at redis:6379
 Worker ready to process jobs from 'ingestion' queue
 Queue size: 0

 Starting ingestion for: /app/uploads/abc123_document.txt
 Read 24500 characters from /app/uploads/abc123_document.txt
  Split into 8 chunks
 Generating embeddings for 8 chunks...
[x] Generated 8 embeddings
 Inserting 8 chunks into Milvus...
[x] Ingestion complete for document.txt in 45.2s
```

### **Check Redis Queue Status**

```bash
# Connect to Redis
docker exec -it rag-redis redis-cli

# Check queue length
LLEN rq:queue:ingestion

# List all keys
KEYS *

# Exit
exit
```

### **Monitor Backend API**

```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs
```

---

##  Testing

### **Test with Sample Document**

```bash
# Create a test document
cat > test_document.txt << 'EOF'
# Enterprise RAG System Test Document

This is a test document for the RAG ingestion pipeline.

## Key Features

1. Asynchronous processing
2. Redis message queue
3. Distributed workers
4. Scalable architecture

## Technical Details

The system uses:
- FastAPI for the REST API
- RQ (Redis Queue) for job management
- Milvus for vector storage
- BAAI/bge-base-en for embeddings
EOF

# Upload the document
curl -X POST http://localhost:8000/api/ingest/upload \
  -F "file=@test_document.txt" \
  -o response.json

# Extract job ID
JOB_ID=$(cat response.json | grep -o '"job_id":"[^"]*' | cut -d'"' -f4)

echo "Job ID: $JOB_ID"

# Wait a bit for processing
sleep 10

# Check status
curl http://localhost:8000/api/ingest/status/$JOB_ID

# Query the document
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key features of the RAG system?",
    "session_id": "test"
  }'
```

---

##  Advanced Usage

### **Batch Upload Multiple Documents**

```bash
#!/bin/bash
# batch_upload.sh

FILES=(
  "document1.txt"
  "document2.txt"
  "document3.txt"
)

for file in "${FILES[@]}"; do
  echo "Uploading $file..."
  curl -X POST http://localhost:8000/api/ingest/upload \
    -F "file=@$file" \
    -s | jq '.'
  sleep 1
done
```

### **Poll Job Status Until Complete**

```bash
#!/bin/bash
# wait_for_job.sh

JOB_ID=$1

while true; do
  STATUS=$(curl -s http://localhost:8000/api/ingest/status/$JOB_ID | jq -r '.status')
  echo "Status: $STATUS"
  
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    curl -s http://localhost:8000/api/ingest/status/$JOB_ID | jq '.'
    break
  fi
  
  sleep 5
done
```

### **Scale Workers**

```bash
# Scale to 3 workers for higher throughput
docker compose up -d --scale ingestion=3

# Check running workers
docker compose ps | grep ingestion
```

---

##  Troubleshooting

### **"Ingestion service not available"**

**Problem:** Redis connection failed

**Solution:**
```bash
# Check Redis is running
docker compose ps redis

# Check Redis health
docker exec rag-redis redis-cli ping

# Restart services
docker compose restart redis backend ingestion
```

### **Jobs stuck in "queued" status**

**Problem:** Worker not processing jobs

**Solution:**
```bash
# Check worker logs
docker compose logs ingestion

# Restart worker
docker compose restart ingestion

# Check queue manually
docker exec -it rag-redis redis-cli LLEN rq:queue:ingestion
```

### **"File format not supported"**

**Problem:** Uploaded non-text file

**Solution:**
- Only `.txt`, `.md`, and `.text` files are supported
- Convert other formats to text first
- For PDFs, use: `pdftotext document.pdf document.txt`

### **Worker crashes during embedding**

**Problem:** Out of memory

**Solution:**
```bash
# Increase Docker memory limit in Docker Desktop
# Or reduce batch size in pipeline.py

# Check memory usage
docker stats rag-ingestion
```

---

##  Performance

### **Benchmarks**

| Document Size | Chunks | Embedding Time | Total Time |
|--------------|--------|----------------|------------|
| 10 KB | 3 | ~2s | ~5s |
| 50 KB | 15 | ~8s | ~15s |
| 100 KB | 30 | ~15s | ~30s |
| 500 KB | 150 | ~75s | ~120s |

*Tested on M1 MacBook Pro with BAAI/bge-base-en*

### **Optimization Tips**

1. **Scale workers** for concurrent processing:
   ```bash
   docker compose up -d --scale ingestion=5
   ```

2. **Use smaller embedding model** for faster processing:
   ```bash
   EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
   ```

3. **Adjust chunk size** in `ingestion/pipeline.py`:
   ```python
   chunks = self.chunk_text(content, max_chars=2000, overlap=300)
   ```

4. **Pre-process large documents** before upload:
   - Remove unnecessary content
   - Split into multiple files
   - Clean formatting

---

##  Best Practices

1. **File Naming**
   - Use descriptive filenames
   - Avoid special characters
   - Keep names under 100 characters

2. **Document Quality**
   - Remove duplicate content
   - Fix encoding issues
   - Use proper formatting

3. **Error Handling**
   - Always check job status
   - Handle failed jobs gracefully
   - Implement retry logic

4. **Security**
   - Validate file content
   - Scan for malicious content
   - Implement rate limiting

---

##  Future Enhancements

- [ ] Support for PDF files
- [ ] Support for DOCX files
- [ ] Automatic retries for failed jobs
- [ ] Bulk upload API
- [ ] Progress updates via WebSocket
- [ ] Job prioritization
- [ ] Scheduled ingestion
- [ ] File watcher for auto-ingestion
- [ ] Admin dashboard for job management

---

##  Related Documentation

- [Architecture Overview](./ARCHITECTURE.md)
- [Quick Start Guide](./QUICKSTART.md)
- [API Documentation](http://localhost:8000/docs)
- [RAG Pipeline Implementation](./backend/rag_pipeline.py)

---

**Need Help?** Check the logs or open an issue on GitHub! 
