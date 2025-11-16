#!/bin/bash

# Documentation Removal Script
# Removes unnecessary documentation files that are no longer needed
# Keeps only valuable knowledge base and architectural documents

set -e

echo "🗑️  RAG Enterprise - Documentation Cleanup (Aggressive)"
echo "========================================================"
echo ""
echo "This will DELETE documentation files that are:"
echo "  - Historical bug fix summaries (already fixed)"
echo "  - Duplicate/redundant guides"
echo "  - Old phase completion reports"
echo "  - Temporary implementation notes"
echo ""
echo "KEEPING valuable documents:"
echo "  - Architecture documentation"
echo "  - Current implementation guides"
echo "  - Privacy and security docs"
echo ""

# Count before
TOTAL_BEFORE=$(find docs_archive -type f | wc -l | tr -d ' ')
echo "Total files before: $TOTAL_BEFORE"
echo ""

read -p "⚠️  Are you sure you want to DELETE these files? (type 'yes' to confirm): " -r
echo ""

if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
    echo "❌ Cancelled. No files were deleted."
    exit 0
fi

echo "Starting deletion..."
echo ""

# ============================================
# DELETE: Legacy bug fix summaries (all useless)
# ============================================
echo "🗑️  Deleting legacy bug fix summaries..."
cd docs_archive/legacy

rm -f ARM64_FIX_SUMMARY.md                    # Fixed long ago
rm -f CLEANUP_SUMMARY.md                      # Historical cleanup notes
rm -f CODE_CLEANUP_SUMMARY.md                 # Historical cleanup notes
rm -f EMOJI_REMOVAL_SUMMARY.md                # Minor UX fix
rm -f FINAL_DIAGNOSIS.md                      # Old debugging notes
rm -f FRONTEND_SCROLLING_FIX.md               # Minor bug fix
rm -f GIT_COMMIT_SUMMARY.md                   # Git history, not needed
rm -f IMMEDIATE_FIX_README.md                 # Temporary fix notes
rm -f ISSUE_RESOLUTION_EMBEDDINGS_CHAT.md     # Old bug resolution
rm -f LLM_HARDENING_SUMMARY.md                # Historical hardening notes
rm -f LOGGING_AND_THREAD_SAFETY_FIXES.md      # Historical fix notes
rm -f RELIABILITY_FIXES_SUMMARY.md            # Historical fix notes
rm -f SHELL_SCRIPT_FIXES.md                   # Historical fix notes
rm -f SOURCE_DISPLAY_CLEANUP.md               # Historical cleanup notes

echo "  ✅ Deleted 14 legacy bug fix summaries"

# ============================================
# DELETE: Redundant implementation summaries
# ============================================
echo "🗑️  Deleting redundant implementation summaries..."

rm -f CHECKLIST.md                            # Old checklist
rm -f IMPLEMENTATION_CHECKLIST.md             # Duplicate checklist
rm -f INGESTION_COMPLETE.md                   # Redundant with guides
rm -f INGESTION_DUAL_PATHWAY.md               # Redundant
rm -f INGESTION_IMPLEMENTATION_SUMMARY.md     # Redundant
rm -f INGESTION_SUMMARY.md                    # Redundant
rm -f KNOWLEDGE_BASE_SUMMARY.md               # Redundant

echo "  ✅ Deleted 7 redundant summaries"

# ============================================
# DELETE: Old phase completion reports
# ============================================
echo "🗑️  Deleting old phase completion reports..."

rm -f EVALUATION_PHASE3_SUMMARY.md            # Old phase report
rm -f PHASE2_IMPLEMENTATION_COMPLETE.md       # Old phase report
rm -f PHASE3_RESTORED.md                      # Old phase report

echo "  ✅ Deleted 3 phase reports"

# ============================================
# DELETE: UX improvement notes (implemented)
# ============================================
echo "🗑️  Deleting implemented UX improvement notes..."

rm -f CHATGPT_STYLE_UX.md                     # Already implemented
rm -f FRONTEND_UX_IMPROVEMENTS.md             # Already implemented
rm -f PHASE3_UX_IMPROVEMENTS.md               # Already implemented

echo "  ✅ Deleted 3 UX improvement notes"

