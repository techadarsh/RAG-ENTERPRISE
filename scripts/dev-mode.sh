#!/usr/bin/env bash
###############################################################################
# RAG Enterprise - Development Mode Starter
# Enables hot-reload for backend (Python) and frontend (React)
###############################################################################

set -e

# Load env vars if .env exists (strip inline comments)
if [ -f .env ]; then
    # Safely load environment variables, including those with spaces/special characters
    set -a
    source .env
    set +a
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
echo -e "${BLUE}║   RAG Enterprise - Development Mode         ║${NC}"
echo -e "${BLUE}║   Hot Reload: Backend, Frontend, Ingestion    ║${NC}"
echo -e "${BLUE}║   Services: + Trigger Service                 ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Start infrastructure services first (no dev overrides)
echo -e "${BLUE} Starting infrastructure services...${NC}"
docker compose up -d milvus etcd minio redis ollama
echo -e "${GREEN} Infrastructure services started${NC}"
echo ""

# Step 2: Wait for Ollama container to be running
echo -e "${BLUE} Waiting for Ollama container to be ready...${NC}"
timeout=60
elapsed=0
while ! docker ps --format '{{.Names}}' | grep -q "^${OLLAMA_CONTAINER}$"; do
    if [ $elapsed -ge $timeout ]; then
        echo -e "${RED} Timeout: Ollama container did not start${NC}"
        exit 1
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done
echo -e "${GREEN} Ollama container is running${NC}"
echo ""

# Step 3: Check if model is present, download if missing
echo -e "${BLUE} Ensuring Ollama model '${LLM_MODEL}' is present...${NC}"
docker exec -it ${OLLAMA_CONTAINER} ollama list || true
echo ""

if docker exec ${OLLAMA_CONTAINER} ollama list 2>/dev/null | grep -qi "${LLM_MODEL}"; then
    echo -e "${GREEN} Model '${LLM_MODEL}' is already installed${NC}"
else
    echo -e "${YELLOW}⬇  Model '${LLM_MODEL}' not found. Downloading...${NC}"
    echo -e "${YELLOW}   This may take several minutes depending on model size.${NC}"
    docker exec -it ${OLLAMA_CONTAINER} ollama pull ${LLM_MODEL}
    echo -e "${GREEN} Model '${LLM_MODEL}' downloaded successfully${NC}"
fi
echo ""

# Step 4: Start backend and frontend with dev configuration
echo -e "${BLUE} Starting backend, frontend, ingestion, and trigger with HOT RELOAD...${NC}"
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d backend frontend ingestion
docker compose --profile trigger up -d trigger
echo -e "${GREEN} Development services started${NC}"
echo ""

# Step 5: Wait for backend health
echo -e "${BLUE} Waiting for backend health checks (max 60s)...${NC}"
deadline=$((SECONDS + 60))
health_ok=false

while [ $SECONDS -lt $deadline ]; do
    health_response=$(curl -s "http://localhost:${API_PORT}/health/deps" 2>/dev/null || echo "")
    
    if [ -n "$health_response" ]; then
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
    echo -e "${GREEN} All services are healthy!${NC}"
else
    echo -e "${YELLOW}  Warning: Not all services reported healthy within timeout${NC}"
    echo -e "${YELLOW}   Services may still be initializing. Check logs if issues persist.${NC}"
fi

# Step 6: Verify ingestion and trigger services are running
echo ""
echo -e "${BLUE} Verifying ingestion and trigger services...${NC}"
if docker ps --format '{{.Names}}' | grep -q "rag-ingestion"; then
    echo -e "${GREEN}   Ingestion service: Running${NC}"
else
    echo -e "${YELLOW}   Ingestion service: Not running${NC}"
fi

if docker ps --format '{{.Names}}' | grep -q "rag-trigger"; then
    echo -e "${GREEN}   Trigger service: Running${NC}"
else
    echo -e "${YELLOW}   Trigger service: Not running${NC}"
fi

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        Development Mode Active!           ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN} Access URLs:${NC}"
echo -e "   Frontend:  ${BLUE}http://localhost:3000${NC}"
echo -e "   Backend:   ${BLUE}http://localhost:${API_PORT}${NC}"
echo -e "   API Docs:  ${BLUE}http://localhost:${API_PORT}/docs${NC}"
echo ""
echo -e "${GREEN} Services Running:${NC}"
echo -e "   Backend API:         Hot-reload enabled"
echo -e "   Frontend (React):    Hot-reload enabled"
echo -e "   Ingestion Worker:    Monitoring Redis queue"
echo -e "   Trigger Service:     Watching ${BLUE}./data/incoming/${NC}"
echo ""
echo -e "${GREEN} Hot Reload Enabled:${NC}"
echo -e "   Backend:   Edit files in ${BLUE}./backend/${NC} → Auto-reload"
echo -e "   Frontend:  Edit files in ${BLUE}./frontend/src/${NC} → Auto-reload"
echo -e "   Ingestion: Edit files in ${BLUE}./ingestion/${NC} → Restart container"
echo -e "   Trigger:   Edit files in ${BLUE}./trigger/${NC} → Restart container"
echo ""
echo -e "${GREEN} Test Ingestion:${NC}"
echo -e "   Drop file: ${BLUE}cp myfile.txt ./data/incoming/${NC}"
echo -e "   Or API:    ${BLUE}curl -X POST http://localhost:${API_PORT}/ingest/file ...${NC}"
echo ""
echo -e "${GREEN} Useful Commands:${NC}"
echo -e "   All Logs:  ${BLUE}docker compose logs -f${NC}"
echo -e "   Backend:   ${BLUE}docker compose logs -f backend${NC}"
echo -e "   Ingestion: ${BLUE}docker compose logs -f ingestion${NC}"
echo -e "   Trigger:   ${BLUE}docker compose logs -f trigger${NC}"
echo -e "   Stop All:  ${BLUE}docker compose --profile trigger down${NC}"
echo -e "   Restart:   ${BLUE}docker compose restart backend ingestion trigger${NC}"
echo ""
echo -e "${YELLOW} Tips:${NC}"
echo -e "   - Python changes reload backend automatically"
echo -e "   - React changes rebuild frontend automatically"
echo -e "   - Drop files in ${BLUE}./data/incoming/${NC} for auto-ingestion"
echo -e "   - Check ${BLUE}./data/incoming/processed/${NC} for completed files"
echo ""
