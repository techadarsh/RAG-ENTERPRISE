# RAG Enterprise Performance Optimization - Implementation Plan

## Current Status
- [x] New environment variables added to .env
- [x] New high-performance LLM client created (llm_client_optimized.py → llm_client.py)
-  Main.py needs health-aware fast-fail and degraded mode
-  RAG pipeline needs optimization
-  Streaming endpoint needed
-  Frontend updates needed
-  Benchmark harness needed

## Critical Path (Implement First)

### 1. Health-Aware Fast-Fail in /ask (CRITICAL - Solves "I don't know" issue)
**File**: `backend/main.py`

Add before `/ask` endpoint:
```python
# Global health cache
_health_cache = {"ollama": "unknown", "last_check": 0}
_health_ttl = 3  # seconds

async def get_cached_health() -> Dict[str, str]:
    """Get cached health status with TTL"""
    global _health_cache
    now = time.time()
    
    if now - _health_cache["last_check"] > _health_ttl:
        # Refresh cache
        try:
            health = await health_check_dependencies()
            _health_cache.update(health)
            _health_cache["last_check"] = now
        except:
            pass
    
    return _health_cache
```

Modify `/ask` endpoint:
```python
@app.post("/ask", response_model=QueryResponse)
async def ask_question(request: QueryRequest) -> QueryResponse:
    # HEALTH GATE - Fast-fail if LLM down
    health_gate_enabled = os.getenv("LLM_HEALTH_GATE", "true").lower() == "true"
    
    if health_gate_enabled:
        health = await get_cached_health()
        if health.get("ollama") != "ok":
            logger.warning(f"  LLM unhealthy (ollama={health.get('ollama')}), using degraded mode")
            return await ask_question_degraded(request)
    
    # Check circuit breaker
    if rag_pipeline and rag_pipeline.llm_client:
        if not rag_pipeline.llm_client.is_available():
            logger.warning(f" Circuit breaker OPEN, using degraded mode")
            return await ask_question_degraded(request)
    
    # Normal flow continues...
```

### 2. Degraded Mode Response
**File**: `backend/main.py`

Add new function:
```python
async def ask_question_degraded(request: QueryRequest) -> QueryResponse:
    """
    Degraded mode: Return retrieval-only results when LLM unavailable
    Fast response (<1s) without waiting for LLM timeout
    """
    if not rag_pipeline:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")
    
    start_time = time.perf_counter()
    session_id = request.session_id or str(uuid.uuid4())
    
    try:
        # Do retrieval only (no LLM generation)
        retrieval_results = rag_pipeline.retrieve_only(request.query)
        
        # Build degraded response with excerpts
        snippets = []
        for r in retrieval_results[:3]:  # Top 3
            snippet = {
                "title": r.get("title", "Unknown"),
                "text_excerpt": r.get("text", "")[:500],  # First 500 chars
                "score": f"{r.get('score', 0)*100:.1f}%"
            }
            snippets.append(snippet)
        
        answer = " Model temporarily unavailable. Here are the most relevant excerpts:\n\n"
        for i, s in enumerate(snippets, 1):
            answer += f"{i}. {s['title']} (relevance: {s['score']})\n{s['text_excerpt']}...\n\n"
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        logger.info(f"[x] Degraded mode response ({latency_ms:.0f}ms)")
        
        return QueryResponse(
            answer=answer,
            sources=retrieval_results,
            latency_ms=round(latency_ms, 2),
            session_id=session_id,
            degraded=True  # Add this field to model
        )
        
    except Exception as e:
        logger.error(f"Degraded mode failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### 3. Update QueryResponse Model
**File**: `backend/main.py`

```python
class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    latency_ms: float
    session_id: Optional[str] = None
    degraded: Optional[bool] = False  # ADD THIS
