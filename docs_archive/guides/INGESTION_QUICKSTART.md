# Quick Start: Document Ingestion

##  Get Started in 3 Minutes

### Step 1: Start All Services

```bash
cd rag-enterprise
docker compose up -d
```

Wait ~2 minutes for all services to initialize.

### Step 2: Upload a Document

```bash
# Create a sample document
cat > my_document.txt << 'EOF'
# Company Security Policy

## Password Requirements
- Minimum 12 characters
- Must include uppercase, lowercase, numbers, and symbols
- Changed every 90 days

## Access Control
- All sensitive data requires MFA
- VPN required for remote access
EOF

# Upload it
curl -X POST http://localhost:8000/api/ingest/upload \
  -F "file=@my_document.txt"
```

**Response:**
```json
{
  "job_id": "abc123-def456-ghi789",
  "status": "queued",
  "message": "Document 'my_document.txt' queued for ingestion"
}
```

### Step 3: Check Processing Status

```bash
# Replace with your job_id from step 2
curl http://localhost:8000/api/ingest/status/abc123-def456-ghi789
```

Wait until status is `"completed"` (~10-30 seconds for small documents).

### Step 4: Query Your Document

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the password requirements?",
    "session_id": "my-session"
  }'
```

**Response:**
```json
{
  "answer": "According to the security policy, passwords must be:\n- Minimum 12 characters\n- Include uppercase, lowercase, numbers, and symbols\n- Changed every 90 days",
  "sources": [
    {
      "title": "my_document.txt",
      "text": "## Password Requirements\n- Minimum 12 characters..."
    }
  ],
  "latency_ms": 1234.56,
  "session_id": "my-session"
}
```

## [x] That's It!

Your document is now searchable in the RAG system!

---

##  Troubleshooting

### Services not running?

```bash
# Check service status
docker compose ps

# View logs
docker compose logs backend
docker compose logs ingestion
docker compose logs redis
```

### Job stuck in "queued" status?

```bash
# Check worker is processing
docker compose logs -f ingestion

# Restart worker
docker compose restart ingestion
```

### Upload failed?

- [x] File must be `.txt` or `.md`
- [x] File must not be empty
- [x] Backend must be running on port 8000

---

##  Next Steps

- [Full API Documentation](./INGESTION_API_GUIDE.md)
- [Implementation Details](./INGESTION_IMPLEMENTATION_SUMMARY.md)
- [Run Tests](./test_ingestion.sh)

---

##  Features

- [x] **Asynchronous** - Upload returns immediately
- [x] **Scalable** - Run multiple workers: `docker compose up -d --scale ingestion=3`
- [x] **Reliable** - Jobs are persisted in Redis
- [x] **Trackable** - Check status anytime with job ID
- [x] **Automatic** - Chunking, embedding, and indexing handled automatically

---

**Need help?** Check the [full documentation](./INGESTION_API_GUIDE.md) or open an issue! 
