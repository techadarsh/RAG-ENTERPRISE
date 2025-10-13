# Dev Mode Quick Reference

## Fixed Issues ✅

### 1. Shell Script Error (RESOLVED)
**Error:** `export: '#': not a valid identifier`

**Cause:** Inline comments in `.env` file after emoji removal

**Fix Applied:**
```bash
# Before (BROKEN)
export $(grep -v '^#' .env | xargs)

# After (FIXED)
export $(grep -v '^#' .env | sed 's/#.*$//' | grep -v '^[[:space:]]*$' | xargs)
```

### 2. Missing Services (RESOLVED)
**Issue:** Ingestion and Trigger services not starting in dev mode

**Fix Applied:**
- Added `ingestion` to startup sequence
- Added `trigger` with `--profile trigger` flag
- Added service verification checks

---

## Usage

### Start Development Mode
```bash
./scripts/dev-mode.sh
```

**What it does:**
1. Starts infrastructure (Milvus, Redis, Ollama, etc.)
2. Ensures Ollama model is downloaded
3. Starts backend with hot-reload
4. Starts frontend with hot-reload  
5. Starts ingestion worker
6. Starts trigger service (file watcher)
7. Waits for health checks

### Services Started

| Service | Purpose | Hot Reload |
|---------|---------|------------|
| **rag-backend** | FastAPI REST API | ✅ Yes (Python) |
| **rag-frontend** | React UI | ✅ Yes (React) |
| **rag-ingestion** | Document processor | ⚠️ Restart needed |
| **rag-trigger** | File watcher | ⚠️ Restart needed |
| milvus | Vector database | ❌ No |
| redis | Job queue | ❌ No |
| rag-ollama | LLM inference | ❌ No |

---

## Access URLs

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health/deps

---

## Testing Ingestion

### Method 1: Drop File (Auto-Ingestion via Trigger)
```bash
# Copy file to watched directory
cp myfile.txt ./data/incoming/

# Watch trigger service logs
docker compose logs -f trigger

# Watch ingestion worker logs
docker compose logs -f ingestion

# Check processed files
ls -lh ./data/incoming/processed/
```

### Method 2: API Upload
```bash
# Upload via REST API
curl -X POST http://localhost:8000/ingest/file \
  -F "file=@myfile.txt" \
  -F "source_name=My Document"

# Check job status
curl http://localhost:8000/ingest/jobs
```

### Method 3: Direct Ingestion
```bash
# Run ingestion script directly
./test_ingestion.sh
```

---

## Useful Commands

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f ingestion
docker compose logs -f trigger

# Last 50 lines
docker compose logs --tail=50 backend
```

### Restart Services
```bash
# Restart backend (after code changes)
docker compose restart backend

# Restart ingestion worker
docker compose restart ingestion

# Restart trigger service
docker compose restart trigger

# Restart all
docker compose restart
```

### Stop Services
```bash
# Stop all (including trigger)
docker compose --profile trigger down

# Stop specific service
docker compose stop backend

# Stop and remove volumes (DANGER: deletes data)
docker compose --profile trigger down -v
```

### Check Service Status
```bash
# List running containers
docker compose ps

# Check specific service health
docker compose exec backend curl http://localhost:8000/health/deps

# Check ingestion worker
docker compose exec ingestion ps aux | grep python
```

### Shell Access
```bash
# Backend shell
docker compose exec backend bash

# Ingestion shell
docker compose exec ingestion bash

# Trigger shell
docker compose exec trigger bash

# Redis CLI
docker compose exec redis redis-cli
```

---

## Hot Reload Details

### Backend (Python)
- **Watch path:** `./backend/`
- **Trigger:** File save
- **Reload time:** ~2-3 seconds
- **Logs:** `docker compose logs -f backend`

### Frontend (React)
- **Watch path:** `./frontend/src/`
- **Trigger:** File save
- **Reload time:** ~5-10 seconds (Vite rebuild)
- **Logs:** `docker compose logs -f frontend`

### Ingestion/Trigger (Manual Restart)
```bash
# Edit file
vim ingestion/worker.py

