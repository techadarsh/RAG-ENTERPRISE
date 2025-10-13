# Shell Script Fixes - Inline Comments Issue

## Problem

After removing emojis from the codebase, the `.env` file gained **inline comments**, which broke shell scripts that load environment variables.

### Root Cause

**Before emoji removal:**
```bash
# .env file
LLM_HOST=rag-ollama
LLM_PORT=11434
```

**After adding proper comments:**
```bash
# .env file
LLM_HOST=rag-ollama             # Docker service name
LLM_PORT=11434                  # Ollama default port
```

**Shell script loading .env:**
```bash
# Old code (BROKEN with inline comments)
export $(grep -v '^#' .env | xargs)
```

**What happened:**
1. `grep -v '^#'` filters lines **starting** with `#`, but not inline comments
2. Result: `LLM_HOST=rag-ollama # Docker service name`
3. Shell tries to execute: `export LLM_HOST=rag-ollama #`
4. Error: `export: '#': not a valid identifier`

The `#` character is interpreted as a separate export argument, causing the error!

---

## Solution

Updated all shell scripts to **strip inline comments** before exporting:

```bash
# New code (FIXED)
export $(grep -v '^#' .env | sed 's/#.*$//' | grep -v '^[[:space:]]*$' | xargs)
```

**Breakdown:**
1. `grep -v '^#' .env` - Skip lines starting with `#` (full-line comments)
2. `sed 's/#.*$//'` - **Strip everything after `#` (inline comments)**
3. `grep -v '^[[:space:]]*$'` - Remove empty lines
4. `xargs` - Convert to arguments for export

**Result:**
```bash
LLM_HOST=rag-ollama             # Docker service name
↓ (after sed)
LLM_HOST=rag-ollama
↓ (clean export)
export LLM_HOST=rag-ollama
```

---

## Files Fixed

### 1. `scripts/dev-mode.sh`
**Changes:**
- ✅ Fixed inline comment handling in `.env` loading
- ✅ Added ingestion service startup
- ✅ Added trigger service startup (with `--profile trigger`)
- ✅ Added service verification after startup
- ✅ Updated help text with ingestion/trigger commands

**New Features:**
```bash
# Start all dev services including ingestion and trigger
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d backend frontend ingestion
docker compose --profile trigger up -d trigger

# Verify services are running
if docker ps --format '{{.Names}}' | grep -q "rag-ingestion"; then
    echo "Ingestion service: Running"
fi
```

### 2. `scripts/dev-up.sh`
**Changes:**
- ✅ Fixed inline comment handling in `.env` loading

---

## Testing

### Test 1: Verify `.env` Loading Works
```bash
cd /Users/adarsharma/Documents/adarsharma/M.tech-4th-sem/rag-enterprise
./scripts/dev-mode.sh
```

**Expected:** No errors about `export: '#': not a valid identifier`

### Test 2: Verify All Services Start
```bash
./scripts/dev-mode.sh

# Check running containers
docker ps --format "table {{.Names}}\t{{.Status}}"
```

**Expected Services:**
- ✅ milvus
- ✅ etcd
- ✅ minio
- ✅ redis
- ✅ rag-ollama
- ✅ rag-backend
- ✅ rag-frontend
- ✅ rag-ingestion
- ✅ rag-trigger

### Test 3: Verify Ingestion Works
```bash
# Copy a test file to trigger auto-ingestion
cp data/sample_confluence_pages/agile_workflow.txt data/incoming/

# Check ingestion logs
docker compose logs -f ingestion

# Verify file moved to processed/
ls data/incoming/processed/
```

### Test 4: Environment Variables Loaded Correctly
```bash
# Start dev mode
./scripts/dev-mode.sh

# Check if variables are set (in a new terminal)
docker exec rag-backend env | grep LLM_HOST
```

**Expected:** `LLM_HOST=rag-ollama` (without the inline comment)

---

## Prevention

### Best Practice: Quote Environment Values in Shell Scripts

**Instead of:**
```bash
export $(grep ... | xargs)  # Dangerous with inline comments
```

**Consider:**
```bash
# Option 1: Use set -a (auto-export)
set -a
source <(grep -v '^#' .env | sed 's/#.*$//' | grep -v '^[[:space:]]*$')
set +a

# Option 2: Use dotenv libraries
# Python: python-dotenv
# Node.js: dotenv
# Docker: docker compose automatically loads .env
```

### For This Project
We use the `sed` approach because:
- ✅ Works in all POSIX shells (bash, zsh, sh)
- ✅ No external dependencies
- ✅ Handles inline comments correctly
- ✅ Simple and fast

---

## Summary

| Issue | Status | Fix |
|-------|--------|-----|
| `export: '#': not a valid identifier` | ✅ Fixed | Added `sed 's/#.*$//'` to strip inline comments |
| Ingestion service not in dev-mode.sh | ✅ Fixed | Added to startup sequence |
| Trigger service not in dev-mode.sh | ✅ Fixed | Added with `--profile trigger` |
| Service verification missing | ✅ Fixed | Added docker ps checks |

---

## Next Steps

- [x] Fix inline comment handling in shell scripts
- [x] Add ingestion service to dev-mode.sh
- [x] Add trigger service to dev-mode.sh
- [x] Update help text with new services
- [ ] Test end-to-end ingestion flow
- [ ] Consider adding health checks for ingestion/trigger
- [ ] Update documentation with new dev-mode features

---

## Related Files

- `scripts/dev-mode.sh` - Development mode startup (updated)
- `scripts/dev-up.sh` - Production-like startup (updated)
- `.env` - Configuration with inline comments
- `docker-compose.yml` - Service definitions
- `docker-compose.dev.yml` - Development overrides

---

## Lessons Learned

1. **Inline comments in .env files are dangerous** when using simple shell parsing
2. **Always test shell scripts** after modifying .env format
3. **Use `sed` to strip comments** for robust .env loading
4. **Document environment variable format** to prevent future issues
5. **Test with actual .env files** that have inline comments
