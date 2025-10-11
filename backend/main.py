"""
FastAPI backend for RAG chatbot with lazy-loaded embeddings
"""
import logging
import time
import os
import threading
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from rag_pipeline import RAGPipeline
from confluence_ingest import ConfluenceIngestor
from embeddings import EmbeddingModel

# Load environment variables (don't override existing ones)
load_dotenv(override=False)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

# Global RAG pipeline instance
rag_pipeline = None

# In-memory chat session storage
# Format: {session_id: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
chat_sessions: Dict[str, List[Dict[str, str]]] = {}


def warmup_embeddings():
    """
    Warm up embedding model and load data in background after FastAPI starts
    This prevents blocking the startup event
    """
    try:
        logger.info("🔹 Background warm-up started ...")
        
        # Load embedding model first
        model = EmbeddingModel.get_model()
        # Warm up with a test encoding
        _ = model.encode(["warmup"], normalize_embeddings=True, show_progress_bar=False)
        logger.info("✅ Embedding model loaded in background and ready for use")
        
        # Now load data if needed
        if rag_pipeline and hasattr(rag_pipeline, 'load_data_if_needed'):
            rag_pipeline.load_data_if_needed()
            
    except Exception as e:
        logger.error(f"⚠️  Warm-up failed: {e}")


@app.on_event("startup")
async def startup_event():
    """Initialize RAG pipeline on startup (non-blocking for embeddings)"""
    global rag_pipeline
    
    logger.info("Starting up RAG chatbot backend")
    
    # Load Confluence documents (if enabled)
    confluence_mode = os.getenv("CONFLUENCE_MODE", "local")
    logger.info(f"Confluence integration mode: {confluence_mode}")
    
    confluence_docs = []
    if confluence_mode in ["local", "api"]:
        try:
            confluence_ingestor = ConfluenceIngestor()
            confluence_docs = confluence_ingestor.get_documents()
            logger.info(f"✅ Ingested {len(confluence_docs)} Confluence pages (mode: {confluence_mode})")
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
        logger.info("🚀 FastAPI started without blocking - background loading initiated")
        
    except Exception as e:
        logger.error(f"Failed to initialize RAG pipeline: {e}")
        raise


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "ok"}


@app.post("/ask", response_model=QueryResponse)
async def ask_question(request: QueryRequest) -> QueryResponse:
    """
    Process a user query through the RAG pipeline with conversational memory
    
    Args:
        request: QueryRequest with user query and optional session_id
        
    Returns:
        QueryResponse with answer, sources, latency, and session_id
    """
    if not rag_pipeline:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")
    
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Generate session ID if not provided
    import uuid
    session_id = request.session_id or str(uuid.uuid4())
    
    # Get conversation history for this session
    history = chat_sessions.get(session_id, [])
    
    # Measure latency
    start_time = time.perf_counter()
    
    try:
        # Process query with conversation context
        if history:
            result = rag_pipeline.generate_with_context(request.query, history)
        else:
            # First message in conversation - use standard query
            result = rag_pipeline.query(request.query)
        
        # Calculate latency
        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000
        
        # Update conversation history
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []
        
        chat_sessions[session_id].append({
            "role": "user",
            "content": request.query
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
    
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "RAG Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "ask": "/ask (POST)",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
