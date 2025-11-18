#!/bin/bash

# RAG Enterprise Chatbot - Local Mac Startup Script
# Automatically checks, installs, and starts all required services on Mac
# Usage: ./start_local.sh [start|stop|status|clean]

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  RAG Enterprise - Local Mac Launcher       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Function to check and install Homebrew
check_homebrew() {
    echo -e "${BLUE}[1/8] Checking Homebrew...${NC}"
    if ! command -v brew &> /dev/null; then
        echo -e "${YELLOW}⚠️  Homebrew not found. Installing...${NC}"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        echo -e "${GREEN}✅ Homebrew installed${NC}"
    else
        echo -e "${GREEN}✅ Homebrew found: $(brew --version | head -n1)${NC}"
    fi
}

# Function to check and install Python 3.11
check_python() {
    echo -e "${BLUE}[2/8] Checking Python 3.11...${NC}"
    if ! command -v python3.11 &> /dev/null; then
        echo -e "${YELLOW}⚠️  Python 3.11 not found. Installing...${NC}"
        brew install python@3.11
        echo -e "${GREEN}✅ Python 3.11 installed${NC}"
    else
        echo -e "${GREEN}✅ Python 3.11 found: $(python3.11 --version)${NC}"
    fi
    
    # Check/create virtual environment
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}⚠️  Virtual environment not found. Creating...${NC}"
        python3.11 -m venv venv
        echo -e "${GREEN}✅ Virtual environment created${NC}"
    fi
    
    # Activate venv and install dependencies
    source venv/bin/activate
    echo -e "${BLUE}   Installing Python dependencies...${NC}"
    pip install --upgrade pip > /dev/null 2>&1
    
    if [ -f "backend/requirements.txt" ]; then
        pip install -r backend/requirements.txt > /dev/null 2>&1
        echo -e "${GREEN}✅ Python dependencies installed${NC}"
    fi
}

# Function to check and install Node.js
check_node() {
    echo -e "${BLUE}[3/8] Checking Node.js...${NC}"
    if ! command -v node &> /dev/null; then
        echo -e "${YELLOW}⚠️  Node.js not found. Installing...${NC}"
        brew install node
        echo -e "${GREEN}✅ Node.js installed${NC}"
    else
        echo -e "${GREEN}✅ Node.js found: $(node --version)${NC}"
    fi
    
    # Install frontend dependencies
    if [ ! -d "frontend/node_modules" ]; then
        echo -e "${BLUE}   Installing frontend dependencies...${NC}"
        cd frontend
        npm install > /dev/null 2>&1
        cd ..
        echo -e "${GREEN}✅ Frontend dependencies installed${NC}"
    fi
}

# Function to check and install Ollama
check_ollama() {
    echo -e "${BLUE}[4/8] Checking Ollama...${NC}"
    if ! command -v ollama &> /dev/null; then
        echo -e "${YELLOW}⚠️  Ollama not found. Installing...${NC}"
        brew install ollama
        echo -e "${GREEN}✅ Ollama installed${NC}"
    else
        echo -e "${GREEN}✅ Ollama found${NC}"
    fi
}

# Function to check and install Redis
check_redis() {
    echo -e "${BLUE}[5/8] Checking Redis...${NC}"
    if ! command -v redis-server &> /dev/null; then
        echo -e "${YELLOW}⚠️  Redis not found. Installing...${NC}"
        brew install redis
        echo -e "${GREEN}✅ Redis installed${NC}"
    else
        echo -e "${GREEN}✅ Redis found: $(redis-server --version | head -n1)${NC}"
    fi
}

# Function to check Docker (for Milvus)
check_docker() {
    echo -e "${BLUE}[6/8] Checking Docker...${NC}"
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker not found!${NC}"
        echo -e "${YELLOW}   Please install Docker Desktop from: https://www.docker.com/products/docker-desktop${NC}"
        exit 1
    fi
    
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}❌ Docker is not running!${NC}"
        echo -e "${YELLOW}   Please start Docker Desktop and try again${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Docker found and running${NC}"
}

