#!/bin/bash

# RAG Enterprise Chatbot - Startup Script
# This script provides a convenient way to start and manage the application

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ╗${NC}"
echo -e "${BLUE}║      RAG Enterprise Chatbot Launcher      ║${NC}"
echo -e "${BLUE}╚ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ╝${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED} Error: Docker is not running${NC}"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

echo -e "${GREEN}${NC} Docker is running"

# Check if docker compose is available
if ! docker compose version > /dev/null 2>&1; then
    echo -e "${RED} Error: docker compose not found${NC}"
    echo "Please install Docker Compose"
    exit 1
fi

echo -e "${GREEN}${NC} Docker Compose is available"
echo ""

# Parse command line arguments
COMMAND=${1:-up}

case $COMMAND in
    up|start)
        echo -e "${BLUE} Starting RAG Chatbot services...${NC}"
        echo ""
        echo -e "${YELLOW}This may take 5-8 minutes for first-time setup:${NC}"
        echo "  1. Downloading Docker images"
        echo "  2. Downloading Mistral LLM model (~4.4GB)"
        echo "  3. Building backend and frontend"
        echo "  4. Loading BGE-Large-En embedding model (~1.5GB)"
        echo "  5. Initializing Milvus vector database"
        echo "  6. Indexing sample documents"
        echo ""
        
        # Step 1: Start Ollama service first to download the model
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BLUE} Step 1: Starting Ollama service...     ${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        docker compose up -d ollama
        
        # Step 2: Wait for Ollama to be ready
        echo ""
        echo -e "${BLUE} Step 2: Waiting for Ollama to be ready...${NC}"
        MAX_RETRIES=30
        RETRY_COUNT=0
        
        while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
            if docker compose exec -T ollama ollama list >/dev/null 2>&1; then
                echo -e "${GREEN}${NC} Ollama is ready!"
                break
            fi
            RETRY_COUNT=$((RETRY_COUNT + 1))
            echo "  Attempt $RETRY_COUNT/$MAX_RETRIES - waiting for Ollama..."
            sleep 2
        done
        
        if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
            echo -e "${RED} Error: Ollama failed to start${NC}"
            exit 1
        fi
        
        # Step 3: Check if Mistral model is already downloaded
        echo ""
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BLUE} Step 3: Checking for Mistral model...${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        
        if docker compose exec -T ollama ollama list | grep -q "mistral"; then
            echo -e "${GREEN}${NC} Mistral model already downloaded"
        else
            echo -e "${YELLOW} Mistral model not found. Downloading now...${NC}"
            echo -e "${YELLOW} This will download ~4.4GB and may take 5-15 minutes${NC}"
            echo ""
            
            if docker compose exec -T ollama ollama pull mistral; then
                echo ""
                echo -e "${GREEN}${NC} Successfully downloaded Mistral model (4.4GB)"
            else
                echo ""
                echo -e "${RED} Error: Failed to download Mistral model${NC}"
                echo -e "${YELLOW} You can try again later or download manually with:${NC}"
                echo -e "${YELLOW}   docker compose exec ollama ollama pull mistral${NC}"
                exit 1
            fi
        fi
        
        # Step 4: Start all remaining services
        echo ""
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BLUE} Step 4: Starting all services...${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        docker compose up --build
        ;;
    
    down|stop)
        echo -e "${BLUE} Stopping RAG Chatbot services...${NC}"
        docker compose down
        echo -e "${GREEN}${NC} Services stopped"
        ;;
    
    restart)
        echo -e "${BLUE} Restarting RAG Chatbot services...${NC}"
        docker compose down
        docker compose up --build
        ;;
    
    logs)
        SERVICE=${2:-}
        if [ -z "$SERVICE" ]; then
            docker compose logs -f
        else
            docker compose logs -f "$SERVICE"
        fi
        ;;
    
    clean)
        echo -e "${YELLOW}  Warning: This will remove all containers, volumes, and data${NC}"
        read -p "Are you sure? (yes/no): " -r
        if [[ $REPLY =~ ^[Yy]es$ ]]; then
            echo -e "${BLUE} Cleaning up...${NC}"
            docker compose down -v
            echo -e "${GREEN}${NC} Cleanup complete"
        else
            echo "Cancelled"
        fi
        ;;
    
    status)
        echo -e "${BLUE} Service Status:${NC}"
        docker compose ps
        echo ""
        echo -e "${BLUE} Access URLs:${NC}"
        echo "  Frontend:  http://localhost:3000"
        echo "  Backend:   http://localhost:8000"
        echo "  API Docs:  http://localhost:8000/docs"
        echo "  Milvus:    localhost:19530"
        ;;
    
    help|--help|-h)
        echo "Usage: ./start.sh [command]"
        echo ""
        echo "Commands:"
        echo "  up, start      Start all services (default)"
        echo "  down, stop     Stop all services"
        echo "  restart        Restart all services"
        echo "  logs [service] View logs (optional: specific service)"
        echo "  clean          Remove all containers and volumes"
        echo "  status         Show service status and URLs"
        echo "  help           Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./start.sh                    # Start services"
        echo "  ./start.sh logs backend       # View backend logs"
        echo "  ./start.sh down               # Stop services"
        ;;
    
    *)
        echo -e "${RED} Unknown command: $COMMAND${NC}"
        echo "Run './start.sh help' for usage information"
        exit 1
        ;;
esac
