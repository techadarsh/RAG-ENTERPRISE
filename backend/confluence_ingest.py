"""
Confluence Ingestion Module - POC + API-Ready
Supports local mode (reading .txt files) and API mode (stub for future implementation)
"""
import os
import logging
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class ConfluenceIngestor:
    """
    Modular Confluence page ingestion system
    
    Modes:
    - 'local': Read .txt files from data/sample_confluence_pages/
    - 'api': Fetch from Confluence REST API (stub implementation)
    """
    
    def __init__(self, mode: str = None):
        """
        Initialize the Confluence ingestor
        
        Args:
            mode: 'local' or 'api'. If None, reads from CONFLUENCE_MODE env var
        """
        self.mode = mode or os.getenv("CONFLUENCE_MODE", "local")
        self.base_url = os.getenv("CONFLUENCE_BASE_URL", "")
        self.api_token = os.getenv("CONFLUENCE_API_TOKEN", "")
        self.user_email = os.getenv("CONFLUENCE_USER_EMAIL", "")
        self.space_key = os.getenv("CONFLUENCE_SPACE_KEY", "HR")
        self.local_data_dir = os.getenv("CONFLUENCE_LOCAL_DIR", "data/sample_confluence_pages")
        
        logger.info(f"ConfluenceIngestor initialized in '{self.mode}' mode")
    
    def get_documents(self) -> List[Dict[str, str]]:
        """
        Retrieve Confluence pages based on current mode
        
        Returns:
            List of page dictionaries with keys: id, title, body
        """
        if self.mode == "local":
            return self._fetch_local_pages()
        elif self.mode == "api":
            return self._fetch_from_confluence_api()
        else:
            logger.warning(f"Unknown mode '{self.mode}', defaulting to local")
            return self._fetch_local_pages()
    
    def _fetch_local_pages(self) -> List[Dict[str, str]]:
        """
        Read local .txt files from sample_confluence_pages directory
        
        Returns:
            List of page dictionaries
        """
        pages = []
        
        if not os.path.exists(self.local_data_dir):
            logger.warning(f"Local data directory not found: {self.local_data_dir}")
            return pages
        
        txt_files = [f for f in os.listdir(self.local_data_dir) if f.endswith('.txt')]
        
        for filename in txt_files:
            filepath = os.path.join(self.local_data_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Create page dict with Confluence-like structure
                page = {
                    "id": filename.replace('.txt', ''),
                    "title": filename.replace('.txt', '').replace('_', ' ').title(),
                    "body": content
                }
                pages.append(page)
                logger.debug(f"Loaded local page: {page['title']}")
                
            except Exception as e:
                logger.error(f"Error reading {filename}: {e}")
        
        logger.info(f"Loaded {len(pages)} pages from local directory")
        return pages
    
    def _fetch_from_confluence_api(self) -> List[Dict[str, str]]:
        """
        Fetch pages from Confluence REST API (stub implementation)
        
        API Endpoint:
            GET https://<site>.atlassian.net/wiki/rest/api/content
            
        Query Parameters:
            - spaceKey: The space to fetch from (e.g., 'HR', 'ENG')
            - expand: body.storage (to get page content)
            - limit: Number of pages to fetch
            
        Authentication:
            - Basic Auth with email + API token
            - Header: Authorization: Basic base64(email:api_token)
            
        Returns:
            List of page dictionaries
        """
        logger.info(f"TODO: Implement API call to Confluence for space_key={self.space_key}")
        logger.info(f"API Endpoint: {self.base_url}/rest/api/content?spaceKey={self.space_key}&expand=body.storage")
        
        # Stub implementation - returns empty list
        # Future implementation would:
        # 1. Set up authentication headers
        # 2. Make GET request to Confluence API
        # 3. Parse JSON response
        # 4. Extract page id, title, and body.storage.value
        # 5. Return list of page dicts
        
        if not self.base_url or not self.api_token:
            logger.warning("Confluence API credentials not configured. Set CONFLUENCE_BASE_URL and CONFLUENCE_API_TOKEN")
        
        return []
    
    def fetch_page_by_id(self, page_id: str) -> Dict[str, str]:
        """
        Fetch a specific page by ID (stub for API mode)
        
        API Endpoint:
            GET https://<site>.atlassian.net/wiki/rest/api/content/{page_id}?expand=body.storage
        
        Args:
            page_id: Confluence page ID
            
        Returns:
            Page dictionary or empty dict if not found
        """
        logger.info(f"TODO: Implement fetch_page_by_id for page_id={page_id}")
        return {}


# Example usage for testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test local mode
    ingestor = ConfluenceIngestor(mode="local")
    docs = ingestor.get_documents()
    print(f"\nFetched {len(docs)} documents:")
    for doc in docs:
        print(f"  - {doc['title']} (id: {doc['id']})")
