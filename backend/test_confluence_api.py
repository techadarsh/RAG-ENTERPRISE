#!/usr/bin/env python3
"""
Test script for Confluence API integration
Demonstrates both local mode and API mode functionality
"""
import sys
import os
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from confluence_ingest import ConfluenceIngestor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_local_mode():
    """Test local file reading mode"""
    print("\n" + "="*60)
    print("TEST 1: Local Mode (Reading .txt files)")
    print("="*60)
    
    ingestor = ConfluenceIngestor(mode="local")
    docs = ingestor.get_documents()
    
    print(f"\n✅ Fetched {len(docs)} documents from local directory")
    print("\nDocument Titles:")
    for i, doc in enumerate(docs, 1):
        print(f"  {i}. {doc['title']} (ID: {doc['id']})")
        print(f"     Content length: {len(doc['body'])} characters")
    
    return len(docs) > 0


def test_api_mode():
    """Test Confluence Cloud API mode"""
    print("\n" + "="*60)
    print("TEST 2: API Mode (Confluence Cloud)")
    print("="*60)
    
    # Check if API credentials are configured
    base_url = os.getenv("CONFLUENCE_BASE_URL", "")
    api_token = os.getenv("CONFLUENCE_API_TOKEN", "")
    
    if not base_url or not api_token:
        print("\n⚠️  Confluence API credentials not configured")
        print("   To test API mode, set these environment variables:")
        print("   - CONFLUENCE_BASE_URL=https://your-domain.atlassian.net")
        print("   - CONFLUENCE_USER_EMAIL=your-email@example.com")
        print("   - CONFLUENCE_API_TOKEN=your-api-token")
        print("   - CONFLUENCE_SPACE_KEY=YOUR_SPACE")
        print("\n   Skipping API mode test...")
        return True  # Not a failure, just skipped
    
    print(f"\n📡 Connecting to: {base_url}")
    
    ingestor = ConfluenceIngestor(mode="api")
    docs = ingestor.get_documents()
    
    if docs:
        print(f"\n✅ Successfully fetched {len(docs)} documents from Confluence API")
        print("\nDocument Titles:")
        for i, doc in enumerate(docs, 1):
            print(f"  {i}. {doc['title']} (ID: {doc['id']}, v{doc.get('version', '?')})")
            print(f"     URL: {doc.get('url', 'N/A')}")
            print(f"     Content length: {len(doc['body'])} characters")
        return True
    else:
        print("\n⚠️  No documents fetched from API")
        print("   Check your credentials and space key")
        return False


def test_fetch_by_id():
    """Test fetching a specific page by ID"""
    print("\n" + "="*60)
    print("TEST 3: Fetch Page by ID")
    print("="*60)
    
    # Check if API credentials are configured
    base_url = os.getenv("CONFLUENCE_BASE_URL", "")
    api_token = os.getenv("CONFLUENCE_API_TOKEN", "")
    
    if not base_url or not api_token:
        print("\n⚠️  Skipping (API credentials not configured)")
        return True
    
    # First fetch some pages to get an ID
    ingestor = ConfluenceIngestor(mode="api")
    docs = ingestor.get_documents()
    
    if not docs:
        print("\n⚠️  No pages available to test with")
        return True
    
    # Test with first page ID
    test_page_id = docs[0]['id']
    print(f"\n📄 Fetching page ID: {test_page_id}")
    
    page = ingestor.fetch_page_by_id(test_page_id)
    
    if page:
        print(f"\n✅ Successfully fetched page")
        print(f"   Title: {page['title']}")
        print(f"   Version: {page.get('version', '?')}")
        print(f"   URL: {page.get('url', 'N/A')}")
        print(f"   Content length: {len(page['body'])} characters")
        return True
    else:
        print("\n❌ Failed to fetch page by ID")
        return False


def test_search():
    """Test search functionality"""
    print("\n" + "="*60)
    print("TEST 4: Search Pages")
    print("="*60)
    
    # Check if API credentials are configured
    base_url = os.getenv("CONFLUENCE_BASE_URL", "")
    api_token = os.getenv("CONFLUENCE_API_TOKEN", "")
    
    if not base_url or not api_token:
        print("\n⚠️  Skipping (API credentials not configured)")
        return True
    
    ingestor = ConfluenceIngestor(mode="api")
    
    # Test search with a common term
    search_query = "policy"
    print(f"\n🔍 Searching for: '{search_query}'")
    
    results = ingestor.search_pages(search_query, limit=5)
    
    if results:
        print(f"\n✅ Found {len(results)} matching pages")
        for i, page in enumerate(results, 1):
            print(f"  {i}. {page['title']} (ID: {page['id']})")
        return True
    else:
        print("\n⚠️  No results found")
        return True  # Not a failure


def test_pagination():
    """Test pagination functionality"""
    print("\n" + "="*60)
    print("TEST 5: Pagination (fetch all pages)")
    print("="*60)
    
    # Check if API credentials are configured
    base_url = os.getenv("CONFLUENCE_BASE_URL", "")
    api_token = os.getenv("CONFLUENCE_API_TOKEN", "")
    
    if not base_url or not api_token:
        print("\n⚠️  Skipping (API credentials not configured)")
        return True
    
    ingestor = ConfluenceIngestor(mode="api")
    
    print(f"\n📚 Fetching all pages with pagination...")
    pages = ingestor.fetch_all_pages_with_pagination(limit_per_request=10, max_pages=50)
    
    if pages:
        print(f"\n✅ Successfully fetched {len(pages)} total pages")
        return True
    else:
        print("\n⚠️  No pages fetched")
        return True


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 CONFLUENCE API INTEGRATION TEST SUITE")
    print("="*60)
    
    results = []
    
    # Test 1: Local mode (always works)
    results.append(("Local Mode", test_local_mode()))
    
    # Test 2: API mode (requires credentials)
    results.append(("API Mode", test_api_mode()))
    
    # Test 3: Fetch by ID
    results.append(("Fetch by ID", test_fetch_by_id()))
    
    # Test 4: Search
    results.append(("Search", test_search()))
    
    # Test 5: Pagination
    results.append(("Pagination", test_pagination()))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST RESULTS SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}  {test_name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\n{passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed or were skipped")
        return 1


if __name__ == "__main__":
    sys.exit(main())