# Function to create required directories
create_directories() {
    echo -e "${BLUE}[7/8] Creating required directories...${NC}"
    mkdir -p data/uploads
    mkdir -p data/sample_confluence_pages
    mkdir -p data/incoming
    mkdir -p ~/milvus-data
    echo -e "${GREEN}✅ Directories created${NC}"
}

# Function to create .env.local
create_env_local() {
    echo -e "${BLUE}[8/8] Setting up local environment...${NC}"
    
    if [ ! -f ".env.local" ]; then
        cat > .env.local << 'EOF'
# Local Development Configuration - Mac M4 Pro

# LLM Configuration (Local Ollama)
LLM_MODE=api
LLM_HOST=localhost
LLM_PORT=11434
LLM_MODEL=mistral
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=1024
LLM_TIMEOUT_WARM=60000
LLM_TIMEOUT_COLD=90000

# Milvus Configuration (Docker)
MILVUS_HOST=localhost
MILVUS_PORT=19530
COLLECTION_NAME=enterprise_docs

# Redis Configuration (Local)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Embedding Model
EMBEDDING_MODEL=BAAI/bge-base-en
EMBEDDING_DIM=768

# Document Processing
CHUNK_SIZE=512
CHUNK_OVERLAP=50
RETRIEVAL_TOP_K=5
MAX_CONTEXT_CHARS=2000

# Confluence Configuration
CONFLUENCE_MODE=api                                      # local or api 
CONFLUENCE_LOCAL_DIR=data/sample_confluence_pages

# Confluence API Configuration (for API mode)
# To use Confluence Cloud API instead of local files, set CONFLUENCE_MODE=api
# Get your API token from: https://id.atlassian.com/manage-profile/security/api-tokens
CONFLUENCE_BASE_URL=https://wilp-team-cemu4tnf.atlassian.net/wiki
CONFLUENCE_USER_EMAIL=2023mt03610@wilp.bits-pilani.ac.in
CONFLUENCE_API_TOKEN=ATATT3xFfGF0UUStV1nHxREnhPFL88CM7ff7p35kfE2IJP9S7NiyCqDp3chhxI4sW-Z8h4SAdYaPd1Bp5b6SOIjew2ENeb1DVP_dMjMFvZCKKO1FHAHeUI6bT8Rc3KvxHQnicrru3rrRqZhZVC6ktbL_RRUH1sz_eThmycopRaQ144GFAw5Vat0=69C56591
CONFLUENCE_SPACE_KEY=BITSWILP

# Confluence Auto-Sync (polls Confluence for changes)
CONFLUENCE_AUTO_SYNC=true                               # Enable automatic sync
CONFLUENCE_SYNC_INTERVAL=300                            # Check every 300 seconds (5 minutes)

# Confluence Webhook (for real-time updates from Confluence)
export CONFLUENCE_WEBHOOK_SECRET="test-secret-key-12345"

# Data Directories
DATA_DIR=./data
UPLOAD_DIR=./data/uploads

FORCE_INITIAL_LOAD=false

# Etcd/Minio Configuration (Milvus standalone uses embedded versions)
ETCD_USE_EMBED=true
COMMON_STORAGETYPE=local
ETCD_HOST=localhost
ETCD_PORT=2379
MINIO_HOST=localhost
MINIO_PORT=9000

# Local/Standalone Mode Flags
MILVUS_STANDALONE=true
SKIP_ETCD_CHECK=true
SKIP_MINIO_CHECK=true

# Mistral Legacy Config
MISTRAL_API_URL=http://localhost:11434/api/generate
MISTRAL_MODEL=mistral

# All other settings from main .env
LLM_INITIAL_TIMEOUT_MS=60000
LLM_TIMEOUT_MS=45000
LLM_DYNAMIC_TIMEOUT=true
LLM_HEALTH_GATE=false
LLM_BREAKER_ENABLED=true
LLM_BREAKER_FAILS=3
LLM_BREAKER_COOLDOWN_S=90
LLM_WARMUP_ENABLED=true
LLM_KEEPALIVE_ENABLED=true
ASK_STREAMING_ENABLED=false
RETRIEVAL_MIN_SCORE=0.0
RETRIEVAL_NPROBE=8
RETRIEVAL_CACHE_SIZE=32
RETRIEVAL_CACHE_TTL_S=60
MAX_CHUNK_CHARS=800
HTTPX_POOL_LIMIT=20
EMBED_BATCH=32
MILVUS_COLLECTION=enterprise_docs
EMBEDDINGS_HOST=localhost
EMBEDDINGS_PORT=8000
API_HOST=0.0.0.0
API_PORT=8000
ENABLE_FOLDER_WATCHER=false

EOF
        echo -e "${GREEN}✅ .env.local created${NC}"
    else
        echo -e "${GREEN}✅ .env.local already exists${NC}"
    fi
    
    # Create frontend .env.local
    if [ ! -f "frontend/.env.local" ]; then
        echo "REACT_APP_API_URL=http://localhost:8000" > frontend/.env.local
        echo -e "${GREEN}✅ frontend/.env.local created${NC}"
    fi
}

