"""
FastAPI backend for RAG chatbot with lazy-loaded embeddings
"""
import logging
import time
import os
import threading
import uuid
import shutil
import hmac
import hashlib
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from rag_pipeline import RAGPipeline
from confluence_ingest import ConfluenceIngestor
from embeddings import EmbeddingModel
from llm_client import LLMClient
import asyncio
import json

# Setup logging BEFORE any logger usage
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Redis and RQ imports for job queue
try:
    from redis import Redis
    from rq import Queue
    from rq.job import Job
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("  Redis/RQ not available - ingestion API will be disabled")

# Load environment variables - check for .env.local first (for local development)
import os
from pathlib import Path
env_local_path = Path(__file__).parent.parent / '.env.local'
if env_local_path.exists():
    load_dotenv(env_local_path, override=True)
    logger.info(f" Loaded local environment from {env_local_path}")
else:
    load_dotenv(override=False)

# Health check cache (TTL: 10 seconds)
_health_cache = {"data": None, "timestamp": 0}
_health_cache_lock = threading.Lock()
HEALTH_CACHE_TTL = 10  # seconds

# Initialize FastAPI app
app = FastAPI(
    title="RAG Chatbot API",
    description="Retrieval-Augmented Generation chatbot for enterprise knowledge management",
    version="1.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    sources: list
    latency_ms: float
    session_id: str

class IngestionJobResponse(BaseModel):
    job_id: str
    status: str
    message: str
    file_path: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ConfluenceWebhookPayload(BaseModel):
    """Confluence webhook event payload"""
    event: str  # e.g., 'page_created', 'page_updated'
    page: Dict[str, Any]  # Contains page id, title, url, space, etc.

class WebhookResponse(BaseModel):
    status: str
    message: str
    job_id: Optional[str] = None

# Global RAG pipeline instance
rag_pipeline = None

# In-memory chat session storage
# Format: {session_id: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
chat_sessions: Dict[str, List[Dict[str, str]]] = {}

# Redis connection and queue (if available)
redis_conn = None
ingestion_queue = None

# Confluence sync state
confluence_sync_task = None
confluence_last_versions: Dict[str, int] = {}  # page_id -> version number

# Upload directory - support both Docker and local paths
DATA_DIR = os.getenv("DATA_DIR", "./data")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(DATA_DIR, "uploads"))

