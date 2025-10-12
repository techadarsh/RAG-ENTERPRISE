#!/bin/bash

echo "Setting up Ollama with Mistral model..."
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Step 1: Starting Ollama container...${NC}"
docker compose up -d ollama

echo ""
echo -e "${YELLOW}Step 2: Waiting for Ollama to be ready (30 seconds)...${NC}"
sleep 30

echo ""
echo -e "${YELLOW}Step 3: Pulling Mistral model (this may take 5-10 minutes, ~4GB download)...${NC}"
docker compose exec ollama ollama pull mistral

echo ""
echo -e "${GREEN}✅ Ollama setup complete!${NC}"
echo ""
echo "Now starting the full application..."
docker compose up -d

echo ""
echo -e "${GREEN}🎉 All done! Your RAG chatbot is now using Ollama with real AI!${NC}"
echo ""
echo "Access your application at:"
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000/docs"
echo ""
echo "To check Ollama logs:"
echo "  docker compose logs ollama"
echo ""
echo "To check backend logs for 🦙 emoji:"
echo "  docker compose logs backend | grep -E '🦙|ollama'"
