
"""
FILE CONTRACT: logging.py

Goal: Structured JSON logging and request ID middleware.
Requirements:
- Use Python logging configured to JSON (logfmt acceptable if JSON is complex).
- Log level set by LOG_LEVEL env.
- Include request ID middleware:
   * If client sends X-Request-ID, reuse it.
   * Otherwise generate a UUID.
   * Inject into request.state and response headers.
- Provide functions: init_logging(), request_id_middleware(app).
- Add full comments and usage examples.
"""


import logging
import sys
import json
import uuid
from fastapi import Request, Response, FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Callable, Optional
import os

class JsonLogFormatter(logging.Formatter):
    """
    Custom logging formatter that outputs logs as JSON for structured log aggregation.
    Includes timestamp, log level, logger name, message, and request_id if present.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Optionally include request_id if present
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        return json.dumps(log_record)

def init_logging(log_level: Optional[str] = None) -> None:
    """
    Configure root logger to output JSON logs to stdout.
    Log level is set by LOG_LEVEL env or argument.

    Usage:
        from app.core.logging import init_logging
        init_logging()
    """
    level = log_level or os.getenv("LOG_LEVEL", "INFO")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    logging.basicConfig(
        level=level,
        handlers=[handler],
        force=True
    )

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that attaches a unique request ID to each incoming HTTP request.
    - If the client sends X-Request-ID, reuse it.
    - Otherwise, generate a new UUID.
    - Injects request_id into request.state and response headers.
    """
    def __init__(self, app: ASGIApp, header_name: str = "X-Request-ID"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get(self.header_name) or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[self.header_name] = request_id
        return response

def request_id_middleware(app: FastAPI, header_name: str = "X-Request-ID") -> None:
    """
    Adds the request ID middleware to a FastAPI app.

    Usage:
        from app.core.logging import request_id_middleware
        app = FastAPI()
        request_id_middleware(app)
    """
    app.add_middleware(RequestIDMiddleware, header_name=header_name)

def get_request_id(request: Request) -> str:
    """
    Retrieves the request ID from the request state for use in logging or tracing.
    """
    return getattr(request.state, "request_id", "")
