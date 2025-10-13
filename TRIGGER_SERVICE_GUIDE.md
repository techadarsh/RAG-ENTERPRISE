# Auto-Trigger Ingestion Service Guide

## 📋 Overview

The Auto-Trigger Ingestion Service (Phase 2) enables automatic document ingestion without manual API calls. It supports three trigger mechanisms:

1. **📂 Folder Watcher** - Monitors local directory for new/modified files
2. **☁️  S3/MinIO Listener** - Listens to bucket upload events
3. **🔔 Confluence Webhook** - Receives webhook notifications for page updates

All triggers enqueue ingestion jobs to Redis queue for processing by the ingestion worker service.

---

## 🏗️ Architecture

```
┌─────────────────────┐
│  Trigger Sources    │
├─────────────────────┤
│ • Folder Watcher    │──┐
│ • S3/MinIO Events   │──┼──> Redis Queue ──> Ingestion Worker ──> Milvus
│ • Confluence Webhook│──┘
└─────────────────────┘
```

### Components

- **trigger/** - Trigger service with watcher, S3 listener, and orchestrator
- **backend/main.py** - Confluence webhook endpoint (`/api/webhook/confluence`)
- **ingestion/pipeline.py** - Document and URL ingestion jobs
- **Redis** - Message queue for job coordination
- **Docker Compose** - Orchestrates all services

---

## 🚀 Quick Start

### 1. Enable Folder Watcher

```bash
# Edit .env or backend/.env
ENABLE_FOLDER_WATCHER=true
WATCH_DIR=/app/data/incoming

# Start services with trigger profile
docker compose --profile trigger up -d

# Drop a file in the watched folder
cp my_document.txt data/incoming/

# Check logs
docker compose logs -f trigger
```

**Expected output:**
```
📂 New file detected (created): my_document.txt → Enqueued job abc-123
```

### 2. Enable S3/MinIO Listener

```bash
# Edit .env
ENABLE_S3_TRIGGER=true
MINIO_ENDPOINT=http://minio:9000
S3_BUCKET_NAME=documents
S3_WATCH_PREFIX=incoming/

# Start services
docker compose --profile trigger up -d

# Upload file to MinIO bucket (via MinIO console at http://localhost:9001)
# Or use AWS CLI/SDK

# Check logs
docker compose logs -f trigger
```

**Expected output:**
```
☁️  S3 event received: incoming/report.pdf → Downloaded → Enqueued job def-456
```

### 3. Setup Confluence Webhook

```bash
# Configure webhook secret (optional)
echo "CONFLUENCE_WEBHOOK_SECRET=your-secret-key" >> .env

# Restart backend
docker compose restart backend

# Configure webhook in Confluence:
# 1. Go to Settings → Webhooks
# 2. Create webhook with URL: http://your-server:8000/api/webhook/confluence
# 3. Enable events: Page Created, Page Updated
# 4. Save

# When a page is created/updated in Confluence:
```

**Backend logs:**
```
🔔 Confluence webhook received: page_updated
   Page ID: 12345
   Title: Engineering Guidelines
   URL: https://yourcompany.atlassian.net/wiki/spaces/ENG/pages/12345
🔔 Confluence webhook processed → Enqueued job ghi-789
```

---

## ⚙️ Configuration

### Environment Variables

#### Folder Watcher Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_FOLDER_WATCHER` | `false` | Enable folder monitoring |
| `WATCH_DIR` | `/app/data/incoming` | Directory to monitor |

#### S3/MinIO Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_S3_TRIGGER` | `false` | Enable S3/MinIO listener |
| `MINIO_ENDPOINT` | `http://minio:9000` | MinIO/S3 endpoint URL |
| `MINIO_ACCESS_KEY` | `minioadmin` | Access key |
| `MINIO_SECRET_KEY` | `minioadmin` | Secret key |
| `S3_BUCKET_NAME` | `documents` | Bucket to monitor |
| `S3_WATCH_PREFIX` | `incoming/` | Object prefix filter |
| `S3_DOWNLOAD_DIR` | `/app/data/s3_downloads` | Temporary download location |

#### Confluence Webhook Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CONFLUENCE_WEBHOOK_SECRET` | *(empty)* | Optional webhook signature validation |

#### Redis Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `redis` | Redis hostname |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_DB` | `0` | Redis database number |

---

## 📂 Folder Watcher Details

### Supported File Types

- `.txt` - Plain text files
- `.md` - Markdown files
- `.pdf` - PDF documents (requires PDF parser)
- `.doc`, `.docx` - Microsoft Word documents (requires docx parser)

### Ignored Patterns

The watcher automatically ignores:
- Temporary files (`.tmp`, `.swp`)
- System files (`.DS_Store`, `.lock`)
- Files with `~` in the name

### Behavior

- **File Created** → Immediately enqueued
- **File Modified** → Enqueued (with deduplication)
- **Recursive Monitoring** → Watches subdirectories
- **Retry Logic** → 3 attempts with exponential backoff

### Example

```bash
# Watch logs in real-time
docker compose logs -f trigger

# In another terminal, add files
echo "Important document" > data/incoming/test1.txt
cp /path/to/report.pdf data/incoming/

# Organize in subdirectories (also monitored)
mkdir -p data/incoming/policies
cp hr_policy.txt data/incoming/policies/
```

---

## ☁️ S3/MinIO Listener Details

### Setup MinIO Bucket

```bash
# Access MinIO console
open http://localhost:9001

# Login: minioadmin / minioadmin

# Create bucket named "documents"
# Create folder "incoming/"
# Upload files to incoming/
```

### Event Types

The listener subscribes to:
- `s3:ObjectCreated:*` - All object creation events
  - `s3:ObjectCreated:Put`
  - `s3:ObjectCreated:Post`
  - `s3:ObjectCreated:Copy`

### Workflow

1. File uploaded to `s3://documents/incoming/file.pdf`
2. MinIO sends notification event
3. Trigger service receives event
4. File downloaded to `/app/data/s3_downloads/`
5. Ingestion job enqueued with local file path
6. Worker processes file → embeds → stores in Milvus
7. Temporary file cleaned up

### AWS S3 Integration

To use AWS S3 instead of local MinIO:

```bash
# Update .env
ENABLE_S3_TRIGGER=true
MINIO_ENDPOINT=https://s3.amazonaws.com
MINIO_ACCESS_KEY=your-aws-access-key
MINIO_SECRET_KEY=your-aws-secret-key
S3_BUCKET_NAME=your-bucket-name
S3_WATCH_PREFIX=documents/incoming/

# Note: Bucket must have notifications configured
# See: https://docs.aws.amazon.com/AmazonS3/latest/userguide/NotificationHowTo.html
```

---

## 🔔 Confluence Webhook Details

### Webhook Endpoint

```
POST http://your-server:8000/api/webhook/confluence
```

### Expected Payload

```json
{
  "event": "page_created",
  "page": {
    "id": "12345",
    "title": "Engineering Guidelines",
    "url": "https://yourcompany.atlassian.net/wiki/spaces/ENG/pages/12345",
    "space": {
      "key": "ENG",
      "name": "Engineering"
    }
  }
}
```

### Setup in Confluence

1. **Go to Space Settings** → Webhooks (or Confluence Settings for global webhooks)
2. **Click "Create Webhook"**
3. **Configure:**
   - Name: `RAG Ingestion Webhook`
   - URL: `http://your-server:8000/api/webhook/confluence`
   - Events: Select `Page Created` and `Page Updated`
   - (Optional) Add custom header for authentication
4. **Save**

### Testing

```bash
# Test webhook with curl
curl -X POST http://localhost:8000/api/webhook/confluence \
  -H "Content-Type: application/json" \
  -d '{
    "event": "page_created",
    "page": {
      "id": "test123",
      "title": "Test Page",
      "url": "https://example.atlassian.net/wiki/spaces/TEST/pages/123"
    }
  }'

# Expected response:
{
  "status": "success",
  "message": "Confluence page 'Test Page' queued for ingestion",
  "job_id": "xyz-789"
}

# Check job status
curl http://localhost:8000/api/ingest/status/xyz-789
```

### Security

For production deployments:

1. **Use HTTPS** for webhook endpoint
2. **Configure webhook secret** in `.env`
3. **Validate webhook signatures** (implement in backend)
4. **Restrict IP addresses** (firewall rules)
5. **Use API authentication** (add Bearer token validation)

---

## 🐳 Docker Compose Usage

### Standard Mode (No Auto-Triggers)

```bash
# Start core services only
docker compose up -d

# This starts: milvus, redis, backend, ingestion, frontend
```

### With Auto-Triggers

```bash
# Start all services including trigger service
docker compose --profile trigger up -d

# Verify trigger service is running
docker compose ps
# Should show: rag-trigger (running)

# View trigger logs
docker compose logs -f trigger
```

### Stop Trigger Service

```bash
# Stop only trigger service
docker compose --profile trigger stop trigger

# Or remove it
docker compose --profile trigger rm -f trigger
```

### Restart with New Configuration

```bash
# After editing .env
docker compose --profile trigger restart trigger

# Or rebuild if code changed
docker compose --profile trigger up -d --build trigger
```

---

## 🧪 Testing

### Manual Testing

#### Test Folder Watcher

```bash
# 1. Enable and start
echo "ENABLE_FOLDER_WATCHER=true" >> .env
docker compose --profile trigger up -d

# 2. Create test file
echo "Test document content" > data/incoming/test.txt

# 3. Check trigger logs
docker compose logs trigger | grep "test.txt"
# Should show: 📂 New file detected (created): test.txt → Enqueued job ...

# 4. Check ingestion worker logs
docker compose logs ingestion | grep "test.txt"
# Should show: ✅ Successfully ingested (test.txt)

# 5. Query the document
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test document"}'
```

#### Test Confluence Webhook

```bash
# 1. Start services
docker compose up -d

# 2. Send test webhook
curl -X POST http://localhost:8000/api/webhook/confluence \
  -H "Content-Type: application/json" \
  -d '{
    "event": "page_created",
    "page": {
      "id": "test123",
      "title": "Test Confluence Page",
      "url": "https://httpbin.org/html"
    }
  }'

# 3. Get job ID from response and check status
curl http://localhost:8000/api/ingest/status/<job-id>
```

### Automated Testing

See `test_trigger.sh` for comprehensive automated tests.

```bash
# Run all tests
./test_trigger.sh

# Run specific test
./test_trigger.sh folder    # Test folder watcher only
./test_trigger.sh webhook   # Test webhook only
```

---

## 📊 Monitoring

### View Trigger Logs

```bash
# Real-time logs
docker compose logs -f trigger

# Last 100 lines
docker compose logs --tail=100 trigger

# Filter by pattern
docker compose logs trigger | grep "Enqueued"
```

### Check Redis Queue

```bash
# Connect to Redis
docker exec -it rag-redis redis-cli

# View queue length
LLEN rq:queue:ingestion

# View all queues
KEYS rq:queue:*

# View job details
HGETALL rq:job:<job-id>
```

### Monitor Job Status

```bash
# Check specific job
curl http://localhost:8000/api/ingest/status/<job-id>

# Monitor ingestion worker
docker compose logs -f ingestion
```

---

## 🛠️ Troubleshooting

### Trigger Service Not Starting

**Problem:** Container exits immediately

**Check:**
```bash
# View logs
docker compose logs trigger

# Common issues:
# - No triggers enabled (both ENABLE_FOLDER_WATCHER and ENABLE_S3_TRIGGER are false)
# - Redis connection failed
# - MinIO connection failed (if S3 trigger enabled)
```

**Solution:**
```bash
# Enable at least one trigger
echo "ENABLE_FOLDER_WATCHER=true" >> .env

# Verify Redis is running
docker compose ps redis

# Restart trigger service
docker compose --profile trigger restart trigger
```

### Files Not Being Detected

**Problem:** Files added to `data/incoming/` but not processed

**Check:**
1. Is trigger service running?
   ```bash
   docker compose ps trigger
   ```

2. Is folder watcher enabled?
   ```bash
   docker compose exec trigger env | grep ENABLE_FOLDER_WATCHER
   # Should show: ENABLE_FOLDER_WATCHER=true
   ```

3. Is file type supported?
   ```bash
   # Supported: .txt, .md, .pdf, .doc, .docx
   ```

4. Check trigger logs:
   ```bash
   docker compose logs trigger
   # Look for "Ignoring unsupported file type" or errors
   ```

### S3 Events Not Received

**Problem:** MinIO uploads don't trigger ingestion

**Check:**
1. Is S3 trigger enabled?
   ```bash
   grep ENABLE_S3_TRIGGER .env
   # Should be: true
   ```

2. MinIO bucket exists and accessible:
   ```bash
   # Access MinIO console
   open http://localhost:9001
   # Verify "documents" bucket exists
   ```

3. Bucket notifications configured:
   ```bash
   # MinIO automatically subscribes to events via listen_bucket_notification
   # Check trigger logs for connection errors
   docker compose logs trigger | grep MinIO
   ```

### Confluence Webhook Fails

**Problem:** Webhook returns 500 error

**Check:**
1. Backend has Redis connection:
   ```bash
   docker compose logs backend | grep Redis
   # Should show: ✅ Connected to Redis
   ```

2. Payload format is correct:
   ```json
   {
     "event": "page_created",
     "page": {
       "id": "123",
       "title": "Title",
       "url": "https://..."  // Required!
     }
   }
   ```

3. Backend logs for errors:
   ```bash
   docker compose logs backend | grep webhook
   ```

---

## 🔧 Advanced Configuration

### Custom File Extensions

Edit `trigger/watcher.py`:

```python
# Add to SUPPORTED_EXTENSIONS
SUPPORTED_EXTENSIONS = {'.txt', '.md', '.pdf', '.doc', '.docx', '.rtf', '.odt'}
```

### Adjust Retry Logic

Edit `trigger/watcher.py`:

```python
# Increase max retries
def __init__(self, redis_queue: Queue, max_retries: int = 5):
    ...
```

### Multiple Watch Directories

Currently supports one directory. To watch multiple:

```bash
# Option 1: Use subdirectories (automatically watched recursively)
data/incoming/hr/
data/incoming/engineering/
data/incoming/legal/

# Option 2: Run multiple trigger containers (advanced)
# - Create multiple docker compose services
# - Each with different WATCH_DIR
```

---

## 📚 Additional Resources

- **Phase 1 Documentation**: See `INGESTION_API_GUIDE.md` for manual API ingestion
- **Architecture**: See `README.md` for system architecture
- **Ingestion Pipeline**: See `ingestion/pipeline.py` for processing details
- **Backend API**: See `backend/main.py` for webhook implementation

---

## ✅ Summary

### Three Ways to Trigger Ingestion

| Method | Use Case | Setup Complexity |
|--------|----------|------------------|
| **Manual API** | Upload via UI/API | Low |
| **Folder Watcher** | Drop files locally | Low |
| **S3/MinIO** | Cloud storage integration | Medium |
| **Confluence Webhook** | Automatic sync | Medium |

### Quick Reference

```bash
# Enable folder watcher
ENABLE_FOLDER_WATCHER=true

# Enable S3 listener
ENABLE_S3_TRIGGER=true

# Start with triggers
docker compose --profile trigger up -d

# Add files
cp document.txt data/incoming/

# Check status
docker compose logs -f trigger
curl http://localhost:8000/api/ingest/status/<job-id>
```

---

**Last Updated:** Phase 2 Implementation  
**Version:** 1.0.0  
**Status:** ✅ Production Ready
