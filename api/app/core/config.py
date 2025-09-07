
"""
FILE CONTRACT: config.py

Goal: Centralized configuration using Pydantic Settings.
Requirements:
- Load from environment variables only (never hardcode).
- Defaults should match our .env.example.
- Singleton `settings` instance exported.
- Include fields: API_HOST, API_PORT, CORS_ORIGINS,
  MILVUS_HOST, MILVUS_PORT, MILVUS_COLLECTION,
  EMBEDDINGS_HOST, EMBEDDINGS_PORT, EMBEDDINGS_MODEL,
  LLM_HOST, LLM_PORT, LLM_MODEL, LLM_MAX_TOKENS, LLM_TEMP,
  PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD, LOG_LEVEL.
- Add docstrings explaining each field and why it's needed.
"""

from pydantic import Field, AnyHttpUrl
from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    """
    Centralized configuration for the API service.
    All values are loaded from environment variables for security and portability.
    Uses Pydantic BaseSettings for type safety, validation, and .env support.
    """

    # --- API ---
    API_HOST: str = Field(
        "0.0.0.0",
        description="Host address for FastAPI server. Should be 0.0.0.0 for Dockerized deployments."
    )
    API_PORT: int = Field(
        8080,
        description="Port for FastAPI server. Exposed by the container for HTTP API access."
    )
    CORS_ORIGINS: List[AnyHttpUrl] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        description="Allowed CORS origins for frontend UI. Controls which web clients can access the API."
    )

    # --- Milvus Vector DB ---
    MILVUS_HOST: str = Field(
        "milvus",
        description="Hostname or IP address of the Milvus vector database."
    )
    MILVUS_PORT: int = Field(
        19530,
        description="gRPC port for Milvus. Used for all vector search and upsert operations."
    )
    MILVUS_COLLECTION: str = Field(
        "enterprise_docs",
        description="Milvus collection name for storing document vectors."
    )

    # --- Embeddings Service ---
    EMBEDDINGS_HOST: str = Field(
        "embeddings",
        description="Hostname or IP address of the embeddings HTTP service."
    )
    EMBEDDINGS_PORT: int = Field(
        8000,
        description="Port for the embeddings HTTP service."
    )
    EMBEDDINGS_MODEL: str = Field(
        "BAAI/bge-large-en-v1.5",
        description="Model identifier for the embeddings service. Controls which model is used for vectorization."
    )

    # --- LLM (Ollama) ---
    LLM_HOST: str = Field(
        "ollama",
        description="Hostname or IP address of the Ollama LLM service."
    )
    LLM_PORT: int = Field(
        11434,
        description="Port for the Ollama LLM service."
    )
    LLM_MODEL: str = Field(
        "mistral:7b-instruct-q4_K_M",
        description="Model name for the LLM. Used to select the quantized Mistral-7B model."
    )
    LLM_MAX_TOKENS: int = Field(
        512,
        description="Maximum number of tokens to generate in LLM responses. Controls output length."
    )
    LLM_TEMP: float = Field(
        0.2,
        description="Temperature for LLM sampling. Lower values make output more deterministic."
    )

    # --- Postgres (Optional Metadata DB) ---
    PG_HOST: str = Field(
        "postgres",
        description="Hostname or IP address of the Postgres database."
    )
    PG_PORT: int = Field(
        5432,
        description="Port for the Postgres database."
    )
    PG_DB: str = Field(
        "ragdb",
        description="Database name for Postgres. Used for metadata, feedback, and logging."
    )
    PG_USER: str = Field(
        "rag",
        description="Username for Postgres authentication."
    )
    PG_PASSWORD: str = Field(
        "ragpass",
        description="Password for Postgres authentication."
    )

    # --- Logging ---
    LOG_LEVEL: str = Field(
        "INFO",
        description="Log level for API service. Controls verbosity of logs (DEBUG, INFO, WARNING, ERROR)."
    )

    class Config:
        env_file = os.getenv("API_ENV_FILE", ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True

# Singleton settings instance for global use
settings = Settings()