# Create upload directory if it doesn't exist
try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    logger.info(f" Upload directory: {UPLOAD_DIR}")
except Exception as e:
    logger.warning(f"⚠️  Could not create upload directory {UPLOAD_DIR}: {e}")
    UPLOAD_DIR = "./uploads"  # Fallback
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def validate_atlassian_webhook_signature(request_body: bytes, signature: str, secret: str) -> bool:
    """
    Validate Atlassian webhook signature using HMAC-SHA256.
    
    Args:
        request_body: Raw request body bytes
        signature: X-Atlassian-Webhook-Signature header value
        secret: Webhook secret from environment
    
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature or not secret:
        return False
    
    try:
        # Compute HMAC-SHA256
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            request_body,
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures (constant-time comparison to prevent timing attacks)
        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error(f"❌ Signature validation error: {e}")
        return False


def warmup_embeddings():
    """
    Warm up embedding model and load data in background after FastAPI starts
    This prevents blocking the startup event
    """
    try:
        logger.info(" Background warm-up started ...")
        
        # Load embedding model first
        model = EmbeddingModel.get_model()
        # Warm up with a test encoding
        _ = model.encode(["warmup"], normalize_embeddings=True, show_progress_bar=False)
        logger.info(" Embedding model loaded in background and ready for use")
        
        # Now load data if needed
        if rag_pipeline and hasattr(rag_pipeline, 'load_data_if_needed'):
            rag_pipeline.load_data_if_needed()
            
    except Exception as e:
        logger.error(f"  Warm-up failed: {e}")


@app.on_event("startup")
async def startup_event():
    """Initialize RAG pipeline on startup (non-blocking for embeddings)"""
    global rag_pipeline, redis_conn, ingestion_queue
    
    logger.info("Starting up RAG chatbot backend")
    
    # Initialize Redis connection for ingestion queue
    if REDIS_AVAILABLE:
        try:
            redis_host = os.getenv("REDIS_HOST", "redis")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            redis_db = int(os.getenv("REDIS_DB", "0"))
            
            redis_conn = Redis(host=redis_host, port=redis_port, db=redis_db)
            redis_conn.ping()  # Test connection
            
            ingestion_queue = Queue('ingestion', connection=redis_conn)
            logger.info(f" Connected to Redis at {redis_host}:{redis_port}")
            logger.info(f" Ingestion queue size: {len(ingestion_queue)}")
        except Exception as e:
            logger.warning(f"  Redis connection failed: {e}")
            logger.warning("  Ingestion API will be disabled")
            redis_conn = None
            ingestion_queue = None
    
    # Load Confluence documents (if enabled)
    confluence_mode = os.getenv("CONFLUENCE_MODE", "local")
    logger.info(f"Confluence integration mode: {confluence_mode}")
    
    confluence_docs = []
    if confluence_mode in ["local", "api"]:
        try:
            confluence_ingestor = ConfluenceIngestor()
            confluence_docs = confluence_ingestor.get_documents()
            logger.info(f" Ingested {len(confluence_docs)} Confluence pages (mode: {confluence_mode})")
        except Exception as e:
            logger.warning(f"Failed to load Confluence documents: {e}")
            logger.warning("Continuing without Confluence integration")
    
    try:
        rag_pipeline = RAGPipeline(
            milvus_host=os.getenv("MILVUS_HOST", "milvus"),
            milvus_port=int(os.getenv("MILVUS_PORT", "19530")),
            collection_name=os.getenv("COLLECTION_NAME", "enterprise_docs"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "BAAI/bge-base-en"),
            embedding_dim=int(os.getenv("EMBEDDING_DIM", "768")),
            llm_mode=os.getenv("LLM_MODE", "mock"),
            mistral_api_key=os.getenv("MISTRAL_API_KEY"),
            mistral_api_url=os.getenv("MISTRAL_API_URL"),
            data_dir=os.getenv("DATA_DIR", "/app/data"),
            confluence_docs=confluence_docs  # Pass Confluence docs to RAG pipeline
        )
        logger.info("RAG pipeline initialized successfully")
        
        # Start background warmup thread (non-blocking)
        # Now safe with ARM64-compatible PyTorch + fallback logic
        threading.Thread(target=warmup_embeddings, daemon=True).start()
        logger.info(" FastAPI started without blocking - background loading initiated")
        
        # Optional: Force blocking initial load of sample documents on startup
        # Useful when you want the backend to finish indexing before accepting traffic.
        try:
            force_load = os.getenv("FORCE_INITIAL_LOAD", "false").lower() in ["1", "true", "yes"]
            if force_load and rag_pipeline and hasattr(rag_pipeline, 'load_data_if_needed'):
                logger.info("FORCE_INITIAL_LOAD=true -> performing blocking initial data load...")
                rag_pipeline.load_data_if_needed()
                logger.info("Blocking initial data load complete")
        except Exception as e:
            logger.warning(f"FORCE_INITIAL_LOAD failed: {e}")
        
    except Exception as e:
        logger.error(f"Failed to initialize RAG pipeline: {e}")
        raise
    
    # Start automatic Confluence sync if enabled
    global confluence_sync_task
    sync_enabled = os.getenv("CONFLUENCE_AUTO_SYNC", "false").lower() in ["1", "true", "yes"]
    if sync_enabled and confluence_mode == "api":
        sync_interval = int(os.getenv("CONFLUENCE_SYNC_INTERVAL", "300"))  # Default: 5 minutes
        logger.info(f"🔄 Starting automatic Confluence sync (interval: {sync_interval}s)")
        confluence_sync_task = asyncio.create_task(auto_sync_confluence(sync_interval))
    else:
        logger.info("ℹ️  Automatic Confluence sync disabled (set CONFLUENCE_AUTO_SYNC=true to enable)")


async def auto_sync_confluence(interval_seconds: int = 300):
    """
    Automatically poll Confluence for changes and sync updated documents
    
    This function runs in the background and periodically:
    1. Fetches all pages from Confluence
    2. Compares version numbers with last known versions
    3. Updates only changed pages in Milvus
    4. Detects and removes deleted pages from Milvus
    
    Args:
        interval_seconds: How often to check for changes (default: 300 = 5 minutes)
    """
    global confluence_last_versions
    
    logger.info(f"🔄 Confluence auto-sync started (checking every {interval_seconds}s)")
    
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            
            logger.info("🔍 Checking Confluence for updates...")
            
            # Fetch all pages from Confluence
            from confluence_ingest import ConfluenceIngestor
            ingestor = ConfluenceIngestor(mode='api')
            pages = ingestor.get_documents()
            
            if not pages:
                logger.warning("⚠️  No pages fetched from Confluence")
                continue
            
            # Track changes
            new_count = 0
            updated_count = 0
            unchanged_count = 0
            deleted_count = 0
            
            # Get current page IDs from Confluence
            current_page_ids = {page.get("id") for page in pages}
            
            # Check for deleted pages (in our cache but not in Confluence anymore)
            deleted_page_ids = set(confluence_last_versions.keys()) - current_page_ids
            
            for deleted_page_id in deleted_page_ids:
                logger.info(f"   🗑️  Deleted page detected: ID {deleted_page_id}")
                success = rag_pipeline.delete_single_document(deleted_page_id)
                if success:
                    del confluence_last_versions[deleted_page_id]
                    deleted_count += 1
                    logger.info(f"   ✅ Removed from RAG system")
            
            # Process existing/new/updated pages
            for page in pages:
                page_id = page.get("id")
                page_title = page.get("title", "Untitled")
                page_version = page.get("version", 1)
                
                # Check if this is a new or updated page
                if page_id not in confluence_last_versions:
                    # New page - add it
                    logger.info(f"   📄 New page detected: {page_title} (ID: {page_id})")
                    success = rag_pipeline.update_single_document(page_id, page)
                    if success:
                        confluence_last_versions[page_id] = page_version
                        new_count += 1
                elif confluence_last_versions[page_id] < page_version:
                    # Page updated - sync it
                    old_version = confluence_last_versions[page_id]
                    logger.info(f"   🔄 Updated page detected: {page_title} (ID: {page_id}, v{old_version} → v{page_version})")
                    success = rag_pipeline.update_single_document(page_id, page)
                    if success:
                        confluence_last_versions[page_id] = page_version
                        updated_count += 1
                else:
                    # No changes
                    unchanged_count += 1
            
            # Summary
            if new_count > 0 or updated_count > 0 or deleted_count > 0:
                logger.info(f"✅ Sync complete: {new_count} new, {updated_count} updated, {deleted_count} deleted, {unchanged_count} unchanged")
            else:
                logger.info(f"✅ No changes detected ({unchanged_count} pages up-to-date)")
                
        except Exception as e:
            logger.error(f"❌ Error during Confluence auto-sync: {e}", exc_info=True)
            # Continue running despite errors


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Basic health check endpoint"""
    return {"status": "ok"}