# Restart service
docker compose restart ingestion

# Check logs
docker compose logs -f ingestion
```

---

## Troubleshooting

### Issue: Services not starting
```bash
# Check Docker is running
docker ps

# Check logs for errors
docker compose logs backend
docker compose logs ingestion
```

### Issue: Backend not reloading
```bash
# Check volume mount
docker compose exec backend ls -la /app/backend

# Force restart
docker compose restart backend
```

### Issue: Trigger not watching files
```bash
# Check trigger logs
docker compose logs trigger

# Verify directory mount
docker compose exec trigger ls -la /app/data/incoming

# Verify inotify is working
docker compose exec trigger sh -c "ls /app/data/incoming"
```

### Issue: Redis connection failed
```bash
# Check Redis health
docker compose exec redis redis-cli ping

# Should return: PONG

# Check Redis logs
docker compose logs redis
```

### Issue: Milvus connection failed
```bash
# Check Milvus health
curl http://localhost:19530/healthz

# Check Milvus logs
docker compose logs milvus
```

---

## Environment Variables

Key variables loaded from `.env`:

```bash
# LLM
LLM_HOST=rag-ollama
LLM_PORT=11434
LLM_MODEL=mistral
LLM_MAX_TOKENS=256

# Retrieval
RETRIEVAL_TOP_K=5
MAX_CONTEXT_CHARS=2000

# API
API_PORT=8000

# Milvus
MILVUS_HOST=milvus
MILVUS_PORT=19530
```

**Note:** Inline comments in `.env` are now properly handled!

---

## Development Workflow

### 1. Start Dev Mode
```bash
./scripts/dev-mode.sh
```

### 2. Make Code Changes
```bash
# Backend changes (auto-reload)
vim backend/rag_pipeline.py

# Frontend changes (auto-reload)
vim frontend/src/App.js

# Ingestion changes (manual restart)
vim ingestion/pipeline.py
docker compose restart ingestion
```

### 3. Test Changes
```bash
# Test backend endpoint
curl http://localhost:8000/health/deps

# Test ingestion
cp data/sample_confluence_pages/agile_workflow.txt data/incoming/

# Check frontend
open http://localhost:3000
```

### 4. View Logs
```bash
docker compose logs -f backend ingestion trigger
```

### 5. Stop When Done
```bash
docker compose --profile trigger down
```

---

## Quick Tests

### Test 1: Backend Health
```bash
curl http://localhost:8000/health/deps | jq
```

**Expected:**
```json
{
  "milvus": "ok",
  "embeddings": "ok",
  "redis": "ok",
  "ollama": "ok"
}
```

### Test 2: Ask Question
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the agile workflow?"}'
```

### Test 3: File Ingestion
```bash
cp data/sample_confluence_pages/agile_workflow.txt data/incoming/
sleep 5
docker compose logs trigger | tail -20
docker compose logs ingestion | tail -20
```

---

## Performance Tips

1. **Reduce LLM tokens** for faster responses:
   ```bash
   # In .env
   LLM_MAX_TOKENS=128
   docker compose restart backend
   ```

2. **Reduce retrieval chunks** for faster search:
   ```bash
   # In .env
   RETRIEVAL_TOP_K=3
   docker compose restart backend
   ```

3. **Use cache** for repeated queries:
   ```bash
   # In .env
   RETRIEVAL_CACHE_SIZE=100
   docker compose restart backend
   ```

---

## Summary

✅ **Fixed:** Shell script inline comment handling  
✅ **Added:** Ingestion service to dev mode  
✅ **Added:** Trigger service to dev mode  
✅ **Added:** Service verification checks  
✅ **Updated:** Help text and documentation  

**Result:** Full development environment with hot-reload and auto-ingestion! 🚀
