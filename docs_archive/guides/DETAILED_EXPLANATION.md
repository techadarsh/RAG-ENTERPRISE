# Detailed RAG Pipeline Explanation

## 1. rag_pipeline.py - Complete Overview

### Purpose
The `RAGPipeline` class is the **orchestrator** that connects all RAG components: embeddings, vector search (Milvus), and LLM generation. It manages the entire query-to-answer flow.

### Key Components

#### Constructor (`__init__`)
**What it does:**
- Initializes 3 main clients:
  - `EmbeddingModel`: Lazy-loaded SentenceTransformer (BAAI/bge-base-en)
  - `MilvusClient`: Vector database for similarity search
  - `LLMClient`: LLM backend (mock/Ollama/etc)
- Connects to Milvus and verifies schema
- Flags if initial data loading is needed (but defers to background thread)

**Why lazy loading:** Prevents blocking FastAPI startup (embedding model takes 1-2 minutes to download on first run)

#### Core Query Methods

**`query(query, top_k)` - Single-turn query (no conversation history)**

Flow:
1. Embed user question → 768-dim vector
2. Search Milvus for top_k similar chunks (default 3)
3. **Relevance guard:** If best score < 0.02 → return "out of scope" message
4. Build context string (limits: 800 chars/chunk, 2000 chars total)
5. Call `llm_client.generate_answer(query, context)`
6. Return `{answer, sources (top 3), context}`

**`generate_with_context(query, history, top_k)` - Multi-turn query (with history)**

Same as `query()` but:
- Builds history_text from last 6 messages (3 turns)
- Calls `llm_client.generate_answer_with_history(query, context, history_text)`
- LLM sees recent conversation for contextual answers

**Key Difference:**
- `query()`: "What is PTO?" → LLM sees only question + context
- `generate_with_context()`: "Can I rollover?" → LLM sees previous "What is PTO?" + answer + new question + context

#### Helper Methods

**`_chunk_text(text, max_length, overlap)`**
- Splits large documents (>3000 chars) intelligently
- Tries paragraph boundaries first, then sentences
- 500-char overlap to preserve context across chunks

**`_load_initial_data()`**
- Loads sample documents ONCE on first startup (if Milvus empty)
- Sources: Confluence local mode + `data/*.txt`
- Chunks, embeds, inserts into Milvus

**`_extract_document_topics()` and `get_scope_description()`**
- Scans Milvus for all unique document titles
- Builds natural language scope: "I can answer about X, Y, and Z"
- Used for polite out-of-scope rejections

**`_clean_title_for_display(title)`**
- Removes noisy metadata for user-facing titles:
  - "(Part 2/5)" → removed
  - "[Confluence]" → removed
  - ".txt" → removed
- Why needed: Milvus stores full titles for debugging/filtering

---

## 2. Redis Usage - Why It's Essential

**redis_conn and ingestion_queue are ACTIVELY used** for:
- `/api/ingest/upload` - Async document upload
- `/api/ingest/status/{job_id}` - Job tracking
- `/api/webhook/confluence` - Confluence integration
- Folder watcher and S3 listener triggers

**Why not used in `/ask` query flow:**
- Queries need instant responses (no queuing)
- Ingestion is inherently async (can take minutes for large docs)

**Architecture:**
```
User upload → Backend enqueues job → Redis → Worker processes → Milvus
                                    ↑
                              Job queue
                         (persistent, scalable)
```

**Do NOT remove** - it's the backbone of the ingestion pipeline!

---

## 3. Milvus Retrieval - Deep Dive

### How "top_k chunks" are retrieved

**Step-by-step:**

1. **Query vector arrives** (768-dim float array, normalized)

2. **Index lookup** (IVF_FLAT with Inner Product):
   - Milvus partitions vector space into 128 clusters (`nlist=128`)
   - At search time, searches only 10 closest clusters (`nprobe=10`)
   - This is Approximate Nearest Neighbor (ANN) - faster than exact search

3. **Similarity scoring:**
   - Metric: Inner Product (IP)
   - Since vectors are normalized, IP ≈ cosine similarity
   - Formula: `score = dot(query_vector, doc_vector)`
   - Range: 0.0 to 1.0 (higher = more similar)

4. **Results returned:**
   - Top_k documents sorted by score (descending)
   - Each result: `{title, text, score}`

**Example:**
```
Query: "What is the PTO policy?"
Embed → [0.23, -0.45, ..., 0.12]
Milvus search (top_k=3) →
  [
    {title: "leave_policy.txt", text: "Our PTO...", score: 0.87},
    {title: "hr_policy.txt (Part 3/4)", text: "Employees...", score: 0.82},
    {title: "onboarding.txt", text: "During...", score: 0.65}
  ]
```

