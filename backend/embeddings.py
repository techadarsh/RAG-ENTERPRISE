"""
Embeddings module with lazy-loading for BAAI/bge-base-en
Thread-safe singleton pattern to avoid startup blocking
"""
import os
import threading
import numpy as np
from typing import List
import logging

logger = logging.getLogger("EmbeddingModel")


class EmbeddingModel:
    """Thread-safe lazy loader for embedding model."""
    _model = None
    _lock = threading.Lock()
    _embedding_dim = 768
    
    def __init__(self, model_name: str = "BAAI/bge-base-en", embedding_dim: int = 768):
        """
        Initialize embedding model wrapper (does NOT load model yet)
        Model loads lazily on first use to avoid blocking FastAPI startup
        """
        self.model_name = model_name
        self._embedding_dim = embedding_dim
        logger.info(f"EmbeddingModel initialized (lazy loading enabled for {model_name})")
    
    @classmethod
    def get_model(cls):
        """Load model only once on first use (thread-safe singleton with fallback)"""
        if cls._model is None:
            with cls._lock:
                if cls._model is None:
                    from sentence_transformers import SentenceTransformer
                    
                    model_path = os.getenv("EMBEDDING_MODEL", "BAAI/bge-base-en")
                    logger.info(f" Loading embedding model from {model_path} ...")
                    
                    try:
                        cls._model = SentenceTransformer(model_path)
                        logger.info(f" Successfully loaded {model_path}")
                    except Exception as e:
                        logger.warning(f"  {model_path} failed to load ({e})")
                        logger.warning(" Falling back to lighter model: BAAI/bge-small-en-v1.5")
                        try:
                            cls._model = SentenceTransformer("BAAI/bge-small-en-v1.5")
                            logger.info(" Fallback model loaded successfully")
                        except Exception as fallback_error:
                            logger.error(f" Fallback model also failed: {fallback_error}")
                            raise
                    
                    # Verify dimension
                    test_vec = cls._model.encode(["test"], show_progress_bar=False, normalize_embeddings=True)
                    cls._embedding_dim = test_vec.shape[1]
                    
                    logger.info(f" Embedding model ready for use (dim={cls._embedding_dim})")
        
        return cls._model
    
    @property
    def embedding_dim(self):
        """Return embedding dimension"""
        return self._embedding_dim
    
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Embed a list of texts using semantic model (lazy loads on first call)
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            numpy array of embeddings (shape: [n_texts, embedding_dim])
        """
        if not texts:
            return np.array([])
        
        logger.info(f"Generating semantic embeddings for {len(texts)} texts...")
        
        # Lazy load model on first embedding request
        model = self.get_model()
        
        # Use sentence-transformers with smaller batches for faster processing
        embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,  # Disable progress bar to avoid timeout issues
            batch_size=8  # Smaller batch size for faster processing
        )
        
        logger.info(f" Generated {len(embeddings)} embeddings of dimension {embeddings.shape[1]}")
        return embeddings
    
    def embed_query(self, query: str) -> np.ndarray:
        """
        Embed a single query using semantic model (lazy loads on first call)
        
        Args:
            query: Query string to embed
            
        Returns:
            numpy array of embedding (shape: [embedding_dim])
        """
        logger.info(f"Embedding query: {query[:50]}...")
        
        # Lazy load model on first query
        model = self.get_model()
        
        # Encode single query with semantic model
        embedding = model.encode([query], normalize_embeddings=True, show_progress_bar=False)[0]
        
        return embedding