@app.get("/health/deps")
async def health_check_dependencies() -> Dict[str, Any]:
    """
    Comprehensive dependency health check for all critical services with caching.
    Returns ok/fail status for: Milvus, Etcd, Minio, Redis, Ollama, Embeddings, Backend
    
    Cached for 10 seconds to reduce load (health badge polls every 15s).
    """
    # Check cache first
    with _health_cache_lock:
        if _health_cache["data"] and time.time() - _health_cache["timestamp"] < HEALTH_CACHE_TTL:
            return _health_cache["data"]
    
    # Cache miss - perform health checks
    results = {
        "backend": "ok",
        "milvus": "fail",
        "etcd": "fail",
        "minio": "fail",
        "redis": "fail",
        "ollama": "fail",
        "embeddings": "fail"
    }
    
    # Check Milvus
    try:
        from pymilvus import connections
        milvus_host = os.getenv("MILVUS_HOST", "milvus")
        milvus_port = int(os.getenv("MILVUS_PORT", "19530"))
        connections.connect(
            alias="health_check",
            host=milvus_host,
            port=milvus_port,
            timeout=2
        )
        results["milvus"] = "ok"
        connections.disconnect("health_check")
    except Exception as e:
        logger.warning(f"Milvus health check failed: {e}")
        results["milvus"] = "fail"
    
    # Check Etcd (Milvus dependency) - Skip if using embedded Etcd (local/standalone mode)
    etcd_embedded = os.getenv("ETCD_USE_EMBED", "false").lower() == "true"
    if not etcd_embedded:
        try:
            import httpx
            etcd_host = os.getenv("ETCD_HOST", "etcd")
            etcd_port = os.getenv("ETCD_PORT", "2379")
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(f"http://{etcd_host}:{etcd_port}/health")
                if resp.status_code == 200:
                    results["etcd"] = "ok"
        except Exception as e:
            logger.warning(f"Etcd health check failed: {e}")
            results["etcd"] = "fail"
    else:
        # Embedded Etcd - mark as ok if Milvus is ok
        results["etcd"] = "ok" if results["milvus"] == "ok" else "fail"
    
    # Check Minio (Milvus storage) - Skip if using local storage (standalone mode)
    storage_type = os.getenv("COMMON_STORAGETYPE", "minio").lower()
    if storage_type != "local":
        try:
            import httpx
            minio_host = os.getenv("MINIO_HOST", "minio")
            minio_port = os.getenv("MINIO_PORT", "9000")
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(f"http://{minio_host}:{minio_port}/minio/health/live")
                if resp.status_code == 200:
                    results["minio"] = "ok"
        except Exception as e:
            logger.warning(f"Minio health check failed: {e}")
            results["minio"] = "fail"
    else:
        # Local storage - mark as ok if Milvus is ok
        results["minio"] = "ok" if results["milvus"] == "ok" else "fail"
    
    # Check Ollama (try multiple endpoints with fallback)
    llm_host = os.getenv("LLM_HOST", "ollama")
    llm_port = os.getenv("LLM_PORT", "11434")
    ollama_endpoints = [
        f"http://{llm_host}:{llm_port}/api/tags",
        f"http://host.docker.internal:{llm_port}/api/tags",
        f"http://localhost:{llm_port}/api/tags",
    ]
    
    try:
        import httpx
        for endpoint in ollama_endpoints:
            try:
                with httpx.Client(timeout=2.0) as client:
                    resp = client.get(endpoint)
                    if resp.status_code == 200:
                        results["ollama"] = "ok"
                        break
            except Exception:
                continue
    except ImportError:
        # Fallback to requests if httpx not available
        import requests
        for endpoint in ollama_endpoints:
            try:
                resp = requests.get(endpoint, timeout=2.0)
                if resp.status_code == 200:
                    results["ollama"] = "ok"
                    break
            except Exception:
                continue
    
    # Check Redis
    if redis_conn:
        try:
            redis_conn.ping()
            results["redis"] = "ok"
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            results["redis"] = "fail"
    else:
        results["redis"] = "unavailable"
    
    # Check Embeddings model with actual embedding test
    try:
        if rag_pipeline and hasattr(rag_pipeline, 'embedding_model'):
            # Test actual embedding generation to verify model is working
            test_result = rag_pipeline.embedding_model.embed_query("health check test")
            if test_result is not None and len(test_result) > 0:
                results["embeddings"] = "ok"
            else:
                results["embeddings"] = "fail"
        else:
            results["embeddings"] = "not_loaded"
    except Exception as e:
        logger.warning(f"Embeddings health check failed: {e}")
        results["embeddings"] = "fail"
    
    # Update cache
    with _health_cache_lock:
        _health_cache["data"] = results
        _health_cache["timestamp"] = time.time()
    
    return results