# Function to create backend/run_local.py
create_run_local() {
    if [ ! -f "backend/run_local.py" ]; then
        cat > backend/run_local.py << 'EOF'
#!/usr/bin/env python3
"""
Local development server for Mac
Runs without Docker, using local services
"""
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Load local environment
from dotenv import load_dotenv
load_dotenv('.env.local')

# Create required directories
DATA_DIR = os.getenv("DATA_DIR", "./data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
CONFLUENCE_DIR = os.path.join(DATA_DIR, "sample_confluence_pages")

Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(CONFLUENCE_DIR).mkdir(parents=True, exist_ok=True)

import uvicorn

if __name__ == "__main__":
    print("🚀 Starting RAG Enterprise Backend (Local Mode)")
    print(f"📍 Ollama: http://localhost:11434")
    print(f"📍 Milvus: http://localhost:19530")
    print(f"📍 Redis: http://localhost:6379")
    print(f"📍 Backend: http://localhost:8000")
    print(f"📍 API Docs: http://localhost:8000/docs")
    print("")
    
    # Import app after environment is loaded
    from main import app
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
EOF
        chmod +x backend/run_local.py
    fi
}

# Function to start Ollama service
start_ollama() {
    echo -e "${BLUE}Starting Ollama service...${NC}"
    
    # Check if Ollama is already running
    if pgrep -x "ollama" > /dev/null; then
        echo -e "${GREEN}✅ Ollama already running${NC}"
    else
        # Start Ollama in background
        ollama serve > /tmp/ollama.log 2>&1 &
        sleep 3
        
        if pgrep -x "ollama" > /dev/null; then
            echo -e "${GREEN}✅ Ollama started${NC}"
        else
            echo -e "${RED}❌ Failed to start Ollama${NC}"
            exit 1
        fi
    fi
    
    # Check if Mistral model exists
    echo -e "${BLUE}Checking Mistral model...${NC}"
    if ollama list | grep -q "mistral"; then
        echo -e "${GREEN}✅ Mistral model ready${NC}"
    else
        echo -e "${YELLOW}⚠️  Downloading Mistral model (4.4GB)...${NC}"
        echo -e "${YELLOW}   This may take 5-15 minutes...${NC}"
        ollama pull mistral
        echo -e "${GREEN}✅ Mistral model downloaded${NC}"
    fi
}

# Function to start Redis
start_redis() {
    echo -e "${BLUE}Starting Redis...${NC}"
    
    # Check if Redis is already running
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Redis already running${NC}"
    else
        # Start Redis as a service
        brew services start redis > /dev/null 2>&1
        sleep 2
        
        if redis-cli ping > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Redis started${NC}"
        else
            echo -e "${RED}❌ Failed to start Redis${NC}"
            exit 1
        fi
    fi
}

# Function to start Milvus
start_milvus() {
    echo -e "${BLUE}Starting Milvus...${NC}"
    
    # Check if Milvus container exists
    if docker ps -a | grep -q milvus-standalone; then
        # Container exists, check if running
        if docker ps | grep -q milvus-standalone; then
            echo -e "${GREEN}✅ Milvus already running${NC}"
        else
            # Start existing container
            docker start milvus-standalone > /dev/null 2>&1
            echo -e "${GREEN}✅ Milvus started${NC}"
        fi
    else
        # Create and start new container
        docker run -d \
          --name milvus-standalone \
          -p 19530:19530 \
          -p 9091:9091 \
          -v ~/milvus-data:/var/lib/milvus \
          -e ETCD_USE_EMBED=true \
          -e COMMON_STORAGETYPE=local \
          milvusdb/milvus:v2.3.3 \
          milvus run standalone > /dev/null 2>&1
        
        echo -e "${GREEN}✅ Milvus started${NC}"
    fi
    
    # Wait for Milvus to be ready
    echo -e "${BLUE}   Waiting for Milvus to be ready...${NC}"
    for i in {1..30}; do
        if curl -s http://localhost:9091/healthz > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Milvus is ready${NC}"
            break
        fi
        sleep 2
    done
}

# Function to start backend
start_backend() {
    echo -e "${BLUE}Starting Backend...${NC}"
    
    source venv/bin/activate
    cd backend
    python run_local.py > /tmp/rag-backend.log 2>&1 &
    BACKEND_PID=$!
    cd ..
    
    # Save PID for later
    echo $BACKEND_PID > /tmp/rag-backend.pid
    
    echo -e "${GREEN}✅ Backend started (PID: $BACKEND_PID)${NC}"
    echo -e "${BLUE}   Backend is initializing (loading Confluence documents)...${NC}"
    echo -e "${BLUE}   With FORCE_INITIAL_LOAD=true, this may take 2-3 minutes.${NC}"
    echo -e "${BLUE}   💡 Tip: Set FORCE_INITIAL_LOAD=false in .env.local for instant startup${NC}"
    echo -e "${BLUE}   Monitor progress: tail -f /tmp/rag-backend.log${NC}"
    
    # Wait for backend to be ready 
    echo -e "${BLUE}   Waiting for backend health endpoint...${NC}"
    for i in {1..90}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Backend is ready at http://localhost:8000${NC}"
            return 0
        fi
        sleep 2
    done
    
    echo -e "${YELLOW}⚠️  Backend health check timed out (still initializing)${NC}"
    echo -e "${YELLOW}   Check logs: tail -f /tmp/rag-backend.log${NC}"
    echo -e "${YELLOW}   The backend may still become ready in a few moments${NC}"
}

# Function to start frontend
start_frontend() {
    echo -e "${BLUE}Starting Frontend...${NC}"
    
    cd frontend
    
    # Create a simple start script that fixes the localStorage issue
    cat > start_local.sh << 'FRONTEND_SCRIPT'
#!/bin/bash
export PORT=3000
export BROWSER=none
export SKIP_PREFLIGHT_CHECK=true
export NODE_OPTIONS="--localstorage-file=/tmp/node-localstorage"
npm start
FRONTEND_SCRIPT
    
    chmod +x start_local.sh
    
    # Start frontend with proper environment
    ./start_local.sh > /tmp/rag-frontend.log 2>&1 &
    FRONTEND_PID=$!
    cd ..
    
    # Save PID for later
    echo $FRONTEND_PID > /tmp/rag-frontend.pid
    
    echo -e "${GREEN}✅ Frontend started (PID: $FRONTEND_PID)${NC}"
    echo -e "${BLUE}   Waiting for frontend to compile (this may take 30-60 seconds)...${NC}"
    
    # Wait for frontend to be ready
    for i in {1..60}; do
        if curl -s http://localhost:3000 > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Frontend is ready at http://localhost:3000${NC}"
            return 0
        fi
        sleep 2
    done
    
    echo -e "${YELLOW}⚠️  Frontend may still be compiling. Check logs: tail -f /tmp/rag-frontend.log${NC}"
}

# Function to load Confluence documents into Milvus
load_confluence_documents() {
    echo -e "${BLUE}Loading Confluence documents into Milvus...${NC}"
    echo -e "${BLUE}   Documents will be loaded from Confluence API${NC}"
    echo -e "${BLUE}   Waiting for backend to be fully ready...${NC}"
    
    # Wait up to 2 minutes for backend to complete initialization
    BACKEND_READY=false
    for i in {1..60}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            BACKEND_READY=true
            echo -e "${GREEN}✅ Backend is ready${NC}"
            break
        fi
        sleep 2
    done
    
    if [ "$BACKEND_READY" = false ]; then
        echo -e "${YELLOW}⚠️  Backend not ready yet. Documents were auto-loaded during startup.${NC}"
        echo -e "${YELLOW}   The backend loads sample documents automatically on initialization.${NC}"
        echo -e "${YELLOW}   Check: tail -f /tmp/rag-backend.log${NC}"
        return 0
    fi
    
    # Call the ingestion endpoint
    echo -e "${BLUE}   Checking document ingestion status via API...${NC}"
    RESPONSE=$(curl -s -X POST http://localhost:8000/ingest/confluence \
        -H "Content-Type: application/json" \
        -d '{"mode": "api"}' 2>&1)
    
    # Check response for success indicators
    if echo "$RESPONSE" | grep -q "success\|ingested\|loaded\|pages"; then
        echo -e "${GREEN}✅ Documents confirmed in Milvus${NC}"
        echo -e "${GREEN}   $(echo "$RESPONSE" | head -c 200)${NC}"
    else
        echo -e "${YELLOW}⚠️  Documents may already be loaded${NC}"
        echo -e "${YELLOW}   $(echo "$RESPONSE" | head -c 200)${NC}"
    fi
}

# Function to stop backend only
stop_backend() {
    echo -e "${BLUE}Stopping backend...${NC}"
    
    if [ -f /tmp/rag-backend.pid ]; then
        BACKEND_PID=$(cat /tmp/rag-backend.pid)
        kill -9 $BACKEND_PID 2>/dev/null || true
        rm /tmp/rag-backend.pid
    fi
    
    pkill -9 -f "uvicorn.*main:app" 2>/dev/null || true
    pkill -9 -f "python.*uvicorn.*backend" 2>/dev/null || true
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    
    echo -e "${GREEN}✅ Backend stopped${NC}"
}

# Function to stop frontend only
stop_frontend() {
    echo -e "${BLUE}Stopping frontend...${NC}"
    
    if [ -f /tmp/rag-frontend.pid ]; then
        FRONTEND_PID=$(cat /tmp/rag-frontend.pid)
        kill -9 $FRONTEND_PID 2>/dev/null || true
        rm /tmp/rag-frontend.pid
    fi
    
    pkill -9 -f "react-scripts.*start" 2>/dev/null || true
    pkill -9 -f "node.*frontend" 2>/dev/null || true
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    
    echo -e "${GREEN}✅ Frontend stopped${NC}"
}

# Function to stop Ollama only
stop_ollama() {
    echo -e "${BLUE}Stopping Ollama...${NC}"
    pkill -x ollama 2>/dev/null || true
    echo -e "${GREEN}✅ Ollama stopped${NC}"
}

# Function to stop Redis only
stop_redis() {
    echo -e "${BLUE}Stopping Redis...${NC}"
    brew services stop redis > /dev/null 2>&1
    echo -e "${GREEN}✅ Redis stopped${NC}"
}

# Function to stop Milvus only
stop_milvus() {
    echo -e "${BLUE}Stopping Milvus...${NC}"
    docker stop milvus-standalone > /dev/null 2>&1 || true
    echo -e "${GREEN}✅ Milvus stopped${NC}"
}

# Function to start backend only
start_backend() {
    echo -e "${BLUE}Starting Backend...${NC}"
    
    # Source environment
    if [ -f .env.local ]; then
        set -a
        source .env.local
        set +a
    fi
    
    # Start backend
    cd "$PROJECT_DIR/backend"
    PYTHONPATH="$PROJECT_DIR/backend" nohup "$PROJECT_DIR/venv/bin/python3" -m uvicorn main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --log-level info > /tmp/rag-backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > /tmp/rag-backend.pid
    cd "$PROJECT_DIR"
    
    echo -e "${GREEN}✅ Backend started (PID: $BACKEND_PID)${NC}"
    
    # Wait for backend to be ready
    echo -e "${BLUE}   Waiting for backend health endpoint...${NC}"
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Backend is ready at http://localhost:8000${NC}"
            return 0
        fi
        sleep 2
    done
    
    echo -e "${RED}❌ Backend failed to start (timeout)${NC}"
    echo -e "${YELLOW}   Check logs: tail -f /tmp/rag-backend.log${NC}"
    return 1
}

# Function to start frontend only
start_frontend() {
    echo -e "${BLUE}Starting Frontend...${NC}"
    
    cd "$PROJECT_DIR/frontend"
    nohup npm start > /tmp/rag-frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > /tmp/rag-frontend.pid
    cd "$PROJECT_DIR"
    
    echo -e "${GREEN}✅ Frontend started (PID: $FRONTEND_PID)${NC}"
    echo -e "${BLUE}   Waiting for frontend to compile (this may take 30-60 seconds)...${NC}"
    
    for i in {1..60}; do
        if curl -s http://localhost:3000 > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Frontend is ready at http://localhost:3000${NC}"
            return 0
        fi
        sleep 2
    done
    
    echo -e "${RED}❌ Frontend failed to start (timeout)${NC}"
    echo -e "${YELLOW}   Check logs: tail -f /tmp/rag-frontend.log${NC}"
    return 1
}

# Function to start Ollama only
start_ollama() {
    echo -e "${BLUE}Starting Ollama service...${NC}"
    
    if ! pgrep -x "ollama" > /dev/null; then
        nohup ollama serve > /tmp/ollama.log 2>&1 &
        sleep 3
        echo -e "${GREEN}✅ Ollama started${NC}"
    else
        echo -e "${YELLOW}⚠️  Ollama already running${NC}"
    fi
    
    # Check if mistral model is available
    echo -e "${BLUE}Checking Mistral model...${NC}"
    if ollama list | grep -q "mistral"; then
        echo -e "${GREEN}✅ Mistral model ready${NC}"
    else
        echo -e "${YELLOW}⚠️  Mistral model not found. Pulling (this may take a few minutes)...${NC}"
        ollama pull mistral
        echo -e "${GREEN}✅ Mistral model ready${NC}"
    fi
}

# Function to start Redis only
start_redis() {
    echo -e "${BLUE}Starting Redis...${NC}"
    
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Redis already running${NC}"
    else
        brew services start redis > /dev/null 2>&1
        sleep 2
        if redis-cli ping > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Redis started${NC}"
        else
            echo -e "${RED}❌ Redis failed to start${NC}"
            return 1
        fi
    fi
}

# Function to start Milvus only
start_milvus() {
    echo -e "${BLUE}Starting Milvus...${NC}"
    
    # Check if Milvus is already running
    if docker ps | grep -q milvus-standalone; then
        echo -e "${YELLOW}⚠️  Milvus already running${NC}"
    else
        # Check if container exists but is stopped
        if docker ps -a | grep -q milvus-standalone; then
            docker start milvus-standalone > /dev/null
        else
            # Create new container
            mkdir -p ~/milvus-data
            docker run -d \
                --name milvus-standalone \
                -p 19530:19530 \
                -p 9091:9091 \
                -v ~/milvus-data:/var/lib/milvus \
                milvusdb/milvus:latest > /dev/null
        fi
        
        echo -e "${GREEN}✅ Milvus started${NC}"
        
        # Wait for Milvus to be ready
        echo -e "${BLUE}   Waiting for Milvus to be ready...${NC}"
        for i in {1..30}; do
            if curl -s http://localhost:9091/healthz > /dev/null 2>&1; then
                echo -e "${GREEN}✅ Milvus is ready${NC}"
                return 0
            fi
            sleep 2
        done
        
        echo -e "${RED}❌ Milvus failed to start (timeout)${NC}"
        return 1
    fi
}

# Function to restart a specific service
restart_service() {
    SERVICE=$1
    
    case $SERVICE in
        backend)
            stop_backend
            sleep 1
            start_backend
            ;;
        frontend)
            stop_frontend
            sleep 1
            start_frontend
            ;;
        ollama)
            stop_ollama
            sleep 1
            start_ollama
            ;;
        redis)
            stop_redis
            sleep 1
            start_redis
            ;;
        milvus)
            stop_milvus
            sleep 2
            start_milvus
            ;;
        *)
            echo -e "${RED}❌ Unknown service: $SERVICE${NC}"
            echo "Available services: backend, frontend, ollama, redis, milvus"
            return 1
            ;;
    esac
}

