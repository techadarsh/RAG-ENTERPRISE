"""
FastAPI backend for RAG chatbot with lazy-loaded embeddings
"""
import logging
import time
import os
import threading
import uuid
import shutil
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from rag_pipeline import RAGPipeline
from confluence_ingest import ConfluenceIngestor
from embeddings import EmbeddingModel

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

# Load environment variables (don't override existing ones)
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

# Upload directory
UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


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
        
    except Exception as e:
        logger.error(f"Failed to initialize RAG pipeline: {e}")
        raise


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
    
    # Check Etcd (Milvus dependency)
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
    
    # Check Minio (Milvus storage)
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
    
    # Check Embeddings model
    try:
        if rag_pipeline and hasattr(rag_pipeline, 'embedding_model'):
            # Try a simple embedding to verify it's working
            test_result = rag_pipeline.embedding_model.embed_query("test")
            if test_result is not None and len(test_result) > 0:
                results["embeddings"] = "ok"
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
    import uuid
    session_id = query_req.session_id or str(uuid.uuid4())
    
    # Get conversation history for this session
    history = chat_sessions.get(session_id, [])
    
    # Measure latency
    start_time = time.perf_counter()
    
    try:
        # Check if client is still connected before processing
        if await request.is_disconnected():
            logger.info(f"Client disconnected before processing (session: {session_id[:8]}...)")
            raise HTTPException(status_code=499, detail="Client disconnected")
        
        # Process query with conversation context and request object for disconnection detection
        if history:
            result = rag_pipeline.generate_with_context(query_req.query, history, request=request)
        else:
            # First message in conversation - use standard query
            result = rag_pipeline.query(query_req.query, request=request)
        
        # Check again after generation (in case it took long)
        if await request.is_disconnected():
            logger.info(f"Client disconnected after generation (session: {session_id[:8]}...)")
            raise HTTPException(status_code=499, detail="Client disconnected")
        
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
        # Return user-friendly error message
        error_msg = "I encountered an unexpected error while processing your request. Please try again."
        
        # Check if it's a specific known error type
        error_str = str(e).lower()
        if "circuit" in error_str or "breaker" in error_str:
            error_msg = "I'm currently experiencing technical difficulties. Please try again in a moment."
        elif "timeout" in error_str or "timed out" in error_str:
            error_msg = "The request took too long to process. Please try asking a simpler question or try again later."
        elif "connection" in error_str or "unreachable" in error_str:
            error_msg = "I'm having trouble connecting to the AI service. Please try again in a moment."
        
        raise HTTPException(status_code=500, detail=error_msg)


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
async def confluence_webhook(payload: ConfluenceWebhookPayload):
    """
    Receive Confluence webhook events and enqueue ingestion jobs
    
    Confluence sends webhooks when pages are created or updated.
    This endpoint extracts the page information and queues it for ingestion.
    
    Expected payload structure:
    {
        "event": "page_created" or "page_updated",
        "page": {
            "id": "12345",
            "title": "Page Title",
            "url": "https://yourcompany.atlassian.net/wiki/spaces/ENG/pages/12345",
            "space": {"key": "ENG", "name": "Engineering"},
            ...
        }
    }
    
    Args:
        payload: Confluence webhook payload
        
    Returns:
        Webhook processing status and job ID
    """
    if not REDIS_AVAILABLE or redis_conn is None:
        raise HTTPException(
            status_code=503,
            detail="Ingestion service not available - Redis not connected"
        )
    
    try:
        # Validate webhook secret if configured
        webhook_secret = os.getenv("CONFLUENCE_WEBHOOK_SECRET", "")
        if webhook_secret:
            # In production, validate the webhook signature
            # For now, we'll just check if it's present in headers
            # Confluence typically sends X-Atlassian-Webhook-Signature header
            pass
        
        # Extract page information
        event_type = payload.event
        page_info = payload.page
        page_id = page_info.get("id", "unknown")
        page_title = page_info.get("title", "Untitled")
        page_url = page_info.get("url", "")
        
        # Validate required fields
        if not page_url:
            raise HTTPException(
                status_code=400,
                detail="Missing required field: page.url"
            )
        
        logger.info(f" Confluence webhook received: {event_type}")
        logger.info(f"   Page ID: {page_id}")
        logger.info(f"   Title: {page_title}")
        logger.info(f"   URL: {page_url}")
        
        # Enqueue URL ingestion job
        # We'll pass a special marker to indicate this is a URL-based job
        job = ingestion_queue.enqueue(
            'ingestion.pipeline.ingest_url_job',
            page_url,
            page_title,
            job_timeout='10m',
            result_ttl=86400,
            failure_ttl=604800
        )
        
        logger.info(f" Confluence webhook processed → Enqueued job {job.id}")
        
        return WebhookResponse(
            status="success",
            message=f"Confluence page '{page_title}' queued for ingestion",
            job_id=job.id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Confluence webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing webhook: {str(e)}"
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
