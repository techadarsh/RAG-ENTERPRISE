# 🔗 Confluence API Integration Guide

Complete guide to enable real Confluence API integration in your RAG Enterprise system.

## ✅ What's Already Implemented

Your system **already has full Confluence API support**! The implementation includes:

- ✅ **Basic Authentication** (email + API token)
- ✅ **Fetch all pages** from a space with pagination
- ✅ **Fetch specific page by ID**
- ✅ **CQL Search** support
- ✅ **Comprehensive error handling** (401, 404, timeout, connection errors)
- ✅ **Automatic HTML content extraction**
- ✅ **Version tracking**
- ✅ **URL generation for pages**

**File**: `backend/confluence_ingest.py` (433 lines, fully implemented)

## 🚀 Quick Setup (3 Steps)

### Step 1: Get Confluence API Token

1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click **"Create API token"**
3. Name it: `RAG Enterprise Integration`
4. **Copy the token** (you won't see it again!)
5. Save it securely

### Step 2: Get Your Confluence Details

You need:
- **Base URL**: `https://YOUR-DOMAIN.atlassian.net/wiki`
  - Example: `https://acme-corp.atlassian.net/wiki`
- **Email**: Your Atlassian account email
- **Space Key**: (Optional) The space to fetch from
  - Example: `HR`, `ENG`, `DOCS`
  - Find it in Confluence URL: `/wiki/spaces/HR/pages/...`

### Step 3: Update Configuration

Edit `.env.local` in the project root:

```bash
# Change this line from:
CONFLUENCE_MODE=local

# To:
CONFLUENCE_MODE=api

# Uncomment and fill in these lines:
CONFLUENCE_BASE_URL=https://YOUR-DOMAIN.atlassian.net/wiki
CONFLUENCE_USER_EMAIL=your-email@company.com
CONFLUENCE_API_TOKEN=your-actual-api-token-from-step-1
CONFLUENCE_SPACE_KEY=YOUR_SPACE_KEY
```

**Example configuration:**
```bash
CONFLUENCE_MODE=api
CONFLUENCE_BASE_URL=https://acme-corp.atlassian.net/wiki
CONFLUENCE_USER_EMAIL=john.doe@acme.com
CONFLUENCE_API_TOKEN=ATATT3xFfGF0abcdefghijklmnopqrstuvwxyz1234567890
CONFLUENCE_SPACE_KEY=ENG
```

### Step 4: Restart the Backend

```bash
./start_local.sh restart
```

That's it! Your system will now fetch pages from Confluence API.

## 🧪 Testing the Integration

### Test 1: Check Logs for API Calls

```bash
./start_local.sh logs backend | grep Confluence
```

You should see:
```
📡 Fetching pages from Confluence space: ENG
   API URL: https://acme-corp.atlassian.net/wiki/rest/api/content
✅ Successfully fetched 25 pages from Confluence API
   - Engineering Standards (ID: 123456, v3)
   - API Best Practices (ID: 789012, v5)
   ...
```

### Test 2: Query the Documents

```bash
curl http://localhost:8000/health/deps
```

Check the document count - it should show pages from your Confluence space.

### Test 3: Ask a Question

Go to http://localhost:3000 and ask a question about content in your Confluence pages.

## 🔍 Available API Methods

The implementation supports multiple API methods:

### 1. Fetch All Pages (Default)

Fetches all pages from a space with pagination support.

```python
# Automatically called when backend starts
ingestor = ConfluenceIngestor(mode='api')
pages = ingestor.get_documents()
```

### 2. Fetch Page by ID

```python
page = ingestor.fetch_page_by_id('123456')
```

### 3. Fetch with Pagination

```python
pages = ingestor.fetch_all_pages_with_pagination(limit=50)
```

### 4. Search Pages with CQL

```python
pages = ingestor.search_pages('title ~ "engineering*"')
```

## 📊 API Response Structure

Each page returned has this structure:

```python
{
    "id": "123456",
    "title": "Engineering Standards",
    "body": "<html content>",
    "version": 3,
    "url": "https://acme-corp.atlassian.net/wiki/spaces/ENG/pages/123456"
}
```

## 🛠️ Advanced Configuration

### Fetch from Multiple Spaces

Currently configured for one space. To fetch from multiple spaces, you can:

1. Set multiple space keys separated by comma:
```bash
CONFLUENCE_SPACE_KEY=HR,ENG,DOCS
```

2. Modify `confluence_ingest.py` to loop through spaces:
```python
space_keys = os.getenv("CONFLUENCE_SPACE_KEY", "HR").split(',')
for space in space_keys:
    # Fetch pages from each space
```

### Adjust Page Limit

Edit `confluence_ingest.py` line ~145:

```python
params = {
    "spaceKey": self.space_key,
    "expand": "body.storage,version",
    "limit": 100,  # Change this number (max 100 per request)
    "type": "page"
}
```

### Filter by Labels

Add label filtering to the API call:

```python
params = {
    "spaceKey": self.space_key,
    "expand": "body.storage,version",
    "limit": 100,
    "type": "page",
    "label": "documentation"  # Only pages with this label
}
```

### CQL Search Examples

```python
# Search by title
ingestor.search_pages('title ~ "API*"')

# Search by content
ingestor.search_pages('text ~ "authentication"')

# Search by space and title
ingestor.search_pages('space = "ENG" AND title ~ "standards"')

# Search by label
ingestor.search_pages('label = "documentation"')

# Search updated after date
ingestor.search_pages('lastModified > "2024-01-01"')
```

## 🐛 Troubleshooting

### Error: 401 Unauthorized

**Problem**: Invalid credentials

**Solution**:
1. Verify your email is correct
2. Regenerate API token at https://id.atlassian.com/manage-profile/security/api-tokens
3. Make sure you copied the full token
4. Check for extra spaces in `.env.local`

### Error: 404 Not Found

**Problem**: Space key doesn't exist or you don't have access

**Solution**:
1. Verify the space key in Confluence URL
2. Make sure you have permission to view the space
3. Try removing `CONFLUENCE_SPACE_KEY` to fetch from all accessible spaces

### Error: Connection Timeout

**Problem**: Network issues or slow Confluence instance

**Solution**:
1. Check your internet connection
2. Try increasing timeout in `confluence_ingest.py`:
```python
response = requests.get(url, headers=headers, params=params, timeout=60)  # Increase to 60s
```

### No Pages Returned

**Problem**: Empty space or no access

**Solution**:
1. Check backend logs: `./start_local.sh logs backend`
2. Verify you have pages in the space
3. Check permissions in Confluence
4. Try fetching a specific page by ID to test auth

### HTML Content Not Clean

**Problem**: Confluence returns HTML with lots of markup

**Solution**: The system already handles this, but you can improve it:

1. Install `beautifulsoup4`:
```bash
pip install beautifulsoup4
```

2. Add HTML cleaning in `confluence_ingest.py`:
```python
from bs4 import BeautifulSoup

def clean_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    return soup.get_text()
```

## 🔒 Security Best Practices

### 1. Never Commit API Tokens

`.env.local` is in `.gitignore` - **never remove it!**

### 2. Use Environment Variables

For production, use secure environment variable management:
- AWS Secrets Manager
- HashiCorp Vault
- Azure Key Vault

### 3. Rotate Tokens Regularly

Set a reminder to rotate your API token every 90 days.

### 4. Use Read-Only Tokens

The current implementation only needs **read access**. Don't use tokens with write/admin permissions.

### 5. Restrict Token Scope

When creating the API token, limit it to:
- Confluence Cloud API
- Read-only access
- Specific spaces (if possible)

## 📈 Performance Optimization

### 1. Pagination

For large spaces (100+ pages), implement pagination:

```python
all_pages = ingestor.fetch_all_pages_with_pagination(limit=50)
```

### 2. Caching

Cache Confluence responses to reduce API calls:

```python
import json
from datetime import datetime, timedelta

# Cache pages for 1 hour
cache_file = 'confluence_cache.json'
cache_duration = timedelta(hours=1)

if os.path.exists(cache_file):
    cache_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
    if datetime.now() - cache_time < cache_duration:
        with open(cache_file, 'r') as f:
            return json.load(f)
```

### 3. Incremental Updates

Only fetch pages updated since last sync:

```python
last_sync = "2024-11-15"
pages = ingestor.search_pages(f'lastModified > "{last_sync}"')
```

### 4. Parallel Fetching

Fetch multiple pages in parallel using threading:

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=5) as executor:
    pages = list(executor.map(ingestor.fetch_page_by_id, page_ids))