@app.get("/health/stream")
async def health_stream():
    """
    Server-Sent Events (SSE) endpoint for real-time health updates.
    Pushes health status every 15 seconds instead of client polling.
    """
    async def event_generator():
        try:
            while True:
                # Get health status (uses cache)
                health_data = await health_check_dependencies()
                
                # Send as SSE event
                yield f"data: {json.dumps(health_data)}\n\n"
                
                # Wait 15 seconds before next update
                await asyncio.sleep(15)
                
        except asyncio.CancelledError:
            logger.info("Health stream connection closed by client")
            raise
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@app.get("/llm/health")
async def llm_health_check() -> Dict[str, Any]:
    """
    Detailed LLM health check with sample generation test.
    Returns model name, reachability, and a test sample.
    """
    llm_model = os.getenv("LLM_MODEL", "mistral")
    llm_host = os.getenv("LLM_HOST", "ollama")
    llm_port = os.getenv("LLM_PORT", "11434")
    
    result = {
        "model": llm_model,
        "host": llm_host,
        "port": llm_port,
        "reachable": False,
        "sample": None,
        "error": None
    }
    
    # Try endpoints
    endpoints = [
        f"http://{llm_host}:{llm_port}/api/generate",
        f"http://host.docker.internal:{llm_port}/api/generate",
    ]
    
    try:
        import httpx
        use_httpx = True
    except ImportError:
        import requests
        use_httpx = False
    
    for endpoint in endpoints:
        try:
            payload = {
                "model": llm_model,
                "prompt": "ping",
                "options": {"num_predict": 10},
                "stream": False
            }
            
            if use_httpx:
                with httpx.Client(timeout=5.0) as client:
                    resp = client.post(endpoint, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
            else:
                resp = requests.post(endpoint, json=payload, timeout=5.0)
                resp.raise_for_status()
                data = resp.json()
            
            sample_text = data.get("response", "")[:50]
            result["reachable"] = True
            result["sample"] = sample_text
            result["endpoint"] = endpoint
            break
            
        except Exception as e:
            result["error"] = f"{type(e).__name__}: {str(e)[:100]}"
            continue
    
    return result


def needs_conversation_context(query: str, has_history: bool) -> bool:
    """
    Smart detection: Does this query need conversation history?
    
    Returns True if query appears to reference previous context.
    Returns False for standalone questions.
    
    This improves performance by avoiding unnecessary context for new topics.
    """
    if not has_history:
        return False  # No history to use
    
    query_lower = query.lower().strip()
    
    # Very short queries are often follow-ups
    if len(query_lower.split()) <= 3:
        return True
    
    # Check for referential pronouns and follow-up indicators
    follow_up_indicators = [
        # Pronouns
        'it', 'its', 'that', 'this', 'these', 'those', 'they', 'them',
        # Follow-up requests
        'more', 'explain', 'elaborate', 'detail', 'expand', 'clarify',
        'continue', 'further', 'additionally', 'also',
        # Questions about previous content
        'what about', 'how about', 'what do you mean', 'you said', 'you mentioned',
        # Comparisons and references
        'same', 'similar', 'different', 'compare', 'versus', 'vs',
        # Direct references
        'above', 'previous', 'earlier', 'before', 'mentioned'
    ]
    
    # Check if query starts with follow-up words (strong signal)
    first_words = ' '.join(query_lower.split()[:3])
    for indicator in ['can you', 'could you', 'please', 'more', 'explain', 'what about']:
        if first_words.startswith(indicator):
            return True
    
    # Check if query contains any follow-up indicators
    for indicator in follow_up_indicators:
        if indicator in query_lower:
            return True
    
    # Standalone questions typically start with question words
    standalone_starters = [
        'what is', 'what are', 'who is', 'who are', 'where is', 'where are',
        'when is', 'when are', 'why is', 'why are', 'how does', 'how do',
        'tell me about', 'explain the', 'describe', 'list', 'show me'
    ]
    
    for starter in standalone_starters:
        if query_lower.startswith(starter):
            return False  # Likely a new topic
    
    # Default: use context if we have history (conservative approach)
    return True


@app.post("/ask", response_model=QueryResponse)
async def ask_question(query_req: QueryRequest, request: Request) -> QueryResponse:
    """
    Process a user query through the RAG pipeline with conversational memory
    """
    if not rag_pipeline:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")
    
    if not query_req.query or not query_req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Generate session ID if not provided
    session_id = query_req.session_id or str(uuid.uuid4())
    
    # Get conversation history for this session
    history = chat_sessions.get(session_id, [])
    
    # Measure latency
    start_time = time.perf_counter()
    
    # We'll capture thread_id inside the executor thread
    thread_id_holder = {'id': None}
    
    try:
        # Check if client is still connected before processing
        if await request.is_disconnected():
            logger.info(f"Client disconnected before processing (session: {session_id[:8]}...)")
            raise HTTPException(status_code=499, detail="Client disconnected")
        
        # Start background task to monitor disconnection and update cancellation flag
        async def monitor_disconnection():
            try:
                # Wait a bit for thread_id to be captured
                await asyncio.sleep(0.1)
                while True:
                    await asyncio.sleep(0.5)  # Check every 500ms
                    if await request.is_disconnected():
                        # Mark this thread's request as cancelled
                        thread_id = thread_id_holder['id']
                        if thread_id:
                            with LLMClient._requests_lock:
                                if thread_id in LLMClient._active_requests:
                                    LLMClient._active_requests[thread_id] = False
                                    logger.info(f"Client disconnected during processing - marked for cancellation (session: {session_id[:8]}...)")
                        break
            except Exception as e:
                logger.debug(f"Disconnection monitor error (expected on completion): {e}")
        
        # Start monitoring task
        monitor_task = asyncio.create_task(monitor_disconnection())
        
        try:
            # Wrapper to run RAG pipeline in thread and capture thread_id
            def run_rag_query():
                # Capture thread ID in the executor thread
                thread_id_holder['id'] = threading.get_ident()
                
                # Smart context detection: Only use history if query needs it
                use_context = needs_conversation_context(query_req.query, bool(history))
                
                if use_context and history:
                    logger.info(f"📚 Using conversation context (detected follow-up query)")
                    return rag_pipeline.generate_with_context(query_req.query, history)
                else:
                    if history:
                        logger.info(f"🆕 Treating as new topic (standalone query)")
                    # First message or standalone question - use standard query (faster)
                    return rag_pipeline.query(query_req.query)
            
            # Run synchronous RAG pipeline in thread pool to avoid blocking event loop
            result = await asyncio.to_thread(run_rag_query)
            
            # Check again after generation (in case it took long)
            if await request.is_disconnected():
                logger.info(f"Client disconnected after generation (session: {session_id[:8]}...)")
                raise HTTPException(status_code=499, detail="Client disconnected")
        finally:
            # Always cancel monitoring task to prevent resource leak
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                # Expected exception when cancelling task; safe to ignore
                pass
        
        # Calculate latency
        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000
        
        # Update conversation history
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []
        
        chat_sessions[session_id].append({
            "role": "user",
            "content": query_req.query
        })
        chat_sessions[session_id].append({
            "role": "assistant",
            "content": result["answer"]
        })
        
        # Keep only last 5 turns (10 messages: 5 user + 5 assistant)
        if len(chat_sessions[session_id]) > 10:
            chat_sessions[session_id] = chat_sessions[session_id][-10:]
        
        logger.info(f"Query processed in {latency_ms:.2f}ms (session: {session_id[:8]}..., history: {len(history)//2} turns)")
        
        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            latency_ms=round(latency_ms, 2),
            session_id=session_id
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions (like 499 for disconnection)
        raise
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        # LLM client already returns user-friendly messages for common errors
        # This handler only catches unexpected exceptions
        raise HTTPException(
            status_code=500,
            detail="I encountered an unexpected error while processing your request. Please try again."
        )


@app.post("/api/ingest/upload", response_model=IngestionJobResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document for asynchronous ingestion
    
    Accepts a file upload and enqueues it for processing by the ingestion worker.
    Returns a job ID that can be used to check the processing status.
    
    Args:
        file: Uploaded file (text format)
        
    Returns:
        Job ID and status information
    """
    if not REDIS_AVAILABLE or ingestion_queue is None:
        raise HTTPException(
            status_code=503,
            detail="Ingestion service not available - Redis not connected"
        )
    
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Validate file type
        if not file.filename.endswith(('.txt', '.md', '.text')):
            raise HTTPException(
                status_code=400,
                detail="Only text files (.txt, .md) are supported"
            )
        
        # Save uploaded file
        file_path = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f" Saved uploaded file: {file_path}")
        
        # Enqueue ingestion job (RQ requires string path to function)
        job = ingestion_queue.enqueue(
            'ingestion.pipeline.ingest_document_job',
            file_path,
            file.filename,
            None,  # metadata
            job_timeout='10m',
            result_ttl=86400,
            failure_ttl=604800
        )
        
        logger.info(f" Enqueued ingestion job {job.id} for {file.filename}")
        
        return IngestionJobResponse(
            job_id=job.id,
            status="queued",
            message=f"Document '{file.filename}' queued for ingestion",
            file_path=file_path
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest/confluence")
async def ingest_confluence(payload: Dict[str, str] = None):
    """
    Trigger Confluence ingestion (local or api mode).

    This endpoint is used by the local startup script to force-loading
    sample Confluence documents into the RAG pipeline when Milvus is empty.

    Payload (optional): {"mode": "local"} or {"mode": "api"}
    """
    mode = None
    try:
        if payload and isinstance(payload, dict):
            mode = payload.get("mode")
    except Exception:
        mode = None

    mode = mode or os.getenv("CONFLUENCE_MODE", "local")

    try:
        ingestor = ConfluenceIngestor(mode=mode)
        docs = ingestor.get_documents()
        logger.info(f"/ingest/confluence: fetched {len(docs)} documents (mode={mode})")

        # If RAG pipeline is initialized, load these documents into Milvus
        if rag_pipeline:
            try:
                # Update confluence_docs and perform initial load synchronously
                rag_pipeline.confluence_docs = docs
                rag_pipeline._load_initial_data()
                rag_pipeline._extract_document_topics()
                return {"status": "success", "loaded": len(docs), "message": "Documents loaded into Milvus"}
            except Exception as e:
                logger.error(f"Error loading documents into RAG pipeline: {e}", exc_info=True)
                return {"status": "partial", "loaded": 0, "message": str(e)}

        return {"status": "fetched", "count": len(docs), "message": "Documents fetched; backend not ready to load into Milvus"}

    except Exception as e:
        logger.error(f"/ingest/confluence failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ingest/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Check the status of an ingestion job
    
    Args:
        job_id: The job ID returned from the upload endpoint
        
    Returns:
        Job status and result (if completed)
    """
    if not REDIS_AVAILABLE or redis_conn is None:
        raise HTTPException(
            status_code=503,
            detail="Ingestion service not available - Redis not connected"
        )
    
    try:
        # Get job from Redis
        job = Job.fetch(job_id, connection=redis_conn)
        
        # Map RQ status to our response
        status_map = {
            'queued': 'queued',
            'started': 'processing',
            'finished': 'completed',
            'failed': 'failed',
            'stopped': 'stopped',
            'scheduled': 'scheduled',
            'deferred': 'deferred',
            'canceled': 'canceled'
        }
        
        status = status_map.get(job.get_status(), 'unknown')
        
        response = JobStatusResponse(
            job_id=job_id,
            status=status,
            result=job.result if job.is_finished else None,
            error=str(job.exc_info) if job.is_failed else None
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Error fetching job status: {e}", exc_info=True)
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}"
        )


@app.delete("/api/ingest/job/{job_id}")
async def cancel_job(job_id: str):
    """
    Cancel a pending or running ingestion job
    
    Args:
        job_id: The job ID to cancel
        
    Returns:
        Cancellation status
    """
    if not REDIS_AVAILABLE or redis_conn is None:
        raise HTTPException(
            status_code=503,
            detail="Ingestion service not available - Redis not connected"
        )
    
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        
        if job.is_finished:
            return {"status": "already_completed", "message": "Job already completed"}
        
        if job.is_failed:
            return {"status": "already_failed", "message": "Job already failed"}
        
        job.cancel()
        logger.info(f" Cancelled job {job_id}")
        
        return {"status": "cancelled", "message": f"Job {job_id} cancelled"}
    
    except Exception as e:
        logger.error(f"Error cancelling job: {e}", exc_info=True)
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}"
        )
    
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@app.post("/api/webhook/confluence", response_model=WebhookResponse)
async def confluence_webhook(
    request: Request,
    payload: ConfluenceWebhookPayload,
    background_tasks: BackgroundTasks,
    x_atlassian_webhook_signature: Optional[str] = Header(None)
):
    """
    Receive Confluence webhook events and trigger automatic document sync
    
    Confluence sends webhooks when pages are created, updated, or deleted.
    This endpoint validates the signature, then processes updates asynchronously.
    
    Expected payload structure:
    {
        "event": "page_created" or "page_updated" or "page_removed",
        "page": {
            "id": "12345",
            "title": "Page Title",
            "url": "https://yourcompany.atlassian.net/wiki/spaces/ENG/pages/12345",
            "space": {"key": "ENG", "name": "Engineering"},
            ...
        }
    }
    
    Args:
        request: FastAPI request object (for signature validation)
        payload: Confluence webhook payload
        background_tasks: FastAPI background tasks manager
        x_atlassian_webhook_signature: Webhook signature header
        
    Returns:
        Webhook processing status (immediately, actual processing happens in background)
    """
    try:
        # 🔒 PRIORITY 1: Signature Validation
        webhook_secret = os.getenv("CONFLUENCE_WEBHOOK_SECRET", "")
        if webhook_secret:
            # Read raw body for signature validation
            body = await request.body()
            
            if not validate_atlassian_webhook_signature(
                body, 
                x_atlassian_webhook_signature or "", 
                webhook_secret
            ):
                logger.warning("⚠️  Webhook signature validation failed")
                raise HTTPException(
                    status_code=401,
                    detail="Invalid webhook signature"
                )
            logger.info("✅ Webhook signature validated")
        else:
            logger.warning("⚠️  Webhook secret not configured - signature validation skipped")
        
        # Extract page information
        event_type = payload.event
        page_info = payload.page
        page_id = page_info.get("id", "unknown")
        page_title = page_info.get("title", "Untitled")
        page_url = page_info.get("url", "")
        
        # Validate required fields
        if not page_id or page_id == "unknown":
            raise HTTPException(
                status_code=400,
                detail="Missing required field: page.id"
            )
        
        logger.info(f"📡 Confluence webhook received: {event_type}")
        logger.info(f"   Page ID: {page_id}")
        logger.info(f"   Title: {page_title}")
        logger.info(f"   URL: {page_url}")
        
        # Generate unique job ID
        job_id = f"webhook_{event_type}_{page_id}_{int(time.time())}"
        
        # 🚀 PRIORITY 1: Async Background Processing
        # Schedule processing in background to prevent timeout
        background_tasks.add_task(
            process_webhook_with_retry,
            event_type,
            page_id,
            page_title,
            page_url,
            job_id
        )
        
        # Return immediately
        logger.info(f"✅ Webhook queued for background processing: {job_id}")
        return WebhookResponse(
            status="queued",
            message=f"Webhook for page '{page_title}' queued for processing",
            job_id=job_id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error processing Confluence webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing webhook: {str(e)}"
        )


