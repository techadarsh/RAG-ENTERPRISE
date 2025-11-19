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
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=32768),  # Increased to 32KB for full Confluence pages
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dim),
            # NEW: Add metadata fields for source tracking
            FieldSchema(name="source_type", dtype=DataType.VARCHAR, max_length=100, default_value="local"),  # "local", "confluence", etc.
            FieldSchema(name="source_url", dtype=DataType.VARCHAR, max_length=1000, default_value=""),  # Document URL
            FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=200, default_value="")  # External document ID
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
    
    def insert(self, titles: List[str], texts: List[str], embeddings: np.ndarray, 
               source_types: List[str] = None, source_urls: List[str] = None, doc_ids: List[str] = None):
        """
        Insert documents into collection
        
        Args:
            titles: List of document titles
            texts: List of document texts
            embeddings: numpy array of embeddings
            source_types: List of source types ("local", "confluence", etc.)
            source_urls: List of source URLs
            doc_ids: List of external document IDs
        """
        if len(titles) != len(texts) or len(titles) != len(embeddings):
            raise ValueError("Lengths of titles, texts, and embeddings must match")
        
        # Default metadata if not provided
        if source_types is None:
            source_types = ["local"] * len(titles)
        if source_urls is None:
            source_urls = [""] * len(titles)
        if doc_ids is None:
            doc_ids = [""] * len(titles)
        
        logger.info(f"Inserting {len(titles)} documents into Milvus")
        
        entities = [
            titles,
            texts,
            embeddings.tolist(),
            source_types,
            source_urls,
            doc_ids
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
            List of dictionaries with title, text, score, source_type, source_url
        """
        search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
        
        results = self.collection.search(
            data=[query_vector.tolist()],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["title", "text", "source_type", "source_url", "doc_id"]
        )
        
        output = []
        for hits in results:
            for hit in hits:
                output.append({
                    "title": hit.get("title"),
                    "text": hit.get("text"),
                    "score": hit.score,
                    "source_type": hit.get("source_type") or "local",
                    "source_url": hit.get("source_url") or "",
                    "doc_id": hit.get("doc_id") or ""
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
    
    def delete_by_doc_id(self, doc_id: str) -> int:
        """
        Delete all chunks/entries for a specific document ID
        
        Args:
            doc_id: The document ID to delete (e.g., Confluence page ID)
            
        Returns:
            Number of entities deleted
        """
        try:
            self.collection.load()
            
            # First, query to get all IDs matching this doc_id
            results = self.collection.query(
                expr=f'doc_id == "{doc_id}"',
                output_fields=["id"]
            )
            
            if not results:
                logger.info(f"No documents found with doc_id: {doc_id}")
                return 0
            
            # Extract primary key IDs
            ids_to_delete = [str(result["id"]) for result in results]
            
            # Delete using primary key IDs
            delete_expr = f"id in [{','.join(ids_to_delete)}]"
            self.collection.delete(delete_expr)
            
            logger.info(f"Deleted {len(ids_to_delete)} chunks for doc_id: {doc_id}")
            return len(ids_to_delete)
            
        except Exception as e:
            logger.error(f"Error deleting document with doc_id {doc_id}: {e}")
            raise
