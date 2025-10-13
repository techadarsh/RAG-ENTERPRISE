"""
Document ingestion pipeline for processing and indexing documents
Handles chunking, embedding generation, and Milvus insertion
Supports both file-based and URL-based ingestion
"""
import logging
import os
import sys
import time
import requests
from typing import List, Dict, Any
from pathlib import Path

# Add parent directory to path to import shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from embeddings import EmbeddingModel
from milvus_client import MilvusClient

# Configure logging before creating logger instance
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IngestionPipeline:
    """
    Handles the complete document ingestion workflow
    """
    
    def __init__(self):
        """Initialize pipeline with shared components"""
        logger.info(" Initializing IngestionPipeline")
        
        # Get configuration from environment
        self.milvus_host = os.getenv("MILVUS_HOST", "milvus")
        self.milvus_port = int(os.getenv("MILVUS_PORT", "19530"))
        self.collection_name = os.getenv("COLLECTION_NAME", "enterprise_docs")
        self.embedding_model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-base-en")
        self.embedding_dim = int(os.getenv("EMBEDDING_DIM", "768"))
        
        # Initialize components
        self.embedding_model = EmbeddingModel(
            model_name=self.embedding_model_name,
            embedding_dim=self.embedding_dim
        )
        
        self.milvus_client = MilvusClient(
            host=self.milvus_host,
            port=self.milvus_port,
            collection_name=self.collection_name,
            dim=self.embedding_dim
        )
        
        # Connect to Milvus
        self.milvus_client.connect()
        logger.info(" IngestionPipeline initialized successfully")
    
    def chunk_text(
        self, 
        text: str, 
        max_chars: int = 3000, 
        overlap: int = 500
    ) -> List[str]:
        """
        Split text into overlapping chunks for better context preservation
        
        Args:
            text: Text to chunk
            max_chars: Maximum characters per chunk
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List of text chunks
        """
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Get chunk from start to start + max_chars
            end = start + max_chars
            
            # If not the last chunk, try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings (., !, ?, \n\n)
                sentence_ends = [
                    text.rfind('. ', start, end),
                    text.rfind('! ', start, end),
                    text.rfind('? ', start, end),
                    text.rfind('\n\n', start, end)
                ]
                
                # Use the last sentence boundary found
                best_end = max(sentence_ends)
                if best_end > start:
                    end = best_end + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start forward with overlap
            start = end - overlap if end < len(text) else end
        
        return chunks if chunks else [text[:max_chars]]
    
    def process_document(
        self, 
        file_path: str, 
        title: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process a single document: read, chunk, embed, and insert into Milvus
        
        Args:
            file_path: Path to the document file
            title: Document title (defaults to filename)
            metadata: Additional metadata to store
            
        Returns:
            Dictionary with processing results
        """
        start_time = time.time()
        
        try:
            logger.info(f" Starting ingestion for: {file_path}")
            
            # Validate file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                raise ValueError(f"File is empty: {file_path}")
            
            logger.info(f" Read {len(content)} characters from {file_path}")
            
            # Generate title if not provided
            if not title:
                title = os.path.basename(file_path)
            
            # Chunk the document
            chunks = self.chunk_text(content)
            logger.info(f"  Split into {len(chunks)} chunks")
            
            # Prepare titles for chunks
            titles = []
            texts = []
            
            for i, chunk in enumerate(chunks, 1):
                if len(chunks) > 1:
                    chunk_title = f"{title} (Part {i}/{len(chunks)})"
                else:
                    chunk_title = title
                
                titles.append(chunk_title)
                texts.append(chunk)
            
            # Generate embeddings
            logger.info(f" Generating embeddings for {len(chunks)} chunks...")
            embeddings = self.embedding_model.embed_texts(texts)
            logger.info(f" Generated {len(embeddings)} embeddings")
            
            # Insert into Milvus
            logger.info(f" Inserting {len(chunks)} chunks into Milvus...")
            self.milvus_client.insert(titles, texts, embeddings)
            
            elapsed = time.time() - start_time
            
            result = {
                "status": "success",
                "file_path": file_path,
                "title": title,
                "chunks": len(chunks),
                "total_characters": len(content),
                "elapsed_seconds": round(elapsed, 2),
                "message": f" Successfully ingested: {title}"
            }
            
            logger.info(f" Ingestion complete for {title} in {elapsed:.2f}s")
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = f" Ingestion failed for {file_path}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            return {
                "status": "failed",
                "file_path": file_path,
                "title": title,
                "error": str(e),
                "elapsed_seconds": round(elapsed, 2),
                "message": error_msg
            }


# Job function that RQ will call
def ingest_document_job(file_path: str, title: str = None, metadata: Dict[str, Any] = None):
    """
    RQ job function for document ingestion
    This function is called by the worker when processing jobs
    
    Args:
        file_path: Path to document file
        title: Optional document title
        metadata: Optional metadata dictionary
        
    Returns:
        Processing result dictionary
    """
    pipeline = IngestionPipeline()
    result = pipeline.process_document(file_path, title, metadata)
    
    # Log result
    if result["status"] == "success":
        logger.info(f" Job completed: {result['message']}")
    else:
        logger.error(f" Job failed: {result['message']}")
    
    return result


def ingest_url_job(url: str, title: str = None, metadata: Dict[str, Any] = None):
    """
    RQ job function for URL-based document ingestion (e.g., Confluence pages)
    Fetches content from URL and processes it
    
    Args:
        url: URL to fetch content from
        title: Optional document title
        metadata: Optional metadata dictionary
        
    Returns:
        Processing result dictionary
    """
    pipeline = IngestionPipeline()
    
    try:
        logger.info(f" Fetching content from URL: {url}")
        
        # Fetch content from URL
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # For now, treat it as text content
        # In production, you'd parse HTML, extract Confluence content, etc.
        content = response.text
        
        # Save temporarily for processing
        temp_dir = "/tmp/url_ingestion"
        Path(temp_dir).mkdir(parents=True, exist_ok=True)
        
        # Create safe filename from title or URL
        safe_title = title or url.split("/")[-1] or "untitled"
        safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in safe_title)
        temp_file = os.path.join(temp_dir, f"{safe_title}.txt")
        
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Add URL to metadata
        if metadata is None:
            metadata = {}
        metadata["source_url"] = url
        metadata["fetch_method"] = "direct_http"
        
        # Process the document
        result = pipeline.process_document(temp_file, title, metadata)
        
        # Clean up temp file
        try:
            os.remove(temp_file)
        except Exception as e:
            logger.warning(f"Could not remove temp file {temp_file}: {e}")
        
        # Log result
        if result["status"] == "success":
            logger.info(f" URL job completed: {result['message']}")
        else:
            logger.error(f" URL job failed: {result['message']}")
        
        return result
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to fetch URL {url}: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "failed",
            "url": url,
            "title": title or "Unknown",
            "error": error_msg,
            "message": error_msg
        }
    except Exception as e:
        error_msg = f"Error processing URL {url}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "failed",
            "url": url,
            "title": title or "Unknown",
            "error": str(e),
            "message": error_msg
        }

