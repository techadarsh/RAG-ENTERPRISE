"""
Milvus client for vector storage and retrieval
"""
import logging
import time
from typing import List, Dict, Any
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
import numpy as np

logger = logging.getLogger(__name__)


class MilvusClient:
    def __init__(self, host: str, port: int, collection_name: str, dim: int):
        """
        Initialize Milvus client
        
        Args:
            host: Milvus server host
            port: Milvus server port
            collection_name: Name of the collection
            dim: Dimension of embeddings
        """
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.dim = dim
        self.collection = None
        
    def connect(self, max_retries: int = 10, retry_delay: int = 5):
        """Connect to Milvus with retry logic"""
        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to Milvus at {self.host}:{self.port} (attempt {attempt + 1}/{max_retries})")
                connections.connect(
                    alias="default",
                    host=self.host,
                    port=str(self.port)
                )
                logger.info("Connected to Milvus successfully")
                self._setup_collection()
                return
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error("Max retries reached. Could not connect to Milvus")
                    raise
    
    def _setup_collection(self):
        """Create or load collection, recreating if dimension mismatch detected"""
        if utility.has_collection(self.collection_name):
            logger.info(f"Collection '{self.collection_name}' exists, checking schema...")
            existing_collection = Collection(self.collection_name)
            
            # Check if dimension matches
            schema_mismatch = False
            for field in existing_collection.schema.fields:
                if field.name == "embedding":
                    existing_dim = field.params.get('dim', 0)
                    if existing_dim != self.dim:
                        logger.warning(f"  Schema mismatch detected: existing dim={existing_dim}, required dim={self.dim}")
                        schema_mismatch = True
                        break
            
            if schema_mismatch:
                logger.info("Dropping old collection and creating new one with correct dimension...")
                utility.drop_collection(self.collection_name)
                self._create_new_collection()
            else:
                logger.info(f"Schema matches, loading collection '{self.collection_name}'")
                self.collection = existing_collection
                self.collection.load()
        else:
            logger.info(f"Collection '{self.collection_name}' does not exist, creating new one")
            self._create_new_collection()
    
    def _create_new_collection(self):
        """Create a new collection with current dimension"""
        logger.info(f"Creating new collection: {self.collection_name} with dim={self.dim}")
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dim)
        ]
        schema = CollectionSchema(fields=fields, description="Enterprise documents collection")
        self.collection = Collection(name=self.collection_name, schema=schema)
        
        # Create index for fast similarity search
        index_params = {
            "metric_type": "IP",  # Inner Product (cosine similarity for normalized vectors)
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128}
        }
        self.collection.create_index(field_name="embedding", index_params=index_params)
        logger.info(f" Collection created and indexed successfully (dim={self.dim})")
    
    def insert(self, titles: List[str], texts: List[str], embeddings: np.ndarray):
        """
        Insert documents into collection
        
        Args:
            titles: List of document titles
            texts: List of document texts
            embeddings: numpy array of embeddings
        """
        if len(titles) != len(texts) or len(titles) != len(embeddings):
            raise ValueError("Lengths of titles, texts, and embeddings must match")
        
        logger.info(f"Inserting {len(titles)} documents into Milvus")
        
        entities = [
            titles,
            texts,
            embeddings.tolist()
        ]
        
        self.collection.insert(entities)
        self.collection.flush()
        self.collection.load()
        logger.info("Documents inserted successfully")
    
    def search(self, query_vector: np.ndarray, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Search for similar documents
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            
        Returns:
            List of dictionaries with title, text, and score
        """
        search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
        
        results = self.collection.search(
            data=[query_vector.tolist()],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["title", "text"]
        )
        
        output = []
        for hits in results:
            for hit in hits:
                output.append({
                    "title": hit.entity.get("title"),
                    "text": hit.entity.get("text"),
                    "score": hit.score
                })
        
        logger.info(f"Found {len(output)} results")
        return output
    
    def count(self) -> int:
        """Get document count in collection"""
        return self.collection.num_entities
    
    def is_empty(self) -> bool:
        """Check if collection is empty"""
        return self.count() == 0
    
    def get_all_documents(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Retrieve all documents from the collection (up to limit)
        
        Args:
            limit: Maximum number of documents to retrieve
            
        Returns:
            List of documents with their metadata
        """
        try:
            self.collection.load()
            
            # Query all documents
            results = self.collection.query(
                expr="id >= 0",  # Get all documents
                output_fields=["id", "title", "text"],
                limit=limit
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving all documents: {e}")
            return []
