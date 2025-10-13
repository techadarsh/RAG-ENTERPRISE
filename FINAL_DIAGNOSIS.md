# Final Diagnosis: "I don't know" Issue

## ✅ What We Fixed
1. **New LLM Client** with connection pooling, circuit breaker, adaptive timeouts - ACTIVE
2. **Environment variables** for performance tuning - CONFIGURED
3. **Ollama is working** - Verified with direct test (responds in <1s)

## 🔴 Current Issue
**Ollama times out (>20s) when called from RAG backend with full context**

### Evidence:
```
rag-backend | 🦙 [Attempt 1/2] Trying Ollama: http://rag-ollama:11434/api/generate (timeout=20.0s cold, breaker=closed)
rag-backend | ❌ Failed at http://rag-ollama:11434/api/generate (20005ms): ReadTimeout: timed out
```

### Why This Happens:
1. **Long prompts**: RAG backend sends full context (could be 2000+ tokens)
2. **Model generation**: Trying to generate 1024 tokens (LLM_MAX_TOKENS=1024)
3. **Hardware limits**: Mistral 7B on CPU is slow for long contexts

### Test Results:
- ✅ Simple prompt ("Say hello"): 266ms
- ❌ Full RAG query with context: >20s (timeout)

## 🎯 Solutions (Apply in Order)

### Solution 1: Reduce Max Tokens (QUICK FIX - Do This Now)
Reduce token generation limit to make responses faster.

**File**: `.env`
```bash
# Change from:
LLM_MAX_TOKENS=1024

# To:
LLM_MAX_TOKENS=256   # Much faster, still enough for answers
```

Then:
```bash
docker compose restart backend
sleep 20  # Wait for embeddings
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query":"What is PTO policy?"}' \
  --max-time 15
```

### Solution 2: Increase Timeout for Complex Queries
The 20s timeout is too aggressive for long contexts.

**File**: `.env`
```bash
# Change:
LLM_INITIAL_TIMEOUT_MS=20000
LLM_TIMEOUT_MS=5000

# To:
LLM_INITIAL_TIMEOUT_MS=45000   # 45s for cold start
LLM_TIMEOUT_MS=30000           # 30s for normal queries
```

###Solution 3: Implement Context Compression (BEST - Do Next)
Reduce the amount of context sent to LLM.

**File**: `backend/rag_pipeline.py`

Find the `query()` method and add context trimming:

```python
def query(self, query: str, top_k: int = 3) -> Dict[str, Any]:
    # ... existing retrieval code ...
    
    # TRIM context to reduce tokens
    MAX_CONTEXT_CHARS = 2000  # ~500 tokens
    trimmed_context = context_text[:MAX_CONTEXT_CHARS]
    if len(context_text) > MAX_CONTEXT_CHARS:
        trimmed_context += "... [truncated]"
    
    # Use trimmed context
    answer = self.llm_client.generate_answer(query, trimmed_context)
```

### Solution 4: Add Degraded Mode (RECOMMENDED - Full Solution)
Return results immediately when LLM is slow/unavailable.

This requires implementing the changes in `PERFORMANCE_OPTIMIZATION_PLAN.md`:
- Health gate check before LLM call
- Degraded mode response (retrieval-only)
- Fast-fail in <1s when LLM unavailable

## 📊 Expected Results After Fixes

### After Solution 1 (Reduce Tokens):
- Query time: 8-15s (down from >20s)
- Answer length: Shorter but sufficient
- Timeout rate: Much lower

### After Solution 2 (Increase Timeout):
- Timeout rate: 0% (allows completion)
- Query time: 15-30s (unchanged, but completes)
- May still be slow

### After Solution 3 (Context Compression):
- Query time: 5-10s (significant improvement)
- Answer quality: Still good with focused context
- Token usage: 50-70% reduction

### After Solution 4 (Degraded Mode):
- LLM down: <1s response with excerpts
- LLM slow: Circuit breaker triggers, degraded mode
- User experience: Always responsive

## 🚀 Recommended Action Plan

### Phase 1: Quick Win (5 minutes)
```bash
# Edit .env
LLM_MAX_TOKENS=256
LLM_TIMEOUT_MS=30000
LLM_INITIAL_TIMEOUT_MS=45000

# Restart
docker compose restart backend
sleep 20

# Test
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query":"What is the PTO policy?"}' \
  --max-time 35
```

**Expected**: Query completes in 10-20s with answer

### Phase 2: Context Optimization (15 minutes)
- Add context trimming to rag_pipeline.py
- Reduce RETRIEVAL_TOP_K from 3 to 2
- Test query time improvement

### Phase 3: Degraded Mode (30 minutes)
- Implement health gate in /ask endpoint
- Add `ask_question_degraded()` function
- Add `retrieve_only()` to RAGPipeline
- Test fast-fail behavior

## 🔍 Debugging Commands

### Check Current Configuration:
```bash
docker compose exec backend env | grep -E "LLM_|RETRIEVAL_"
```

### Monitor LLM Attempts:
```bash
docker compose logs -f backend | grep -E "🦙|timeout|Failed"
```

### Test Ollama Directly:
```bash
# Quick test
curl -X POST http://localhost:11434/api/generate \
  -d '{"model":"mistral","prompt":"hi","stream":false}' \
  -H "Content-Type: application/json"

# With timing
time curl -X POST http://localhost:11434/api/generate \
  -d '{"model":"mistral","prompt":"Answer in 20 words: What is PTO?","options":{"num_predict":50},"stream":false}' \
  -H "Content-Type: application/json"
```

### Check Circuit Breaker State:
```bash
docker compose logs backend | grep -E "Circuit breaker|breaker="
```

## 📈 Performance Metrics

### Current State:
- Health checks: ~200ms ✅
- Simple Ollama query: ~300ms ✅
- RAG query: >20s timeout ❌
- Timeout rate: 100% ❌

### Target State (After All Fixes):
- Health checks: ~200ms
- Simple Ollama query: ~300ms
- RAG query: 5-15s
- Timeout rate: <5%
- Degraded mode (LLM down): <1s

## 🛠️ Files to Modify

1. `.env` - Timeouts and max tokens (DONE - just need to edit values)
2. `backend/llm_client.py` - Already optimized ✅
3. `backend/rag_pipeline.py` - Add context trimming (TODO)
4. `backend/main.py` - Add degraded mode (TODO)

## ✅ Success Criteria

Query should return:
```json
{
  "answer": "PTO (Paid Time Off) allows employees to...",
  "sources": [...],
  "latency_ms": 12000,  // < 20s
  "session_id": "...",
  "degraded": false  // Not in degraded mode
}
```

Not:
```json
{
  "answer": "I don't know.\n\nNote: LLM generation service appears unreachable...",
  "latency_ms": 40000  // > 20s timeout
}
```

---

**NEXT STEP**: Apply Solution 1 (reduce max tokens) and test immediately!