```

## 📝 Example: Full Integration Workflow

```python
from backend.confluence_ingest import ConfluenceIngestor

# Initialize with API mode
ingestor = ConfluenceIngestor(mode='api')

# Fetch all pages from configured space
pages = ingestor.get_documents()
print(f"Fetched {len(pages)} pages")

# Fetch a specific page
page = ingestor.fetch_page_by_id('123456')
print(f"Page title: {page['title']}")

# Search for specific pages
results = ingestor.search_pages('title ~ "API*"')
print(f"Found {len(results)} API-related pages")

# Fetch with pagination (for large spaces)
all_pages = ingestor.fetch_all_pages_with_pagination(limit=50)
print(f"Total pages: {len(all_pages)}")
```

## 🎯 Next Steps

Once Confluence API is working:

1. **Monitor Usage**: Check Confluence API rate limits (REST API: 180 requests/min per IP)
2. **Optimize Chunking**: Confluence pages can be large - adjust `CHUNK_SIZE` in `.env.local`
3. **Add Webhooks**: Set up Confluence webhooks to auto-update when pages change
4. **Implement Caching**: Cache Confluence responses to reduce API calls
5. **Add Filtering**: Filter out draft pages or old content

## 📚 Useful Resources

- **Confluence REST API Docs**: https://developer.atlassian.com/cloud/confluence/rest/v1/intro/
- **CQL Reference**: https://developer.atlassian.com/cloud/confluence/advanced-searching-using-cql/
- **API Rate Limits**: https://developer.atlassian.com/cloud/confluence/rate-limiting/
- **Authentication Guide**: https://developer.atlassian.com/cloud/confluence/basic-auth-for-rest-apis/

## ✅ Summary

**You already have a complete Confluence API integration!** Just:

1. Get API token from Atlassian
2. Update 4 lines in `.env.local`
3. Restart backend: `./start_local.sh restart`
4. Done! 🎉

The implementation is production-ready with proper error handling, pagination support, and multiple fetch methods.