async def process_webhook_with_retry(
    event_type: str,
    page_id: str,
    page_title: str,
    page_url: str,
    job_id: str,
    max_retries: int = 3
):
    """
    🔄 PRIORITY 1: Process webhook with retry logic
    
    Handles transient failures with exponential backoff.
    
    Args:
        event_type: Type of webhook event (page_created, page_updated, page_removed)
        page_id: Confluence page ID
        page_title: Page title
        page_url: Page URL
        job_id: Unique job identifier
        max_retries: Maximum retry attempts (default: 3)
    """
    attempt = 0
    last_error = None
    
    while attempt < max_retries:
        try:
            attempt += 1
            logger.info(f"🔄 Processing webhook job {job_id} (attempt {attempt}/{max_retries})")
            
            # Handle different event types
            if event_type in ["page_created", "page_updated"]:
                # Fetch the latest page content from Confluence API
                from confluence_ingest import ConfluenceIngestor
                ingestor = ConfluenceIngestor(mode='api')
                page_data = ingestor.fetch_page_by_id(page_id)
                
                if not page_data:
                    raise Exception(f"Could not fetch page {page_id} from Confluence")
                
                # Update document in Milvus (delete old + insert new)
                success = rag_pipeline.update_single_document(page_id, page_data)
                
                if success:
                    logger.info(f"✅ Webhook job {job_id} completed: {page_title}")
                    return  # Success - exit retry loop
                else:
                    raise Exception(f"Failed to update document {page_id}")
            
            elif event_type == "page_removed":
                # Delete document from Milvus
                success = rag_pipeline.delete_single_document(page_id)
                
                if success:
                    logger.info(f"✅ Webhook job {job_id} completed: Page {page_id} deleted")
                    return  # Success - exit retry loop
                else:
                    logger.warning(f"⚠️  Page {page_id} not found in RAG system (may not have been indexed)")
                    return  # Not an error - page wasn't indexed
            
            else:
                logger.warning(f"⚠️  Unknown event type: {event_type}")
                return  # Don't retry for unknown events
        
        except Exception as e:
            last_error = e
            logger.error(f"❌ Attempt {attempt}/{max_retries} failed for job {job_id}: {e}")
            
            # Don't retry on last attempt
            if attempt >= max_retries:
                logger.error(f"💥 Job {job_id} failed after {max_retries} attempts: {last_error}")
                break
            
            # Exponential backoff: 2^attempt seconds (2s, 4s, 8s, ...)
            backoff_time = 2 ** attempt
            logger.info(f"⏳ Retrying in {backoff_time} seconds...")
            await asyncio.sleep(backoff_time)
    
    # If we reach here, all retries failed
    logger.error(f"💥 Webhook job {job_id} permanently failed after {max_retries} attempts")
    logger.error(f"   Last error: {last_error}")


