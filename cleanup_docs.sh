#!/bin/bash

# Documentation Cleanup Script
# Moves old documentation files to docs_archive/ directory

set -e

echo "📚 RAG Enterprise - Documentation Cleanup"
echo "=========================================="
echo ""

# Create archive directories
echo "Creating archive directories..."
mkdir -p docs_archive/legacy
mkdir -p docs_archive/guides
mkdir -p docs_archive/summaries

# Count files
TOTAL_FILES=$(find . -maxdepth 1 -type f \( -name "*.md" -o -name "*.txt" \) | wc -l | tr -d ' ')
echo "Found $TOTAL_FILES documentation files"
echo ""

# Files to KEEP in root (current/active documentation)
KEEP_FILES=(
    "README.md"
    "QUICKSTART.md"
    "QUICK_REFERENCE_LOCAL.md"
    "LOCAL_SETUP_SUCCESS.md"
    "IMPROVEMENT_AREAS.md"
    "DEMO_PREP_CHECKLIST.md"
    "DOCUMENTATION_INVENTORY.md"
)

echo "Files that will STAY in root directory:"
for file in "${KEEP_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    fi
done
echo ""

# Legacy summaries (move to docs_archive/legacy/)
echo "Moving legacy summaries to docs_archive/legacy/..."
LEGACY_FILES=(
    "ARM64_FIX_SUMMARY.md"
    "CHATGPT_STYLE_UX.md"
    "CHECKLIST.md"
    "CLEANUP_SUMMARY.md"
    "CODE_CLEANUP_SUMMARY.md"
    "CONVERSATIONAL_MEMORY_IMPLEMENTATION.md"
    "EMOJI_REMOVAL_SUMMARY.md"
    "EVALUATION_PHASE3_SUMMARY.md"
    "FINAL_DIAGNOSIS.md"
    "FRONTEND_SCROLLING_FIX.md"
    "FRONTEND_UX_IMPROVEMENTS.md"
    "GIT_COMMIT_SUMMARY.md"
    "IMMEDIATE_FIX_README.md"
    "IMPLEMENTATION_CHECKLIST.md"
    "INGESTION_COMPLETE.md"
    "INGESTION_DUAL_PATHWAY.md"
    "INGESTION_IMPLEMENTATION_SUMMARY.md"
    "INGESTION_SUMMARY.md"
    "ISSUE_RESOLUTION_EMBEDDINGS_CHAT.md"
    "KNOWLEDGE_BASE_SUMMARY.md"
    "LLM_HARDENING_SUMMARY.md"
    "LOGGING_AND_THREAD_SAFETY_FIXES.md"
    "PHASE2_IMPLEMENTATION_COMPLETE.md"
    "PHASE3_RESTORED.md"
    "PHASE3_UX_IMPROVEMENTS.md"
    "RELIABILITY_FIXES_SUMMARY.md"
    "SHELL_SCRIPT_FIXES.md"
    "SOURCE_DISPLAY_CLEANUP.md"
)

MOVED_LEGACY=0
for file in "${LEGACY_FILES[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" docs_archive/legacy/
        echo "  📦 $file"
        MOVED_LEGACY=$((MOVED_LEGACY + 1))
    fi
done
echo "  ✅ Moved $MOVED_LEGACY legacy files"
echo ""

# Technical guides (move to docs_archive/guides/)
echo "Moving technical guides to docs_archive/guides/..."
GUIDE_FILES=(
    "ARCHITECTURE.md"
    "CONFLUENCE_API_IMPLEMENTATION.md"
    "CONFLUENCE_IMPLEMENTATION.md"
    "DETAILED_EXPLANATION.md"
    "DEV_MODE_QUICK_REFERENCE.md"
    "HOT_RELOAD_GUIDE.md"
    "INGESTION_API_GUIDE.md"
    "INGESTION_QUICKSTART.md"
    "LLM_BACKEND_IMPLEMENTATION.md"
    "LOCAL_SETUP_GUIDE.md"
    "PHASE2_QUICK_REFERENCE.md"
    "QUICK_SWITCH_GUIDE.md"
    "TRIGGER_SERVICE_GUIDE.md"
)

MOVED_GUIDES=0
for file in "${GUIDE_FILES[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" docs_archive/guides/
        echo "  📦 $file"
        MOVED_GUIDES=$((MOVED_GUIDES + 1))
    fi
done
echo "  ✅ Moved $MOVED_GUIDES guide files"
echo ""

# Planning/summary documents (move to docs_archive/summaries/)
echo "Moving planning documents to docs_archive/summaries/..."
SUMMARY_FILES=(
    ".env_UPDATE_SUMMARY.md"
    "PERFORMANCE_OPTIMIZATION_PLAN.md"
    "PRIVACY_GUARANTEE.md"
    "PROJECT_SUMMARY.txt"
    "PROMPT_DESIGN.md"
    "TODO_RESOLUTION_SUMMARY.md"
    "UX_IMPROVEMENTS.md"
)

MOVED_SUMMARIES=0
for file in "${SUMMARY_FILES[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" docs_archive/summaries/
        echo "  📦 $file"
        MOVED_SUMMARIES=$((MOVED_SUMMARIES + 1))
    fi
done
echo "  ✅ Moved $MOVED_SUMMARIES planning files"
echo ""

# Summary
echo "=========================================="
echo "✅ Cleanup Complete!"
echo ""
echo "Summary:"
echo "  - Legacy files moved: $MOVED_LEGACY → docs_archive/legacy/"
echo "  - Guide files moved: $MOVED_GUIDES → docs_archive/guides/"
echo "  - Planning files moved: $MOVED_SUMMARIES → docs_archive/summaries/"
echo "  - Total moved: $((MOVED_LEGACY + MOVED_GUIDES + MOVED_SUMMARIES))"
echo ""
echo "Files remaining in root:"
ls -1 *.md 2>/dev/null | wc -l | xargs echo "  -" 
echo ""
echo "To view archived docs:"
echo "  cd docs_archive"
echo "  ls -la legacy/ guides/ summaries/"
echo ""