```

### 4. Add retrieve_only Method to RAGPipeline
**File**: `backend/rag_pipeline.py`

```python
def retrieve_only(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Retrieve relevant documents without LLM generation
    Fast degraded mode response
    """
    # Embed query
    query_embedding = self.embedding_model.embed_query(query)
    
    # Search Milvus
    results = self.milvus_client.search(
        collection_name=self.collection_name,
        query_vectors=[query_embedding],
        limit=top_k,
        output_fields=["doc_id", "text", "title", "metadata"]
    )
    
    # Format results
    formatted = []
    for hit in results[0]:
        formatted.append({
            "doc_id": hit.entity.get("doc_id"),
            "text": hit.entity.get("text"),
            "title": hit.entity.get("title", "Unknown"),
            "score": hit.distance,
            "metadata": hit.entity.get("metadata", {})
        })
    
    return formatted
```

### 5. Add Warm-up on Startup
**File**: `backend/main.py`

In `startup_event()`:
```python
@app.on_event("startup")
async def startup_event():
    """Initialize RAG pipeline on startup"""
    global rag_pipeline, redis_conn, ingestion_queue
    
    # ... existing initialization ...
    
    # WARM-UP LLM
    warmup_enabled = os.getenv("LLM_WARMUP_ENABLED", "true").lower() == "true"
    if warmup_enabled and rag_pipeline:
        try:
            from llm_client import LLMClient
            success = LLMClient.warmup()
            if success:
                logger.info(" LLM warm-up completed successfully")
            else:
                logger.warning("  LLM warm-up failed (non-fatal)")
        except Exception as e:
            logger.warning(f"  LLM warm-up error: {e}")
    
    # START KEEP-ALIVE TASK
    keepalive_enabled = os.getenv("LLM_KEEPALIVE_ENABLED", "true").lower() == "true"
    if keepalive_enabled:
        asyncio.create_task(llm_keepalive_task())
```

Add keep-alive task:
```python
async def llm_keepalive_task():
    """Background task to keep LLM model loaded"""
    from llm_client import LLMClient
    
    while True:
        try:
            await asyncio.sleep(180)  # Every 3 minutes
            LLMClient.keepalive_probe()
            logger.debug(" LLM keep-alive probe sent")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Keep-alive probe failed: {e}")
```

## Quick Fixes to Apply Now

### Fix 1: Increase Timeout (Immediate)
**File**: `backend/llm_client.py` (the one we just replaced)

The new client already has adaptive timeouts:
- Initial: 20s (cold start)
- Normal: 5s (warm)

But the current issue shows 40s timeouts are happening. This is likely because the old client is still being used.

### Fix 2: Test New LLM Client
Rebuild backend with new LLM client:
```bash
cd /Users/adarsharma/Documents/adarsharma/M.tech-4th-sem/rag-enterprise
docker compose build backend
docker compose up -d backend
```

### Fix 3: Verify Health Status
```bash
curl http://localhost:8000/health/deps | python3 -m json.tool
```

### Fix 4: Test Query
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query":"What is API documentation?","session_id":"test"}' \
  --max-time 10
```

If this times out in 5-10s instead of 40s, the new client is working!

##  Next Steps (After Critical Fixes)

1. **Add streaming endpoint** (`/ask/stream`) - Medium priority
2. **Add query cache** (LRU with 60s TTL) - Medium priority
3. **Optimize Milvus search params** - Low priority
4. **Add benchmark harness** - Low priority
5. **Update frontend** for degraded mode banner - Low priority

## Expected Improvements

### Before Optimization
-  LLM down → 40s timeout → "I don't know" error
-  First query → 30-40s (cold start)
-  Subsequent queries → 20-30s
-  No connection reuse
-  No circuit breaker

### After Optimization  
- [x] LLM down → <1s response with degraded mode
- [x] First query → 15-20s (warm-up on startup)
- [x] Subsequent queries → 3-8s (connection pooling + warm model)
- [x] Circuit breaker prevents cascading failures
- [x] Health gate provides instant feedback

## Rollback Plan

If issues occur:
```bash
cd backend
cp llm_client_backup.py llm_client.py
docker compose build backend
docker compose up -d backend
```

## Testing Checklist

- [ ] Backend builds without errors
- [ ] Health endpoint shows all services OK
- [ ] Query with LLM UP returns in <10s
- [ ] Query with LLM DOWN returns degraded response in <2s
- [ ] Circuit breaker opens after 3 failures
- [ ] Warm-up runs on startup
- [ ] Connection pool reuses connections
- [ ] No memory leaks after 100 queries

