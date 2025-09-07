
"""
FILE CONTRACT: main.py

Goal: FastAPI entrypoint for the API container.
Requirements:
- Initialize logging (init_logging).
- Apply request ID middleware.
- Mount routers:
   * health (prefix /health)
   * root ("/") returning {service:"enterprise-rag",status:"alive"}
- Apply CORS policy using CORS_ORIGINS from settings.
- Ensure app is importable as `app` for uvicorn.
"""

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.logging import init_logging, request_id_middleware
from app.routes import health, chat

# Initialize structured logging at startup
init_logging(settings.LOG_LEVEL)

# Create FastAPI app
app = FastAPI(
    title="Enterprise RAG POC API",
    description="Backend API for Retrieval-Augmented Generation POC.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Apply CORS policy from settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Apply request ID middleware
request_id_middleware(app)

# Mount health router at /health
app.include_router(health.router, prefix="/health")

# Mount chat router at /chat
app.include_router(chat.router, prefix="/chat", tags=["chat"])


# Root endpoint for service banner
@app.get("/", tags=["root"])
def root() -> dict:
    """
    Returns a service banner for the API root.
    """
    return {"service": "enterprise-rag", "status": "alive"}
