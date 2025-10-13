"""
RAG Pipeline orchestrating embeddings, vector search, and LLM
"""
import logging
import os
import glob
import time
from typing import Dict, Any, List
from embeddings import EmbeddingModel
from milvus_client import MilvusClient
from llm_client import LLMClient

logger = logging.getLogger(__name__)


class RAGPipeline:
    def __init__(
        self,
        milvus_host: str,
        milvus_port: int,
        collection_name: str,
        embedding_model: str,
        embedding_dim: int,
        llm_mode: str,
        mistral_api_key: str = None,
        mistral_api_url: str = None,
        data_dir: str = None,
        confluence_docs: List[Dict[str, str]] = None
    ):
        """Initialize RAG Pipeline"""
        logger.info("Initializing RAG Pipeline")
        
        # Initialize components
        self.embedding_model = EmbeddingModel(model_name=embedding_model, embedding_dim=embedding_dim)
        self.milvus_client = MilvusClient(
            host=milvus_host,
            port=milvus_port,
            collection_name=collection_name,
            dim=embedding_dim
        )
        self.llm_client = LLMClient()
        self.data_dir = data_dir
        self.confluence_docs = confluence_docs or []
        
                # Will store document topics dynamically
        self.document_topics = []
        
        # Connect to Milvus
        self.milvus_client.connect()
        
        # Check if data loading needed but DON'T load during init (let background task handle it)
        self.needs_data_loading = self.milvus_client.is_empty() and (data_dir or self.confluence_docs)
        
        if self.needs_data_loading:
            logger.info("⏸️  Collection is empty - data loading deferred to background task")
        else:
            # Extract document topics if data already exists
            self._extract_document_topics()
    
    def load_data_if_needed(self):
        """
        Load initial SAMPLE documents if collection is empty (called from background task)
        
        NOTE: This is for the INITIAL KNOWLEDGE BASE (17 sample Confluence documents).
        For NEW document uploads during runtime, use the async ingestion API:
            - POST /api/ingest/upload
            - Status tracking via /api/ingest/status/{job_id}
        
        This ensures the system has a working knowledge base on first startup
        while all production document ingestion uses the proper async pipeline.
        """
        if self.needs_data_loading:
            logger.info("📥 Loading initial SAMPLE knowledge base in background...")
            logger.info("💡 For new documents, use: POST /api/ingest/upload")
            self._load_initial_data()
            self._extract_document_topics()
            self.needs_data_loading = False
            logger.info("✅ Background data loading complete")
    
    def _clean_title_for_display(self, title: str) -> str:
        """
        Clean document title for user-friendly display
        - Remove chunk numbers like (Part 11/11)
        - Remove [Confluence] prefix
        - Remove file extensions
        """
        clean_title = title.replace('.txt', '').replace('[Confluence] ', '')
        # Remove "Part X/Y" suffix
        if ' (Part ' in clean_title:
            clean_title = clean_title.split(' (Part ')[0]
        return clean_title.strip()
    
    def _extract_document_topics(self):
        """
        Extract unique document topics/titles from the knowledge base
        to dynamically generate scope messages
        """
        logger.info("Starting document topic extraction...")
        try:
            # Get all documents from Milvus
            all_docs = self.milvus_client.get_all_documents()
            logger.info(f"Retrieved {len(all_docs) if all_docs else 0} documents from Milvus")
            
            if not all_docs:
                logger.warning("No documents found in collection")
                self.document_topics = ["company documentation"]
                return
            
            # Extract unique titles and clean them
            titles = set()
            for doc in all_docs:
                title = doc.get('title', '')
                if title:
                    clean_title = self._clean_title_for_display(title)
                    titles.add(clean_title)
            
            # Sort and store
            self.document_topics = sorted(list(titles))
            logger.info(f"📚 Extracted {len(self.document_topics)} document topics: {', '.join(self.document_topics[:5])}{'...' if len(self.document_topics) > 5 else ''}")
            
        except Exception as e:
            logger.error(f"Error extracting document topics: {e}")
            self.document_topics = ["company documentation"]
    
    def get_scope_description(self) -> str:
        """
        Generate a dynamic description of what topics the chatbot can answer about
        
        Returns:
            Human-readable string describing the knowledge base scope
        """
        if not self.document_topics:
            return "company documentation"
        
        if len(self.document_topics) == 1:
            return self.document_topics[0]
        elif len(self.document_topics) == 2:
            return f"{self.document_topics[0]} and {self.document_topics[1]}"
        else:
            # Join all but last with commas, add "and" before last
            return f"{', '.join(self.document_topics[:-1])}, and {self.document_topics[-1]}"
    
    def _chunk_text(self, text: str, max_length: int = 3000, overlap: int = 500) -> List[str]:
        """
        Split text into chunks if it exceeds max_length.
        Tries to split on paragraphs first, then sentences.
        
        Args:
            text: Text to chunk
            max_length: Maximum characters per chunk
            
        Returns:
            List of text chunks
        """
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        # Split by double newlines (paragraphs) first
        paragraphs = text.split('\n\n')
        current_chunk = ""
        
        for para in paragraphs:
            # If single paragraph is too large, split further
            if len(para) > max_length:
                # If current chunk has content, save it
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # Split large paragraph by sentences
                sentences = para.split('. ')
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) + 2 <= max_length:
                        current_chunk += sentence + '. '
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence + '. '
            
            # Add paragraph to current chunk if it fits
            elif len(current_chunk) + len(para) + 2 <= max_length:
                current_chunk += para + '\n\n'
            else:
                # Save current chunk and start new one
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + '\n\n'
        
        # Add remaining content
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text[:max_length]]
    
    def _load_initial_data(self):
        """
        Load and index SAMPLE documents from data directory and Confluence
        
        IMPORTANT: This method is ONLY for initial knowledge base loading on startup.
        For runtime document ingestion, use the async ingestion API instead.
        
        This method loads:
        - Confluence sample documents (17 enterprise docs)
        - Any .txt files in DATA_DIR
        
        For NEW documents during production:
        - Use POST /api/ingest/upload (async processing)
        - Do NOT add files to data/ directory
        """
        titles = []
        texts = []
        
        # Load Confluence documents first (with chunking)
        if self.confluence_docs:
            logger.info(f"Loading {len(self.confluence_docs)} Confluence documents")
            for doc in self.confluence_docs:
                doc_chunks = self._chunk_text(doc['body'])
                
                if len(doc_chunks) > 1:
                    logger.info(f"Split '{doc['title']}' into {len(doc_chunks)} chunks")
                    for i, chunk in enumerate(doc_chunks, 1):
                        titles.append(f"[Confluence] {doc['title']} (Part {i}/{len(doc_chunks)})")
                        texts.append(chunk)
                else:
                    titles.append(f"[Confluence] {doc['title']}")
                    texts.append(doc['body'])
        
        # Load local text files from data directory (with chunking)
        if self.data_dir and os.path.exists(self.data_dir):
            txt_files = glob.glob(os.path.join(self.data_dir, "*.txt"))
            
            for file_path in txt_files:
                filename = os.path.basename(file_path)
                logger.info(f"Reading file: {filename}")
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        
                        if content:
                            doc_chunks = self._chunk_text(content)
                            
                            if len(doc_chunks) > 1:
                                logger.info(f"Split '{filename}' into {len(doc_chunks)} chunks")
                                for i, chunk in enumerate(doc_chunks, 1):
                                    titles.append(f"{filename} (Part {i}/{len(doc_chunks)})")
                                    texts.append(chunk)
                            else:
                                titles.append(filename)
                                texts.append(content)
                except Exception as e:
                    logger.error(f"Error reading file {filename}: {e}")
        
        if not texts:
            logger.warning("No content found in data files or Confluence")
            return
        
        # Generate embeddings
        logger.info(f"📊 Starting embedding generation for {len(texts)} document chunks...")
        logger.info(f"⏱️  This may take 1-2 minutes on first run...")
        
        start_time = time.time()
        embeddings = self.embedding_model.embed_texts(texts)
        elapsed = time.time() - start_time
        
        logger.info(f"✅ Embedding generation completed in {elapsed:.1f}s")
        
        # Insert into Milvus
        logger.info(f"💾 Inserting {len(texts)} documents into Milvus...")
        self.milvus_client.insert(titles, texts, embeddings)
        logger.info(f"✅ Loaded {len(texts)} document chunks into Milvus")
    
    def query(self, query: str, top_k: int = None) -> Dict[str, Any]:
        """
        Process a query through the RAG pipeline
        
        Args:
            query: User query string
            top_k: Number of documents to retrieve (defaults to RETRIEVAL_TOP_K env var)
            
        Returns:
            Dictionary with answer, sources, and metadata
        """
        # Read top_k from environment if not provided
        if top_k is None:
            top_k = int(os.getenv("RETRIEVAL_TOP_K", "3"))
        
        logger.info(f"Processing query: {query}")
        
        # 1. Embed query
        query_vector = self.embedding_model.embed_query(query)
        
        # 2. Search in Milvus (fetch top_k for context, show top 3 in response)
        results = self.milvus_client.search(query_vector, top_k=top_k)
        
        if not results:
            return {
                "answer": "I don't have information about that in my knowledge base. Please try rephrasing your question or ask about our available documentation.",
                "sources": [],
                "context": ""
            }
        
        # 3. Check relevance - if top result has very low score, question is likely out of scope
        RELEVANCE_THRESHOLD = 0.02  # Lowered for hash embeddings (2%) - LLM will do final filtering
        top_score = float(results[0]['score'])
        
        if top_score < RELEVANCE_THRESHOLD:
            logger.info(f"Query relevance too low (score: {top_score:.4f}). Rejecting out-of-scope question.")
            scope = self.get_scope_description()
            return {
                "answer": f"I can only answer questions about {scope}. Please ask about topics covered in our documentation.",
                "sources": [],
                "context": ""
            }
        
        # 4. Combine retrieved texts as context (use all for LLM, show only top 3 in response)
        context_parts = []
        sources = []
        sources_for_display = []  # Only top 3 for user
        
        # Context compression settings
        MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "2000"))  # ~500 tokens
        MAX_CHUNK_CHARS = int(os.getenv("MAX_CHUNK_CHARS", "800"))  # ~200 tokens per chunk
        
        for i, result in enumerate(results, 1):
            # Trim individual chunks to prevent overly long context
            text = result['text']
            if len(text) > MAX_CHUNK_CHARS:
                text = text[:MAX_CHUNK_CHARS] + "... [truncated]"
            
            context_parts.append(f"[Document {i}: {result['title']}]\n{text}")
            
            # Clean title for user-friendly display
            display_title = self._clean_title_for_display(result['title'])
            
            # Collect all sources for context, but only top 3 for display
            source_obj = {
                "title": display_title,
                "text": result['text'][:200] + "..." if len(result['text']) > 200 else result['text'],
                "score": f"{float(result['score']) * 100:.2f}%"
            }
            sources.append(source_obj)
            
            # Only show top 3 sources to user
            if i <= 3:
                sources_for_display.append(source_obj)
        
        context = "\n\n".join(context_parts)
        
        # Trim total context if still too long
        if len(context) > MAX_CONTEXT_CHARS:
            context = context[:MAX_CONTEXT_CHARS] + "\n\n... [context truncated for performance]"
            logger.info(f"Context trimmed to {MAX_CONTEXT_CHARS} chars for faster LLM generation")
        
        # 5. Generate answer with LLM (with strict prompt to only use context)
        answer = self.llm_client.generate_answer(query, context)
        
        return {
            "answer": answer,
            "sources": sources_for_display,  # Only show top 3 to user
            "context": context
        }
    
    def generate_with_context(self, query: str, history: List[Dict[str, str]], top_k: int = None) -> Dict[str, Any]:
        """
        Process a query through the RAG pipeline with conversation history
        
        Args:
            query: Current user query string
            history: List of previous conversation turns [{"role": "user/assistant", "content": "..."}]
            top_k: Number of documents to retrieve (defaults to RETRIEVAL_TOP_K env var)
            
        Returns:
            Dictionary with answer, sources, and metadata
        """
        # Read top_k from environment if not provided
        if top_k is None:
            top_k = int(os.getenv("RETRIEVAL_TOP_K", "3"))
        
        logger.info(f"Processing query with conversation context: {query}")
        
        # 1. Embed query
        query_vector = self.embedding_model.embed_query(query)
        
        # 2. Search in Milvus (fetch top_k for context, show top 3 in response)
        results = self.milvus_client.search(query_vector, top_k=top_k)
        
        if not results:
            return {
                "answer": "I don't have information about that in my knowledge base. Please try rephrasing your question or ask about our available documentation.",
                "sources": [],
                "context": ""
            }
        
        # 3. Check relevance - if top result has very low score, question is likely out of scope
        RELEVANCE_THRESHOLD = 0.02  # Lowered for hash embeddings (2%) - LLM will do final filtering
        top_score = float(results[0]['score'])
        
        if top_score < RELEVANCE_THRESHOLD:
            logger.info(f"Query relevance too low (score: {top_score:.4f}). Rejecting out-of-scope question.")
            scope = self.get_scope_description()
            return {
                "answer": f"I can only answer questions about {scope}. Please ask about topics covered in our documentation.",
                "sources": [],
                "context": ""
            }
        
        # 4. Combine retrieved texts as context (use all for LLM, show only top 3 in response)
        context_parts = []
        sources_for_display = []  # Only top 3 for user
        
        for i, result in enumerate(results, 1):
            context_parts.append(f"[Document {i}: {result['title']}]\n{result['text']}")
            
            # Clean title for user-friendly display
            display_title = self._clean_title_for_display(result['title'])
            
            # Only show top 3 sources to user
            if i <= 3:
                sources_for_display.append({
                    "title": display_title,
                    "text": result['text'][:200] + "..." if len(result['text']) > 200 else result['text'],
                    "score": f"{float(result['score']) * 100:.2f}%"
                })
        
        context = "\n\n".join(context_parts)
        
        # 5. Build conversation history string
        history_text = "\n".join([
            f"{turn['role'].capitalize()}: {turn['content']}" 
            for turn in history[-6:]  # Last 3 turns (6 messages)
        ])
        
        # 5. Generate answer with LLM using history + context
        answer = self.llm_client.generate_answer_with_history(query, context, history_text)
        
        return {
            "answer": answer,
            "sources": sources_for_display,  # Only show top 3 to user
            "context": context
        }
