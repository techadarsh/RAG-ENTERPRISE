#!/usr/bin/env python3
"""
Quick Confluence API Connection Test
"""
import os
import base64
import requests
from dotenv import load_dotenv

# Load .env.local
load_dotenv('.env.local', override=True)

# Get credentials
BASE_URL = os.getenv("CONFLUENCE_BASE_URL", "")
USER_EMAIL = os.getenv("CONFLUENCE_USER_EMAIL", "")
API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN", "")
SPACE_KEY = os.getenv("CONFLUENCE_SPACE_KEY", "BITSWILP")

print("🔍 Testing Confluence API Connection")
print("=" * 60)
print(f"Base URL: {BASE_URL}")
print(f"Email: {USER_EMAIL}")
print(f"Space Key: {SPACE_KEY}")
print(f"API Token: {'*' * 20}...{API_TOKEN[-4:] if API_TOKEN else 'NOT SET'}")
print("=" * 60)
print()

if not BASE_URL or not USER_EMAIL or not API_TOKEN:
    print("❌ Missing credentials! Please set in .env.local:")
    print("   - CONFLUENCE_BASE_URL")
    print("   - CONFLUENCE_USER_EMAIL")
    print("   - CONFLUENCE_API_TOKEN")
    exit(1)

# Create auth header
auth_string = f"{USER_EMAIL}:{API_TOKEN}"
auth_bytes = auth_string.encode('utf-8')
auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')

headers = {
    "Authorization": f"Basic {auth_b64}",
    "Accept": "application/json"
}

# Test 1: Check API connectivity
print("Test 1: Testing basic API connectivity...")
try:
    # First, try to get the space info
    space_url = f"{BASE_URL}/rest/api/space/{SPACE_KEY}"
    print(f"   URL: {space_url}")
    
    response = requests.get(space_url, headers=headers, timeout=10)
    
    if response.status_code == 200:
        space_data = response.json()
        print(f"   ✅ Space found: {space_data.get('name', 'Unknown')}")
        print(f"   Space ID: {space_data.get('id', 'Unknown')}")
        print(f"   Space Key: {space_data.get('key', 'Unknown')}")
    elif response.status_code == 401:
        print("   ❌ Authentication failed!")
        print("   Check your CONFLUENCE_USER_EMAIL and CONFLUENCE_API_TOKEN")
        print(f"   Response: {response.text[:200]}")
    elif response.status_code == 404:
        print(f"   ❌ Space '{SPACE_KEY}' not found!")
        print("   Let's list all available spaces...")
        
        # List all spaces
        all_spaces_url = f"{BASE_URL}/rest/api/space"
        spaces_response = requests.get(all_spaces_url, headers=headers, timeout=10)
        
        if spaces_response.status_code == 200:
            spaces_data = spaces_response.json()
            results = spaces_data.get('results', [])
            print(f"\n   Available spaces ({len(results)}):")
            for space in results:
                print(f"      - {space.get('key', 'N/A')}: {space.get('name', 'N/A')}")
            
            if results:
                print(f"\n   💡 Tip: Update CONFLUENCE_SPACE_KEY in .env.local to one of these keys")
        else:
            print(f"   ❌ Could not list spaces: {spaces_response.status_code}")
            print(f"   Response: {spaces_response.text[:200]}")
    else:
        print(f"   ❌ Error: {response.status_code}")
        print(f"   Response: {response.text[:500]}")
        
except requests.exceptions.Timeout:
    print("   ❌ Request timed out after 10 seconds")
except requests.exceptions.ConnectionError:
    print(f"   ❌ Cannot connect to {BASE_URL}")
    print("   Check if the URL is correct and you have internet connection")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()
print("=" * 60)

# Test 2: Try to fetch pages (if space exists)
print("\nTest 2: Attempting to fetch pages from space...")
try:
    content_url = f"{BASE_URL}/rest/api/content"
    params = {
        "spaceKey": SPACE_KEY,
        "limit": 5,
        "expand": "body.storage,version,space"
    }
    
    print(f"   URL: {content_url}")
    print(f"   Params: {params}")
    
    response = requests.get(content_url, headers=headers, params=params, timeout=15)
    
    if response.status_code == 200:
        data = response.json()
        results = data.get('results', [])
        print(f"   ✅ Found {len(results)} pages")
        
        for page in results:
            print(f"      - {page.get('title', 'Untitled')} (ID: {page.get('id', 'N/A')})")
    elif response.status_code == 404:
        print(f"   ❌ Space '{SPACE_KEY}' not found")
    else:
        print(f"   ❌ Error: {response.status_code}")
        print(f"   Response: {response.text[:300]}")
        
except Exception as e:
    print(f"   ❌ Error: {e}")

print()
print("=" * 60)
print("Test complete!")
