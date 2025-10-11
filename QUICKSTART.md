# 🚀 Quick Start Guide

## One-Command Setup

```bash
docker compose up --build
```

## Access the Application

After 2-3 minutes (first time only):

- **Chat Interface**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Example Queries

Try asking:
- "What is the PTO policy?"
- "How many holidays do we get?"
- "What happens during onboarding?"
- "Can I rollover unused PTO?"
- "What are the performance review dates?"
- "What benefits are offered?"

## Using the Startup Script

For easier management:

```bash
# Start services
./start.sh start

# View logs
./start.sh logs

# Stop services
./start.sh stop

# Check status
./start.sh status

# Clean everything
./start.sh clean
```

## Architecture Overview

```
User → React UI → FastAPI → [Embeddings + Milvus + LLM] → Response
```

1. **Query Embedding**: User query converted to vector (BGE-Large-En)
2. **Vector Search**: Find similar documents in Milvus
3. **Context Building**: Combine top-3 results
4. **Answer Generation**: LLM generates response
5. **Display**: Show answer + sources + latency

## Configuration

### Switch to Mistral API (Production)

Edit `backend/.env`:
```env
LLM_MODE=api
MISTRAL_API_KEY=your_actual_api_key
```

Restart backend:
```bash
docker compose restart backend
```

## Adding Your Documents

1. Add `.txt` files to `data/` folder
2. Restart backend:
   ```bash
   docker compose restart backend
   ```

Documents are automatically indexed on startup.

## Troubleshooting

### Services not starting?
- Ensure Docker Desktop is running
- Check ports 3000, 8000, 19530 are free
- Increase Docker memory to 8GB minimum

### "Connection refused" errors?
- Wait 2-3 minutes for Milvus initialization
- Check health: `curl http://localhost:9091/healthz`

### Out of memory?
- BGE model needs ~4GB RAM
- Adjust Docker memory limits in Settings

## Development Mode

### Backend only:
```bash
cd backend
pip install -r requirements.txt
python main.py
```

### Frontend only:
```bash
cd frontend
npm install
npm start
```

## Next Steps

1. ✅ Start the application
2. ✅ Try example queries
3. ✅ Add your own documents
4. ✅ Customize for your use case

For detailed documentation, see [README.md](README.md)
