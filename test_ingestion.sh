#!/bin/bash
# Test script for the ingestion pipeline

set -e  # Exit on error

echo " Testing RAG Ingestion Pipeline"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Create a test document
echo -e "${BLUE}Step 1: Creating test document${NC}"
cat > /tmp/test_ingestion.txt << 'EOF'
# Test Document for RAG Ingestion Pipeline

This is a comprehensive test document to validate the asynchronous ingestion pipeline.

## System Overview

The RAG Enterprise System uses a microservice architecture with the following components:

1. FastAPI Backend - Handles API requests and publishes ingestion jobs
2. Redis Queue - Manages asynchronous job processing
3. Ingestion Workers - Process documents in the background
4. Milvus Vector Database - Stores document embeddings
5. React Frontend - User interface for queries and uploads

## Key Features

### Asynchronous Processing
Documents are processed in the background without blocking the main API. This ensures:
- Fast response times for upload requests
- Scalable processing with multiple workers
- Fault tolerance with job retry mechanisms
- Status tracking for all ingestion jobs

### Document Chunking
Large documents are automatically split into manageable chunks:
- Default chunk size: 3000 characters
- Overlap between chunks: 500 characters
- Smart splitting at sentence boundaries
- Preserves context across chunks

### Embedding Generation
Each chunk is converted to a 768-dimensional vector using BAAI/bge-base-en:
- State-of-the-art semantic embeddings
- Optimized for English text
- Fast inference on CPU and GPU
- Compatible with ARM64 architecture

## Technical Stack

- Python 3.10
- FastAPI 0.110.2
- Redis 7.0 (Alpine)
- RQ (Redis Queue) 1.15.1
- Milvus 2.3.3
- Sentence Transformers 2.2.2

## Testing Checklist

- [x] Document upload via API
- [x] Job queuing in Redis
- [x] Worker processing
- [x] Embedding generation
- [x] Milvus insertion
- [x] Status tracking
- [x] Query retrieval

This document should be successfully ingested and queryable after processing.
EOF

echo -e "${GREEN} Test document created${NC}"
echo ""

# Step 2: Check if services are running
echo -e "${BLUE}Step 2: Checking if services are running${NC}"

if ! docker ps | grep -q rag-backend; then
    echo -e "${YELLOW}  Backend not running. Start with: docker compose up -d${NC}"
    exit 1
fi

if ! docker ps | grep -q rag-redis; then
    echo -e "${YELLOW}  Redis not running. Start with: docker compose up -d${NC}"
    exit 1
fi

if ! docker ps | grep -q rag-ingestion; then
    echo -e "${YELLOW}  Ingestion worker not running. Start with: docker compose up -d${NC}"
    exit 1
fi

echo -e "${GREEN} All services running${NC}"
echo ""

# Step 3: Upload the document
echo -e "${BLUE}Step 3: Uploading document${NC}"

RESPONSE=$(curl -s -X POST http://localhost:8000/api/ingest/upload \
  -F "file=@/tmp/test_ingestion.txt")

echo "Response: $RESPONSE"

# Extract job ID
JOB_ID=$(echo "$RESPONSE" | grep -o '"job_id":"[^"]*' | cut -d'"' -f4)

if [ -z "$JOB_ID" ]; then
    echo -e "${YELLOW}  Failed to extract job ID${NC}"
    echo "Response: $RESPONSE"
    exit 1
fi

echo -e "${GREEN} Document uploaded, Job ID: $JOB_ID${NC}"
echo ""

# Step 4: Poll for completion
echo -e "${BLUE}Step 4: Waiting for processing to complete${NC}"

MAX_ATTEMPTS=60  # 5 minutes maximum
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    STATUS_RESPONSE=$(curl -s http://localhost:8000/api/ingest/status/$JOB_ID)
    STATUS=$(echo "$STATUS_RESPONSE" | grep -o '"status":"[^"]*' | cut -d'"' -f4)
    
    echo -n "."
    
    if [ "$STATUS" = "completed" ]; then
        echo ""
        echo -e "${GREEN} Processing completed!${NC}"
        echo ""
        echo "Result:"
        echo "$STATUS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$STATUS_RESPONSE"
        break
    elif [ "$STATUS" = "failed" ]; then
        echo ""
        echo -e "${YELLOW}  Processing failed${NC}"
        echo "$STATUS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$STATUS_RESPONSE"
        exit 1
    fi
    
    sleep 5
    ATTEMPT=$((ATTEMPT + 1))
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo ""
    echo -e "${YELLOW}  Timeout waiting for job completion${NC}"
    exit 1
fi

echo ""

# Step 5: Query the ingested document
echo -e "${BLUE}Step 5: Querying the ingested document${NC}"

QUERY_RESPONSE=$(curl -s -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key features of the RAG system described in the test document?",
    "session_id": "test-ingestion"
  }')

echo "Query Result:"
echo "$QUERY_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$QUERY_RESPONSE"
echo ""

# Step 6: Check if answer contains expected content
if echo "$QUERY_RESPONSE" | grep -qi "asynchronous\|processing\|workers\|redis\|milvus"; then
    echo -e "${GREEN} Query successful - answer contains expected content${NC}"
else
    echo -e "${YELLOW}  Answer may not be accurate${NC}"
fi

echo ""
echo -e "${GREEN}=================================="
echo -e " Ingestion pipeline test complete!${NC}"
echo -e "==================================${NC}"
echo ""

# Cleanup
rm -f /tmp/test_ingestion.txt

# Print worker logs
echo -e "${BLUE}Worker logs (last 20 lines):${NC}"
docker compose logs --tail 20 ingestion

echo ""
echo -e "${BLUE}Redis queue status:${NC}"
docker exec rag-redis redis-cli LLEN rq:queue:ingestion || echo "Could not check queue"
