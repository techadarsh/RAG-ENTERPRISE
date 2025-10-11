# Quick Reference: LLM Backend Switching

This guide shows you how to switch between different LLM backends in 3 simple steps.

---

## 📝 Mock Mode (Default)

**Best for:** Development, testing, demos

### Configuration
```bash
# In .env file
LLM_MODE=mock
```

### How to Switch
```bash
# 1. Edit .env
echo "LLM_MODE=mock" > .env

# 2. Restart backend
docker compose restart backend

# 3. Test
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the leave policy?"}'
```

### What to Expect
- ✅ Instant responses (~5ms)
- 📝 Log shows: "📝 Generating mock answer"
- Returns: Template response with context snippet

---

## 🦙 Ollama (Local Inference)

**Best for:** Privacy, offline usage, no API costs

### Prerequisites
```bash
# Install Ollama
brew install ollama  # macOS
# or visit https://ollama.ai for other OS

# Start Ollama
ollama serve

# Pull model (in another terminal)
ollama pull mistral
```

### Configuration
```bash
# In .env file
LLM_MODE=api
MISTRAL_API_URL=http://host.docker.internal:11434/api/generate
MISTRAL_API_KEY=  # Leave empty
MISTRAL_MODEL=mistral
```

### How to Switch
```bash
# 1. Make sure Ollama is running
ollama serve

# 2. Edit .env
cat > .env << EOF
LLM_MODE=api
MISTRAL_API_URL=http://host.docker.internal:11434/api/generate
MISTRAL_API_KEY=
MISTRAL_MODEL=mistral
EOF

# 3. Restart backend
docker compose restart backend

# 4. Test
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "Summarize the leave policy in 3 sentences", "session_id": "test-ollama"}'
```

### What to Expect
- 🦙 Log shows: "🦙 Generating answer via Ollama"
- Response time: 2-10 seconds (depends on hardware)
- Real generated text from Mistral model

### Troubleshooting
```bash
# Check if Ollama is running
curl http://localhost:11434/api/version

# Expected response:
{"version":"0.x.x"}

# If connection error, start Ollama:
ollama serve
```

---

## 🤗 HuggingFace Inference API (Cloud)

**Best for:** Quick start, no local setup, free tier

### Prerequisites
```bash
# 1. Create account at https://huggingface.co
# 2. Generate token at https://huggingface.co/settings/tokens
#    - Name: "RAG Chatbot"
#    - Type: Read
#    - Copy the token (starts with "hf_")
```

### Configuration
```bash
# In .env file
LLM_MODE=api
MISTRAL_API_URL=https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2
MISTRAL_API_KEY=hf_YOUR_TOKEN_HERE
MISTRAL_MODEL=mistralai/Mistral-7B-Instruct-v0.2
```

### How to Switch
```bash
# 1. Get your HuggingFace token
# Visit: https://huggingface.co/settings/tokens

# 2. Edit .env (replace hf_XXX with your actual token)
cat > .env << EOF
LLM_MODE=api
MISTRAL_API_URL=https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2
MISTRAL_API_KEY=hf_YOUR_ACTUAL_TOKEN_HERE
MISTRAL_MODEL=mistralai/Mistral-7B-Instruct-v0.2
EOF

# 3. Restart backend
docker compose restart backend

# 4. Test
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the main HR policies?", "session_id": "test-hf"}'
```

### What to Expect
- 🤗 Log shows: "🤗 Generating answer via HuggingFace"
- **First request:** May take 30-60 seconds (model loading)
- **Subsequent requests:** 5-10 seconds
- Real generated text from HuggingFace model

### Troubleshooting

**Error: "Model is loading"**
```bash
# Wait 30-60 seconds and retry
# The model needs to warm up on first use
sleep 60
# Try request again
```

**Error: "Invalid API key"**
```bash
# Verify your token
echo $MISTRAL_API_KEY  # Should start with "hf_"

# Regenerate token at:
# https://huggingface.co/settings/tokens
```

---

## 🌟 Mistral AI Official API (Cloud)

**Best for:** Production, enterprise support

### Prerequisites
```bash
# 1. Create account at https://console.mistral.ai
# 2. Add payment method
# 3. Generate API key
# 4. Copy the key
```

### Configuration
```bash
# In .env file
LLM_MODE=api
MISTRAL_API_URL=https://api.mistral.ai/v1/chat/completions
MISTRAL_API_KEY=your_mistral_api_key_here
MISTRAL_MODEL=mistral-small-latest
```