# Function to stop all services
stop_services() {
    echo -e "${BLUE}Stopping all services...${NC}"
    
    # Stop backend (use PID file first, then force kill any remaining)
    if [ -f /tmp/rag-backend.pid ]; then
        BACKEND_PID=$(cat /tmp/rag-backend.pid)
        kill -9 $BACKEND_PID 2>/dev/null || true
        rm /tmp/rag-backend.pid
    fi
    
    # Force kill any remaining backend processes
    pkill -9 -f "uvicorn.*main:app" 2>/dev/null || true
    pkill -9 -f "python.*uvicorn.*backend" 2>/dev/null || true
    
    # Kill any process using port 8000
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    
    echo -e "${GREEN}✅ Backend stopped${NC}"
    
    # Stop frontend (use PID file first, then force kill any remaining)
    if [ -f /tmp/rag-frontend.pid ]; then
        FRONTEND_PID=$(cat /tmp/rag-frontend.pid)
        kill -9 $FRONTEND_PID 2>/dev/null || true
        rm /tmp/rag-frontend.pid
    fi
    
    # Force kill any remaining frontend processes
    pkill -9 -f "react-scripts.*start" 2>/dev/null || true
    pkill -9 -f "node.*frontend" 2>/dev/null || true
    
    # Kill any process using port 3000
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    
    echo -e "${GREEN}✅ Frontend stopped${NC}"
    
    # Stop Ollama
    pkill -x ollama 2>/dev/null || true
    echo -e "${GREEN}✅ Ollama stopped${NC}"
    
    # Stop Redis
    brew services stop redis > /dev/null 2>&1
    echo -e "${GREEN}✅ Redis stopped${NC}"
    
    # Stop Milvus
    docker stop milvus-standalone > /dev/null 2>&1 || true
    echo -e "${GREEN}✅ Milvus stopped${NC}"
}

