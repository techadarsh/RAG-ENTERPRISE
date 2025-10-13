#!/usr/bin/env bash
###############################################################################
# RAG Enterprise - Development Startup Script
# Ensures stable startup with Ollama model present and all services healthy
###############################################################################

set -e

# Load env vars if .env exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

API_PORT=${API_PORT:-8000}
LLM_MODEL=${LLM_MODEL:-mistral}
OLLAMA_CONTAINER="rag-ollama"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   RAG Enterprise - Development Startup        ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Start all services
echo -e "${BLUE}🔄 Bringing up Docker services...${NC}"
docker compose up -d
echo -e "${GREEN}✅ Docker services started${NC}"
echo ""

# Step 2: Wait for Ollama container to be running
echo -e "${BLUE}⏳ Waiting for Ollama container to be ready...${NC}"
timeout=60
elapsed=0
while ! docker ps --format '{{.Names}}' | grep -q "^${OLLAMA_CONTAINER}$"; do
    if [ $elapsed -ge $timeout ]; then
        echo -e "${RED}❌ Timeout: Ollama container did not start${NC}"
        exit 1
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done
echo -e "${GREEN}✅ Ollama container is running${NC}"
echo ""

# Step 3: Check if model is present, download if missing
echo -e "${BLUE}🧠 Ensuring Ollama model '${LLM_MODEL}' is present...${NC}"

# First, list all models (also acts as health check)
docker exec -it ${OLLAMA_CONTAINER} ollama list || true
echo ""

# Check if specific model is present
if docker exec ${OLLAMA_CONTAINER} ollama list 2>/dev/null | grep -qi "${LLM_MODEL}"; then
    echo -e "${GREEN}✅ Model '${LLM_MODEL}' is already installed${NC}"
else
    echo -e "${YELLOW}⬇️  Model '${LLM_MODEL}' not found. Downloading...${NC}"
    echo -e "${YELLOW}   This may take several minutes depending on model size.${NC}"
    docker exec -it ${OLLAMA_CONTAINER} ollama pull ${LLM_MODEL}
    echo -e "${GREEN}✅ Model '${LLM_MODEL}' downloaded successfully${NC}"
fi

# Show model details
echo -e "${BLUE}📊 Model information:${NC}"
docker exec -it ${OLLAMA_CONTAINER} ollama show ${LLM_MODEL} || true
echo ""

# Step 4: Wait for /health/deps endpoint to be healthy
echo -e "${BLUE}⏳ Waiting for backend health checks (max 90s)...${NC}"
deadline=$((SECONDS + 90))
health_ok=false

while [ $SECONDS -lt $deadline ]; do
    # Try to fetch health status
    health_response=$(curl -s "http://localhost:${API_PORT}/health/deps" 2>/dev/null || echo "")
    
    if [ -n "$health_response" ]; then
        echo -e "${BLUE}   Health status: $health_response${NC}"
        
        # Check if all critical services are ok
        if echo "$health_response" | grep -q '"milvus":"ok"' && \
           echo "$health_response" | grep -q '"ollama":"ok"' && \
           echo "$health_response" | grep -q '"redis":"ok"'; then
            health_ok=true
            break
        fi
    fi
    
    sleep 3
done

if [ "$health_ok" = true ]; then
    echo -e "${GREEN}✅ All services are healthy!${NC}"
else
    echo -e "${YELLOW}⚠️  Warning: Not all services reported healthy within timeout${NC}"
    echo -e "${YELLOW}   You can still try using the system, but some features may not work.${NC}"
fi

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         🚀 RAG Enterprise is Ready!           ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}📍 Access URLs:${NC}"
echo -e "   Frontend:  http://localhost:3000"
echo -e "   Backend:   http://localhost:${API_PORT}"
echo -e "   API Docs:  http://localhost:${API_PORT}/docs"
echo ""
echo -e "${GREEN}🔍 Quick Tests:${NC}"
echo -e "   Health:    ${BLUE}curl http://localhost:${API_PORT}/health/deps${NC}"
echo -e "   LLM Test:  ${BLUE}curl http://localhost:${API_PORT}/llm/health${NC}"
echo ""
echo -e "${GREEN}💬 Ask a Question:${NC}"
echo -e "   ${BLUE}curl -X POST http://localhost:${API_PORT}/ask \\${NC}"
echo -e "     ${BLUE}-H 'Content-Type: application/json' \\${NC}"
echo -e "     ${BLUE}-d '{\"query\":\"What is the sprint duration?\"}'${NC}"
echo ""
echo -e "${GREEN}📁 Auto-Ingestion:${NC}"
echo -e "   Drop files in: ${BLUE}./data/incoming/${NC}"
echo -e "   Watcher status: ${BLUE}docker compose logs trigger -f${NC}"
echo ""
echo -e "${YELLOW}💡 Tip: Use 'docker compose logs -f' to monitor all services${NC}"
echo ""