@app.post("/api/confluence/sync-now")
async def trigger_confluence_sync():
    """
    Manually trigger an immediate Confluence sync check
    
    Detects new, updated, and deleted pages from Confluence.
    
    Returns:
        Sync status and summary of changes
    """
    global confluence_last_versions
    
    try:
        logger.info("🔄 Manual Confluence sync triggered via API")
        
        # DEBUG: Show current cache state
        logger.info(f"   📦 Cache currently has {len(confluence_last_versions)} pages tracked")
        if confluence_last_versions:
            sample_ids = list(confluence_last_versions.keys())[:3]
            for sample_id in sample_ids:
                logger.debug(f"      Sample: ID {sample_id} → v{confluence_last_versions[sample_id]}")
        
        # Fetch all pages from Confluence
        from confluence_ingest import ConfluenceIngestor
        ingestor = ConfluenceIngestor(mode='api')
        pages = ingestor.get_documents()
        
        if not pages:
            return {
                "status": "error",
                "message": "No pages fetched from Confluence",
                "new": 0,
                "updated": 0,
                "deleted": 0,
                "unchanged": 0
            }
        
        # Track changes
        new_count = 0
        updated_count = 0
        unchanged_count = 0
        deleted_count = 0
        
        # Get current page IDs from Confluence
        current_page_ids = {page.get("id") for page in pages}
        
        # Check for deleted pages (in our cache but not in Confluence anymore)
        deleted_page_ids = set(confluence_last_versions.keys()) - current_page_ids
        
        for deleted_page_id in deleted_page_ids:
            logger.info(f"   🗑️  Deleted page: ID {deleted_page_id}")
            success = rag_pipeline.delete_single_document(deleted_page_id)
            if success:
                del confluence_last_versions[deleted_page_id]
                deleted_count += 1
                logger.info(f"   ✅ Removed from RAG system")
        
        # Process existing/new/updated pages
        for page in pages:
            page_id = page.get("id")
            page_title = page.get("title", "Untitled")
            page_version = page.get("version", 1)
            
            # DEBUG: Log version comparison for every page
            cached_version = confluence_last_versions.get(page_id, "NOT_IN_CACHE")
            logger.debug(f"   🔍 Page '{page_title}' (ID: {page_id}): cached={cached_version}, current={page_version}")
            
            # Check if this is a new or updated page
            if page_id not in confluence_last_versions:
                # New page - add it
                logger.info(f"   📄 New page: {page_title} (ID: {page_id})")
                success = rag_pipeline.update_single_document(page_id, page)
                if success:
                    confluence_last_versions[page_id] = page_version
                    new_count += 1
            elif confluence_last_versions[page_id] < page_version:
                # Page updated - sync it
                old_version = confluence_last_versions[page_id]
                logger.info(f"   🔄 Updated page: {page_title} (ID: {page_id}, v{old_version} → v{page_version})")
                success = rag_pipeline.update_single_document(page_id, page)
                if success:
                    confluence_last_versions[page_id] = page_version
                    updated_count += 1
            else:
                # No changes
                logger.debug(f"   ⏭️  Unchanged: {page_title} (ID: {page_id}, v{page_version})")
                unchanged_count += 1
        
        # Summary
        message = f"Sync complete: {new_count} new, {updated_count} updated, {deleted_count} deleted, {unchanged_count} unchanged"
        logger.info(f"✅ {message}")
        
        return {
            "status": "success",
            "message": message,
            "new": new_count,
            "updated": updated_count,
            "deleted": deleted_count,
            "unchanged": unchanged_count,
            "total": len(pages) + deleted_count
        }
        
    except Exception as e:
        logger.error(f"❌ Manual sync failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {str(e)}"
        )