# Function to show status
show_status() {
    echo -e "${BLUE}Service Status:${NC}"
    echo ""
    
    # Ollama
    if pgrep -x "ollama" > /dev/null; then
        echo -e "${GREEN}✅ Ollama: Running${NC}"
    else
        echo -e "${RED}❌ Ollama: Stopped${NC}"
    fi
    
    # Redis
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Redis: Running${NC}"
    else
        echo -e "${RED}❌ Redis: Stopped${NC}"
    fi
    
    # Milvus
    if docker ps | grep -q milvus-standalone; then
        echo -e "${GREEN}✅ Milvus: Running${NC}"
    else
        echo -e "${RED}❌ Milvus: Stopped${NC}"
    fi
    
    # Backend
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend: Running (http://localhost:8000)${NC}"
    else
        echo -e "${RED}❌ Backend: Stopped${NC}"
    fi
    
    # Frontend
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Frontend: Running (http://localhost:3000)${NC}"
    else
        echo -e "${RED}❌ Frontend: Stopped${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}Access URLs:${NC}"
    echo "  Frontend:  http://localhost:3000"
    echo "  Backend:   http://localhost:8000"
    echo "  API Docs:  http://localhost:8000/docs"
}

# Function to clean everything
clean_all() {
    echo -e "${YELLOW}⚠️  Warning: This will remove all data and containers${NC}"
    read -p "Are you sure? (yes/no): " -r
    if [[ $REPLY =~ ^[Yy]es$ ]]; then
        stop_services
        
        # Remove Milvus container and data
        docker rm -f milvus-standalone 2>/dev/null || true
        rm -rf ~/milvus-data
        
        # Remove Redis data
        rm -rf /usr/local/var/db/redis
        
        # Remove logs
        rm -f /tmp/rag-*.log /tmp/rag-*.pid /tmp/ollama.log
        
        echo -e "${GREEN}✅ Cleanup complete${NC}"
    else
        echo "Cancelled"
    fi
}

# Main command handler
COMMAND=${1:-start}

case $COMMAND in
    start)
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BLUE}  STEP 1: Checking Prerequisites${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        check_homebrew
        check_python
        check_node
        check_ollama
        check_redis
        check_docker
        create_directories
        create_env_local
        create_run_local
        
        echo ""
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BLUE}  STEP 2: Starting Services${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        start_ollama
        start_redis
        start_milvus
        start_backend
        start_frontend
        
        echo ""
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BLUE}  STEP 3: Loading Confluence Documents${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        load_confluence_documents
        
        echo ""
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}  ✅ All services started successfully!${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "${BLUE}📍 Access URLs:${NC}"
        echo "   Frontend:  http://localhost:3000"
        echo "   Backend:   http://localhost:8000"
        echo "   API Docs:  http://localhost:8000/docs"
        echo ""
        echo -e "${YELLOW}📝 Logs:${NC}"
        echo "   Backend:  tail -f /tmp/rag-backend.log"
        echo "   Frontend: tail -f /tmp/rag-frontend.log"
        echo "   Ollama:   tail -f /tmp/ollama.log"
        echo ""
        echo -e "${BLUE}🛑 To stop: ./start_local.sh stop${NC}"
        ;;
    
    stop)
        stop_services
        echo -e "${GREEN}✅ All services stopped${NC}"
        ;;
    
    status)
        show_status
        ;;
    
    restart)
        SERVICE=${2:-all}
        if [ "$SERVICE" = "all" ]; then
            stop_services
            sleep 2
            $0 start
        else
            restart_service "$SERVICE"
        fi
        ;;
    
    clean)
        clean_all
        ;;
    
    logs)
        SERVICE=${2:-backend}
        if [ "$SERVICE" = "backend" ]; then
            tail -f /tmp/rag-backend.log
        elif [ "$SERVICE" = "frontend" ]; then
            tail -f /tmp/rag-frontend.log
        elif [ "$SERVICE" = "ollama" ]; then
            tail -f /tmp/ollama.log
        else
            echo "Unknown service. Use: backend, frontend, or ollama"
        fi
        ;;
    
    help|--help|-h)
        echo "Usage: ./start_local.sh [command] [options]"
        echo ""
        echo "Commands:"
        echo "  start              Check prerequisites, install if needed, and start all services"
        echo "  stop               Stop all services"
        echo "  restart [service]  Restart all services or a specific service"
        echo "                     Services: backend, frontend, ollama, redis, milvus"
        echo "  status             Show service status"
        echo "  logs [service]     View logs (backend|frontend|ollama)"
        echo "  clean              Remove all data and containers"
        echo "  help               Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./start_local.sh start                  # Start everything"
        echo "  ./start_local.sh restart                # Restart everything"
        echo "  ./start_local.sh restart backend        # Restart only backend"
        echo "  ./start_local.sh restart frontend       # Restart only frontend"
        echo "  ./start_local.sh status                 # Check status"
        echo "  ./start_local.sh logs backend           # View backend logs"
        echo "  ./start_local.sh stop                   # Stop everything"
        ;;
    
    *)
        echo -e "${RED}❌ Unknown command: $COMMAND${NC}"
        echo "Run './start_local.sh help' for usage information"
        exit 1
        ;;
esac