# ============================================
# KEEP: Important implementation details
# ============================================
echo "✅ Keeping important implementation docs:"
echo "  - CONVERSATIONAL_MEMORY_IMPLEMENTATION.md (architectural knowledge)"

cd ../..

# ============================================
# DELETE: Redundant guides (keep only best ones)
# ============================================
echo "🗑️  Deleting redundant guides..."
cd docs_archive/guides

rm -f CONFLUENCE_IMPLEMENTATION.md            # Redundant with CONFLUENCE_API_IMPLEMENTATION.md
rm -f DETAILED_EXPLANATION.md                 # Too generic
rm -f DEV_MODE_QUICK_REFERENCE.md             # Redundant with main quick reference
rm -f INGESTION_QUICKSTART.md                 # Redundant with INGESTION_API_GUIDE.md
rm -f LOCAL_SETUP_GUIDE.md                    # Redundant with LOCAL_SETUP_SUCCESS.md (in root)
rm -f PHASE2_QUICK_REFERENCE.md               # Old phase reference
rm -f QUICK_SWITCH_GUIDE.md                   # Not needed anymore
rm -f TRIGGER_SERVICE_GUIDE.md                # Not actively used

echo "  ✅ Deleted 8 redundant guides"

echo "✅ Keeping valuable guides:"
echo "  - ARCHITECTURE.md (system architecture)"
echo "  - CONFLUENCE_API_IMPLEMENTATION.md (API implementation)"
echo "  - HOT_RELOAD_GUIDE.md (development workflow)"
echo "  - INGESTION_API_GUIDE.md (ingestion documentation)"
echo "  - LLM_BACKEND_IMPLEMENTATION.md (LLM implementation)"

cd ../..

# ============================================
# DELETE: Old planning docs
# ============================================
echo "🗑️  Deleting old planning documents..."
cd docs_archive/summaries

rm -f TODO_RESOLUTION_SUMMARY.md              # TODOs already resolved
rm -f UX_IMPROVEMENTS.md                      # Already implemented

echo "  ✅ Deleted 2 old planning docs"

echo "✅ Keeping valuable planning docs:"
echo "  - PERFORMANCE_OPTIMIZATION_PLAN.md (optimization reference)"
echo "  - PRIVACY_GUARANTEE.md (security/privacy documentation)"
echo "  - PROJECT_SUMMARY.txt (project overview)"
echo "  - PROMPT_DESIGN.md (LLM prompt engineering)"

cd ../..

# ============================================
# Summary
# ============================================
echo ""
echo "========================================================"
echo "✅ Cleanup Complete!"
echo ""

TOTAL_AFTER=$(find docs_archive -type f 2>/dev/null | wc -l | tr -d ' ')
DELETED=$((TOTAL_BEFORE - TOTAL_AFTER))

echo "📊 Summary:"
echo "  - Files before: $TOTAL_BEFORE"
echo "  - Files after: $TOTAL_AFTER"
echo "  - Files deleted: $DELETED"
echo ""
echo "📂 Remaining files structure:"
echo ""
echo "docs_archive/"
echo "├── legacy/ (1 file kept)"
echo "│   └── CONVERSATIONAL_MEMORY_IMPLEMENTATION.md"
echo "├── guides/ (5 files kept)"
echo "│   ├── ARCHITECTURE.md"
echo "│   ├── CONFLUENCE_API_IMPLEMENTATION.md"
echo "│   ├── HOT_RELOAD_GUIDE.md"
echo "│   ├── INGESTION_API_GUIDE.md"
echo "│   └── LLM_BACKEND_IMPLEMENTATION.md"
echo "└── summaries/ (4 files kept)"
echo "    ├── PERFORMANCE_OPTIMIZATION_PLAN.md"
echo "    ├── PRIVACY_GUARANTEE.md"
echo "    ├── PROJECT_SUMMARY.txt"
echo "    └── PROMPT_DESIGN.md"
echo ""
echo "💡 These 10 files contain valuable knowledge about:"
echo "   - System architecture and design"
echo "   - Implementation details for key features"
echo "   - Performance optimization strategies"
echo "   - Security and privacy considerations"
echo "   - Prompt engineering best practices"
echo ""
echo "🎯 Result: Clean documentation structure with only essential knowledge!"
echo ""