@app.get("/api/confluence/pages")
async def list_confluence_pages():
    """
    List all tracked Confluence pages with hierarchy information
    
    Returns:
        List of pages with their hierarchy details
    """
    try:
        global confluence_last_versions
        
        if not confluence_last_versions:
            return {
                "status": "success",
                "pages": [],
                "total": 0,
                "message": "No Confluence pages tracked yet"
            }
        
        # Fetch current page details with hierarchy
        from confluence_ingest import ConfluenceIngestor
        ingestor = ConfluenceIngestor(mode='api')
        pages = ingestor.get_documents()
        
        # Build page list with hierarchy info
        page_list = []
        for page in pages:
            page_info = {
                "id": page.get("id"),
                "title": page.get("title"),
                "version": page.get("version", 1),
                "url": page.get("url"),
                "depth": page.get("depth", 0),
                "parent_id": page.get("parent_id"),
                "parent_title": page.get("parent_title"),
                "breadcrumb": page.get("breadcrumb", ""),
                "has_hierarchy_context": "[Page Hierarchy:" in page.get("body", "")
            }
            page_list.append(page_info)
        
        # Sort by breadcrumb to show hierarchy visually
        page_list.sort(key=lambda p: (p["breadcrumb"], p["title"]))
        
        return {
            "status": "success",
            "pages": page_list,
            "total": len(page_list),
            "root_pages": len([p for p in page_list if p["depth"] == 0]),
            "nested_pages": len([p for p in page_list if p["depth"] > 0]),
            "max_depth": max([p["depth"] for p in page_list]) if page_list else 0
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to list pages: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list pages: {str(e)}"
        )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "RAG Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "ask": "/ask (POST)",
            "evaluate": "/evaluate (GET)",
            "docs": "/docs"
        }
    }


@app.get("/evaluate")
async def evaluate():
    """
    Run evaluation script and return results.
    This endpoint triggers the evaluation script and returns the results.
    """
    import subprocess
    import os
    
    try:
        # Run evaluation script
        result = subprocess.run(
            ["python", "evaluate_poc.py"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        # Check if results file exists
        results_file = "/app/results/results.md"
        if os.path.exists(results_file):
            with open(results_file, "r") as f:
                results_content = f.read()
            
            # Extract first few lines for preview
            preview_lines = results_content.split("\n")[:20]
            preview = "\n".join(preview_lines)
            
            return {
                "status": "success",
                "message": "Evaluation completed successfully",
                "results_file": results_file,
                "stdout": result.stdout,
                "preview": preview
            }
        else:
            return {
                "status": "error",
                "message": "Evaluation script ran but results file not found",
                "stdout": result.stdout,
                "stderr": result.stderr
            }
    
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "Evaluation timeout after 5 minutes"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error running evaluation: {str(e)}"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
