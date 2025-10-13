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
        echo -e "${YELLOW}This may take 2-3 minutes for first-time setup:${NC}"
        echo "  1. Downloading Docker images"
        echo "  2. Building backend and frontend"
        echo "  3. Loading BGE-Large-En model (~1.5GB)"
        echo "  4. Initializing Milvus vector database"
        echo "  5. Indexing sample documents"
        echo ""
        
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