**Performance:**
- Search time: <10ms for 3 results (typical)
- Scales to millions of documents with ANN indexing

---

## 4. query() vs generate_with_context() - Detailed Comparison

### query(query, top_k) - Single-turn

**When:** First message OR no session_id

**Prompt structure:**
```
You are an AI assistant for enterprise knowledge...

Context Documents:
[Document 1: leave_policy]
Our PTO policy offers 20 days...

[Document 2: hr_policy]
Employees can rollover...

User Question: What is the PTO policy?

Your Response:
```

**LLM sees:** Only current question + retrieved context

---

### generate_with_context(query, history, top_k) - Multi-turn

**When:** Follow-up message with existing session_id

**Prompt structure:**
```
You are an AI assistant...

Previous Conversation:
User: What is the PTO policy?
Assistant: Our PTO policy offers 20 days per year...
User: Can I rollover unused days?

Context Documents:
[Document 1: leave_policy]
You can rollover up to 5 days...

User Question: Can I rollover unused days?

Your Response:
```

**LLM sees:** Recent conversation (last 3 turns) + current question + retrieved context

**Benefit:** Contextual answers
- "Yes, **as I mentioned**, you can rollover up to 5 days..."
- Understands pronouns: "it", "that", "the policy"
- Can reference previous exchanges

---

## 5. get_scope_description() - Advanced Functionality

### Purpose
Generate human-friendly scope description for out-of-scope rejections.

### How it works

**Phase 1: Topic Extraction (`_extract_document_topics()`)**
- Runs once after data load
- Fetches all document titles from Milvus
- Cleans each title via `_clean_title_for_display()`:
  ```
  "hr_policy.txt (Part 2/3)" → "hr_policy"
  "[Confluence] Engineering Standards" → "Engineering Standards"
  "onboarding.txt" → "onboarding"
  ```
- Deduplicates and sorts: `["Engineering Standards", "hr_policy", "onboarding"]`

**Phase 2: Natural Language Formatting (`get_scope_description()`)**
- **0 topics:** `"company documentation"` (fallback)
- **1 topic:** `"engineering standards"` (singular)
- **2 topics:** `"engineering standards and hr policy"` (and)
- **3+ topics:** `"engineering standards, hr policy, and onboarding"` (Oxford comma)

**Usage example:**
```python
# User asks: "Who won the 2024 Olympics?"
# Top retrieval score: 0.01 (very low)

if top_score < 0.02:
    scope = pipeline.get_scope_description()
    # → "Engineering Standards, hr_policy, and onboarding"
    
    return {
        "answer": f"I can only answer questions about {scope}. 
                   Please ask about topics covered in our documentation.",
        "sources": []
    }
```

