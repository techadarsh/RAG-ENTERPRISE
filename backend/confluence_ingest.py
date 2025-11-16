"""
Confluence Ingestion Module - POC + API-Ready
Supports local mode (reading .txt files) and API mode (Confluence Cloud REST API)
"""
import os
import logging
import base64
from typing import List, Dict, Optional
from dotenv import load_dotenv

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logging.warning("requests library not available - API mode will not work")

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
        Fetch pages from Confluence REST API
        
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
        if not REQUESTS_AVAILABLE:
            logger.error("requests library not installed. Run: pip install requests")
            return []
        
        if not self.base_url or not self.api_token:
            logger.warning("Confluence API credentials not configured. Set CONFLUENCE_BASE_URL and CONFLUENCE_API_TOKEN")
            return []
        
        pages = []
        
        try:
            # Prepare authentication
            auth_string = f"{self.user_email}:{self.api_token}"
            auth_bytes = auth_string.encode('utf-8')
            auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
            
            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # API endpoint
            url = f"{self.base_url}/wiki/rest/api/content"
            params = {
                "spaceKey": self.space_key,
                "expand": "body.storage,version",
                "limit": 100,  # Fetch up to 100 pages
                "type": "page"  # Only fetch pages, not blog posts
            }
            
            logger.info(f"📡 Fetching pages from Confluence space: {self.space_key}")
            logger.info(f"   API URL: {url}")
            
            # Make API request
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                
                logger.info(f"✅ Successfully fetched {len(results)} pages from Confluence API")
                
                for result in results:
                    # Extract page data
                    page = {
                        "id": result.get("id", ""),
                        "title": result.get("title", "Untitled"),
                        "body": result.get("body", {}).get("storage", {}).get("value", ""),
                        "version": result.get("version", {}).get("number", 1),
                        "url": f"{self.base_url}/wiki{result.get('_links', {}).get('webui', '')}"
                    }
                    pages.append(page)
                    logger.debug(f"   - {page['title']} (ID: {page['id']}, v{page['version']})")
                
                # Check if there are more pages (pagination)
                if data.get("_links", {}).get("next"):
                    logger.info(f"⚠️  More pages available (pagination not implemented)")
                    
            elif response.status_code == 401:
                logger.error("❌ Confluence API authentication failed. Check CONFLUENCE_USER_EMAIL and CONFLUENCE_API_TOKEN")
            elif response.status_code == 404:
                logger.error(f"❌ Confluence space '{self.space_key}' not found")
            else:
                logger.error(f"❌ Confluence API error: {response.status_code} - {response.text}")
                
        except requests.exceptions.Timeout:
            logger.error("❌ Confluence API request timed out after 30 seconds")
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Cannot connect to Confluence at {self.base_url}")
        except Exception as e:
            logger.error(f"❌ Error fetching from Confluence API: {e}")
        
        return pages
    
    def fetch_page_by_id(self, page_id: str) -> Dict[str, str]:
        """
        Fetch a specific page by ID from Confluence API
        
        API Endpoint:
            GET https://<site>.atlassian.net/wiki/rest/api/content/{page_id}?expand=body.storage
        
        Args:
            page_id: Confluence page ID
            
        Returns:
            Page dictionary or empty dict if not found
        """
        if not REQUESTS_AVAILABLE:
            logger.error("requests library not installed. Run: pip install requests")
            return {}
        
        if not self.base_url or not self.api_token:
            logger.warning("Confluence API credentials not configured")
            return {}
        
        try:
            # Prepare authentication
            auth_string = f"{self.user_email}:{self.api_token}"
            auth_bytes = auth_string.encode('utf-8')
            auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
            
            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # API endpoint for specific page
            url = f"{self.base_url}/wiki/rest/api/content/{page_id}"
            params = {
                "expand": "body.storage,version"
            }
            
            logger.info(f"📡 Fetching Confluence page ID: {page_id}")
            
            # Make API request
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                page = {
                    "id": result.get("id", ""),
                    "title": result.get("title", "Untitled"),
                    "body": result.get("body", {}).get("storage", {}).get("value", ""),
                    "version": result.get("version", {}).get("number", 1),
                    "url": f"{self.base_url}/wiki{result.get('_links', {}).get('webui', '')}"
                }
                
                logger.info(f"✅ Successfully fetched page: {page['title']}")
                return page
                
            elif response.status_code == 404:
                logger.error(f"❌ Page with ID '{page_id}' not found")
            else:
                logger.error(f"❌ Confluence API error: {response.status_code} - {response.text}")
                
        except requests.exceptions.Timeout:
            logger.error("❌ Confluence API request timed out after 30 seconds")
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Cannot connect to Confluence at {self.base_url}")
        except Exception as e:
            logger.error(f"❌ Error fetching page {page_id}: {e}")
        
        return {}


    def fetch_all_pages_with_pagination(self, limit_per_request: int = 25, max_pages: int = 500) -> List[Dict[str, str]]:
        """
        Fetch all pages from Confluence with pagination support
        
        Args:
            limit_per_request: Number of pages per API request (max 100)
            max_pages: Maximum total pages to fetch
            
        Returns:
            List of all page dictionaries
        """
        if not REQUESTS_AVAILABLE:
            logger.error("requests library not installed")
            return []
        
        if not self.base_url or not self.api_token:
            logger.warning("Confluence API credentials not configured")
            return []
        
        all_pages = []
        start = 0
        
        try:
            auth_string = f"{self.user_email}:{self.api_token}"
            auth_bytes = auth_string.encode('utf-8')
            auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
            
            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            url = f"{self.base_url}/wiki/rest/api/content"
            
            logger.info(f"📡 Fetching all pages from Confluence space: {self.space_key} (with pagination)")
            
            while len(all_pages) < max_pages:
                params = {
                    "spaceKey": self.space_key,
                    "expand": "body.storage,version",
                    "limit": limit_per_request,
                    "start": start,
                    "type": "page"
                }
                
                response = requests.get(url, headers=headers, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    
                    if not results:
                        logger.info(f"✅ No more pages to fetch")
                        break
                    
                    for result in results:
                        page = {
                            "id": result.get("id", ""),
                            "title": result.get("title", "Untitled"),
                            "body": result.get("body", {}).get("storage", {}).get("value", ""),
                            "version": result.get("version", {}).get("number", 1),
                            "url": f"{self.base_url}/wiki{result.get('_links', {}).get('webui', '')}"
                        }
                        all_pages.append(page)
                    
                    logger.info(f"   Fetched {len(results)} pages (total: {len(all_pages)})")
                    
                    # Check if there are more pages
                    size = data.get("size", 0)
                    if size < limit_per_request:
                        logger.info(f"✅ Reached end of results")
                        break
                    
                    start += limit_per_request
                    
                else:
                    logger.error(f"❌ API error: {response.status_code}")
                    break
            
            logger.info(f"✅ Total pages fetched: {len(all_pages)}")
            return all_pages
            
        except Exception as e:
            logger.error(f"❌ Error during pagination: {e}")
            return all_pages


    def search_pages(self, query: str, limit: int = 20) -> List[Dict[str, str]]:
        """
        Search for pages in Confluence using CQL (Confluence Query Language)
        
        Args:
            query: Search query text
            limit: Maximum number of results
            
        Returns:
            List of matching page dictionaries
        """
        if not REQUESTS_AVAILABLE:
            logger.error("requests library not installed")
            return []
        
        if not self.base_url or not self.api_token:
            logger.warning("Confluence API credentials not configured")
            return []
        
        try:
            auth_string = f"{self.user_email}:{self.api_token}"
            auth_bytes = auth_string.encode('utf-8')
            auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
            
            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Use CQL for search
            url = f"{self.base_url}/wiki/rest/api/content/search"
            cql = f"type=page and space={self.space_key} and text~\"{query}\""
            
            params = {
                "cql": cql,
                "expand": "body.storage,version",
                "limit": limit
            }
            
            logger.info(f"🔍 Searching Confluence for: '{query}'")
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                
                pages = []
                for result in results:
                    page = {
                        "id": result.get("id", ""),
                        "title": result.get("title", "Untitled"),
                        "body": result.get("body", {}).get("storage", {}).get("value", ""),
                        "version": result.get("version", {}).get("number", 1),
                        "url": f"{self.base_url}/wiki{result.get('_links', {}).get('webui', '')}"
                    }
                    pages.append(page)
                
                logger.info(f"✅ Found {len(pages)} matching pages")
                return pages
            else:
                logger.error(f"❌ Search API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error during search: {e}")
            return []


# Example usage for testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test local mode
    ingestor = ConfluenceIngestor(mode="local")
    docs = ingestor.get_documents()
    print(f"\nFetched {len(docs)} documents:")
    for doc in docs:
        print(f"  - {doc['title']} (id: {doc['id']})")