### How to Switch
```bash
# 1. Get your Mistral API key
# Visit: https://console.mistral.ai

# 2. Edit .env
cat > .env << EOF
LLM_MODE=api
MISTRAL_API_URL=https://api.mistral.ai/v1/chat/completions
MISTRAL_API_KEY=your_actual_key_here
MISTRAL_MODEL=mistral-small-latest
EOF

# 3. Restart backend
docker compose restart backend

# 4. Test
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the onboarding process?", "session_id": "test-mistral"}'
```

### What to Expect
- 🌟 Log shows: "✅ Mistral API response received"
- Response time: 2-5 seconds
- High-quality generated text

---

## 🔍 How to Verify Which Backend is Active

### Check Logs
```bash
# View backend logs
docker compose logs backend | grep "🤖"

# You should see one of:
# 🤖 LLM Client initialized - Mode: mock, Backend: mock
# 🤖 LLM Client initialized - Mode: api, Backend: ollama
# 🤖 LLM Client initialized - Mode: api, Backend: huggingface
# 🤖 LLM Client initialized - Mode: api, Backend: mistral
```

### During Query
```bash
# Make a test query
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'

# Check logs for emoji indicator
docker compose logs backend | tail -20

# Look for:
# 📝 = Mock mode
# 🦙 = Ollama
# 🤗 = HuggingFace
# 🌟 = Mistral
```

---

## 🐛 Common Issues

### Issue: Backend keeps restarting
```bash
# Check logs
docker compose logs backend

# Common causes:
# 1. Invalid environment variable
# 2. Missing API key
# 3. Typo in .env file

# Solution: Verify .env syntax
cat .env
```

### Issue: "Connection refused" with Ollama
```bash
# Check if Ollama is running
ps aux | grep ollama

# Start Ollama if not running
ollama serve

# Verify it's accessible
curl http://localhost:11434/api/version
```

### Issue: "Model is loading" on HuggingFace
```bash
# This is normal for first request
# Wait 30-60 seconds and retry

# Or use a different model that's already loaded
MISTRAL_API_URL=https://api-inference.huggingface.co/models/mistralai/Mistral-7B-v0.1
```

### Issue: Backend initialized but queries fail
```bash
# 1. Check if backend is running
docker compose ps

# 2. View full logs
docker compose logs backend | tail -50

# 3. Test health endpoint
curl http://localhost:8000/health

# 4. Restart backend
docker compose restart backend
```

---

## 📊 Comparison Table

| Backend | Cost | Speed | Privacy | Setup | Quality |
|---------|------|-------|---------|-------|---------|
| Mock | Free | ⚡ Instant | 🔒 Full | ✅ None | ⭐ Template |
| Ollama | Free | 🚀 Fast | 🔒 Full | 🛠️ Medium | ⭐⭐⭐⭐ High |
| HuggingFace | Free tier | 🐌 Slow | ⚠️ Cloud | ✅ Easy | ⭐⭐⭐⭐ High |
| Mistral | Paid | 🚀 Fast | ⚠️ Cloud | ✅ Easy | ⭐⭐⭐⭐⭐ Best |

---

## 💡 Best Practices

### Development
```bash
# Use mock mode for rapid iteration
LLM_MODE=mock
```

### Local Testing
```bash
# Use Ollama for realistic responses
LLM_MODE=api
MISTRAL_API_URL=http://host.docker.internal:11434/api/generate
```

### Demo/Presentation
```bash
# Use HuggingFace for cloud-free setup
LLM_MODE=api
MISTRAL_API_URL=https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2
MISTRAL_API_KEY=hf_YOUR_TOKEN
```

### Production
```bash
# Use Mistral API for reliability
LLM_MODE=api
MISTRAL_API_URL=https://api.mistral.ai/v1/chat/completions
MISTRAL_API_KEY=your_key
```

---

## 🚀 Quick Switch Commands

### Mock → Ollama
```bash
sed -i '' 's/LLM_MODE=mock/LLM_MODE=api/' .env
echo "MISTRAL_API_URL=http://host.docker.internal:11434/api/generate" >> .env
docker compose restart backend
```

### Mock → HuggingFace
```bash
sed -i '' 's/LLM_MODE=mock/LLM_MODE=api/' .env
echo "MISTRAL_API_URL=https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2" >> .env
echo "MISTRAL_API_KEY=hf_YOUR_TOKEN" >> .env
docker compose restart backend
```

### Back to Mock
```bash
echo "LLM_MODE=mock" > .env
docker compose restart backend
```

---

**For detailed implementation notes, see `LLM_BACKEND_IMPLEMENTATION.md`**
