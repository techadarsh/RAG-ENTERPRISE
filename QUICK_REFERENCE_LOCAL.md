# Quick Reference - RAG Enterprise Local Setup

## 🚀 Start System (One Command)

```bash
./start_local.sh start
```

**Wait 2 minutes**, then access:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs

---

## 🛑 Stop System

```bash
./start_local.sh stop
```

---

## 📊 Check Status

```bash
./start_local.sh status
```

---

## 📋 View Logs

```bash
# Backend
tail -f /tmp/rag-backend.log

# Frontend
tail -f /tmp/rag-frontend.log

# All services
./start_local.sh logs all
```

---

## 🧪 Test Query (CLI)

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the agile workflow?"}'
```

---

## 🏥 Health Check

```bash
curl http://localhost:8000/health/deps | python3 -m json.tool
```

Expected output:
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

---

## 🔄 Restart Services

```bash
./start_local.sh restart
```

---

## 🧹 Clean Shutdown

```bash
./start_local.sh clean
```

---

## 🐛 Troubleshooting

### Backend won't start

```bash
# Check Python environment
python3 --version  # Should be 3.11.x

# Reinstall dependencies
source venv/bin/activate
pip install -r backend/requirements.txt

# Check logs
tail -50 /tmp/rag-backend.log
```

### Frontend won't compile

```bash
# Check Node version
node --version  # Should be v25.2.0 or v23+

# Reinstall packages
cd frontend
rm -rf node_modules
npm install
```

### Milvus connection errors

```bash
# Check Milvus container
docker ps | grep milvus

# Restart Milvus
docker restart milvus-standalone
```

### Ollama not responding

```bash
# Check if Ollama is running
ps aux | grep ollama

# Start Ollama manually
ollama serve > /tmp/ollama.log 2>&1 &

# Verify Mistral model
ollama list | grep mistral
```

---

## 📦 Sample Documents

Located in: `data/sample_confluence_pages/`

**Count**: 14 documents (all `.txt` files)

To add more documents:
1. Place `.txt` files in `data/sample_confluence_pages/`
2. Restart system: `./start_local.sh restart`

---

## 🎯 Performance Expectations

- **First query** (cold start): ~10-15 seconds
- **Subsequent queries**: ~5-8 seconds
- **Document retrieval**: <1 second
- **LLM generation**: ~5-8 seconds

**8-10x faster than Docker** 🚀

---

## ⚡ Commands Cheat Sheet

| Task | Command |
|------|---------|
| Start all services | `./start_local.sh start` |
| Stop all services | `./start_local.sh stop` |
| Check status | `./start_local.sh status` |
| Restart services | `./start_local.sh restart` |
| View backend logs | `tail -f /tmp/rag-backend.log` |
| View frontend logs | `tail -f /tmp/rag-frontend.log` |
| Test health | `curl http://localhost:8000/health/deps` |
| Test query | `curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"query": "test"}'` |
| Open frontend | Open http://localhost:3000 |
| Open API docs | Open http://localhost:8000/docs |
| Clean restart | `./start_local.sh clean && ./start_local.sh start` |

---

## 🎓 Important Notes

1. **Wait 2 minutes** after starting for backend to fully initialize (document loading + topic extraction)
2. **First query is slower** due to model warm-up (~10-15s)
3. **Sample documents are auto-loaded** during backend startup
4. **Metal GPU is used** by Ollama for 8-10x performance improvement
5. **All services must be running** before testing queries

---

## 🔗 Access URLs

| Service | URL |
|---------|-----|
| Frontend UI | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health/deps |
| Ollama | http://localhost:11434 |
| Milvus | http://localhost:19530 |

---

**Quick Start**: `./start_local.sh start` → Wait 2 minutes → Open http://localhost:3000

✅ **System is now running locally on Mac Mini M4 Pro with Metal GPU acceleration!**