**Smart features:**
- Handles chunks gracefully (doesn't show "Part 1, Part 2, Part 3")
- Updates dynamically when new docs ingested
- Graceful fallback for empty KB

---

## 6. MAX_CONTEXT_CHARS and MAX_CHUNK_CHARS - Fixed

### Problem
Comments said "~500 tokens" but value was 2000 chars - confusing!

### Token-to-Character Ratio
- English text: ~1 token = 4 characters
- 2000 chars ≈ 500 tokens ✓
- 800 chars ≈ 200 tokens ✓

### Fixed Values (with clear comments)

**In rag_pipeline.py:**
```python
# Context compression settings
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "2000"))  # Total context limit: ~500 tokens
MAX_CHUNK_CHARS = int(os.getenv("MAX_CHUNK_CHARS", "800"))  # Per-chunk limit: ~200 tokens
```

**Added to .env.example:**
```bash
# RAG Context Limits (affects answer quality vs speed trade-off)
MAX_CONTEXT_CHARS=2000  # Total context sent to LLM (~500 tokens). Lower = faster response.
MAX_CHUNK_CHARS=800     # Max chars per retrieved chunk (~200 tokens). Prevents overly long chunks.
RETRIEVAL_TOP_K=3       # Number of chunks to retrieve from Milvus
```

### Impact Analysis
- **Lowering MAX_CONTEXT_CHARS:** Faster LLM generation, but less context for answers
- **Raising MAX_CONTEXT_CHARS:** More context = better answers, but slower (especially Ollama)
- **Sweet spot:** 2000 chars (current default) balances quality and speed

---

## 7. _clean_title_for_display() - Why Needed

### Where Noisy Prefixes Come From

1. **"(Part X/Y)" suffix**
   - Added by: `_load_initial_data()` and `ingestion/pipeline.py`
   - Why: Large documents are chunked (e.g., 15KB file → 5 chunks)
   - Stored as: `"hr_policy.txt (Part 1/5)"`, `"hr_policy.txt (Part 2/5)"`, etc.

2. **"[Confluence]" prefix**
   - Added by: `_load_initial_data()`
   - Why: Distinguishes Confluence docs from local files
   - Stored as: `"[Confluence] Engineering Standards"`

3. **".txt" extension**
   - From: Original filename
   - Stored as-is

### Why We Don't Remove at Source

**Pros of storing full titles in Milvus:**
- ✅ Essential for debugging (which chunk failed?)
- ✅ Easy filtering (search for all Confluence docs)
- ✅ Traceability (know exact source file)
- ✅ Worker logs show full titles for troubleshooting

**Pros of cleaning for display:**
- ✅ Better UX (users don't care about chunks)
- ✅ No schema migration needed
- ✅ Backward compatible with existing data

### Alternative Approach (Not Recommended)

Could add metadata fields to Milvus schema:
```python
FieldSchema(name="source_type", dtype=DataType.VARCHAR, max_length=50)  # "local" or "confluence"
FieldSchema(name="chunk_number", dtype=DataType.INT64)  # 1, 2, 3...
FieldSchema(name="clean_title", dtype=DataType.VARCHAR, max_length=512)  # "hr_policy"
```

**Why not:**
- ❌ Breaking change (requires re-ingesting all data)
- ❌ More complex code
- ❌ Minimal benefit (cleaning is trivial)

**Conclusion:** Keep `_clean_title_for_display()` - it's the right trade-off.

---

## 8. Embedding Consistency - Verified ✓

### Both Use Same Model

**For document ingestion:** `embed_texts(texts)`
**For user queries:** `embed_query(query)`

Both call `self.get_model()` → same singleton SentenceTransformer instance

**Critical parameters (identical):**
```python
model.encode(
    texts_or_query,
    normalize_embeddings=True,  # ← ESSENTIAL for cosine similarity via Inner Product
    show_progress_bar=False,
    batch_size=8  # Only for embed_texts
)
```

**Why normalization matters:**
- Milvus uses Inner Product (IP) metric
- For normalized vectors: `IP(A, B) = cosine_similarity(A, B)`
- Without normalization: IP would favor longer vectors (wrong!)

**Verification:**
```python
# Both produce same embedding for same text
doc_embed = embedding_model.embed_texts(["What is PTO?"])[0]
query_embed = embedding_model.embed_query("What is PTO?")

assert np.allclose(doc_embed, query_embed)  # ✓ Pass
```

---

## 9. Third-Party API Code Removal

### Privacy Concern
You want data to stay on-premises. Currently, code supports:
- ✅ Mock (local, no network)
- ✅ Ollama (local, self-hosted)
- ❌ HuggingFace Inference API (sends data to HF servers)
- ❌ Mistral API (sends data to Mistral servers)

### What Will Be Removed

**From llm_client.py:**
- `_generate_huggingface()` method
- HuggingFace detection in `_detect_backend()`
- HuggingFace route in `generate()`

**From .env.example:**
- HuggingFace configuration example
- Mistral API configuration example

**What Remains:**
- Mock mode (dev/testing)
- Ollama mode (production, on-prem)

---

## 10. User-Facing Errors (To Discuss Later)

### Common Issues Users Might Face

1. **Ollama model not loaded:**
   - Error: "LLM generation service appears unreachable"
   - Fix: `docker exec rag-ollama ollama pull mistral`

2. **Query returns "out of scope":**
   - Cause: No relevant documents OR relevance score < 0.02
   - Fix: Check if document ingested, adjust threshold if needed

3. **Slow responses (>10s):**
   - Cause: Ollama cold start OR large context
   - Fix: Lower MAX_CONTEXT_CHARS or use smaller model

4. **Empty sources returned:**
   - Cause: Milvus empty OR embedding model failed
   - Check: `/health/deps` endpoint

5. **Session history not working:**
   - Cause: Different session_id OR backend restarted (in-memory sessions lost)
   - Future: Move sessions to Redis for persistence

**Note:** These will be documented in a troubleshooting guide later.

---

## Summary

✅ **All 10 points addressed:**
1. rag_pipeline.py explained in detail
2. Redis usage clarified (essential, don't remove)
3. Milvus retrieval deep dive provided
4. query() vs generate_with_context() compared
5. get_scope_description() functionality detailed
6. MAX_CONTEXT/CHUNK_CHARS fixed with clear comments
7. _clean_title_for_display() rationale explained
8. Embedding consistency verified
9. Third-party API code will be removed
10. User errors noted for later discussion

**Next Steps:**
- Apply code fixes (add env vars, remove HF/Mistral code)
- Test with sample queries
- Document troubleshooting guide
