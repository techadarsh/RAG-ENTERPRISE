#!/bin/bash

###############################################################################
# Auto-Trigger Ingestion Service Test Script
# Tests folder watcher, S3/MinIO listener, and Confluence webhook
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_URL="http://localhost:8000"
TEST_DIR="./data/incoming"
TEST_FILE_PREFIX="test_trigger"
WAIT_TIME=10  # Seconds to wait for processing

# Test results
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

###############################################################################
# Helper Functions
###############################################################################

print_header() {
    echo -e "\n${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}\n"
}

print_test() {
    echo -e "${YELLOW}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
    ((TESTS_PASSED++))
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
    ((TESTS_FAILED++))
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_service() {
    local service=$1
    if docker compose ps $service | grep -q "Up"; then
        return 0
    else
        return 1
    fi
}

wait_for_job() {
    local job_id=$1
    local max_wait=$2
    local waited=0
    
    print_info "Waiting for job $job_id to complete (max ${max_wait}s)..."
    
    while [ $waited -lt $max_wait ]; do
        response=$(curl -s "$BACKEND_URL/api/ingest/status/$job_id")
        status=$(echo $response | jq -r '.status')
        
        if [ "$status" = "completed" ]; then
            print_success "Job completed successfully"
            return 0
        elif [ "$status" = "failed" ]; then
            print_error "Job failed: $(echo $response | jq -r '.error')"
            return 1
        fi
        
        sleep 2
        waited=$((waited + 2))
        echo -n "."
    done
    
    echo ""
    print_error "Job did not complete within ${max_wait}s (status: $status)"
    return 1
}

cleanup_test_files() {
    print_info "Cleaning up test files..."
    rm -f ${TEST_DIR}/${TEST_FILE_PREFIX}_*.txt
    print_success "Test files removed"
}

###############################################################################
# Pre-flight Checks
###############################################################################

preflight_checks() {
    print_header "Pre-flight Checks"
    
    print_test "Checking if Docker is running..."
    if docker info &> /dev/null; then
        print_success "Docker is running"
    else
        print_error "Docker is not running"
        exit 1
    fi
    
    print_test "Checking if backend service is running..."
    if check_service "backend"; then
        print_success "Backend service is running"
    else
        print_error "Backend service is not running. Start with: docker compose up -d"
        exit 1
    fi
    
    print_test "Checking if backend is accessible..."
    if curl -s -f "$BACKEND_URL/" &> /dev/null; then
        print_success "Backend is accessible at $BACKEND_URL"
    else
        print_error "Backend is not accessible at $BACKEND_URL"
        exit 1
    fi
    
    print_test "Checking if Redis is running..."
    if check_service "redis"; then
        print_success "Redis service is running"
    else
        print_error "Redis service is not running"
        exit 1
    fi
    
    print_test "Checking if ingestion worker is running..."
    if check_service "ingestion"; then
        print_success "Ingestion worker is running"
    else
        print_error "Ingestion worker is not running"
        exit 1
    fi
    
    print_test "Checking if jq is installed..."
    if command -v jq &> /dev/null; then
        print_success "jq is installed"
    else
        print_error "jq is not installed. Install with: brew install jq (macOS) or apt-get install jq (Linux)"
        exit 1
    fi
    
    print_test "Creating test directory if needed..."
    mkdir -p "$TEST_DIR"
    print_success "Test directory ready: $TEST_DIR"
}

###############################################################################
# Test 1: Folder Watcher
###############################################################################

test_folder_watcher() {
    print_header "Test 1: Folder Watcher"
    ((TESTS_RUN++))
    
    print_test "Checking if trigger service is running..."
    if ! check_service "trigger"; then
        print_error "Trigger service is not running"
        print_info "Enable with: ENABLE_FOLDER_WATCHER=true in .env"
        print_info "Start with: docker compose --profile trigger up -d"
        return 1
    fi
    print_success "Trigger service is running"
    
    print_test "Checking if folder watcher is enabled..."
    watcher_enabled=$(docker compose exec -T trigger env | grep ENABLE_FOLDER_WATCHER || echo "false")
    if [[ "$watcher_enabled" == *"true"* ]]; then
        print_success "Folder watcher is enabled"
    else
        print_error "Folder watcher is not enabled (ENABLE_FOLDER_WATCHER=false)"
        print_info "Set ENABLE_FOLDER_WATCHER=true in .env and restart"
        return 1
    fi
    
    # Create test file
    local test_file="${TEST_FILE_PREFIX}_$(date +%s).txt"
    local test_content="This is a test document for folder watcher functionality. Generated at $(date)"
    
    print_test "Creating test file: $test_file"
    echo "$test_content" > "${TEST_DIR}/${test_file}"
    print_success "Test file created"
    
    print_test "Waiting ${WAIT_TIME}s for file detection and job enqueue..."
    sleep $WAIT_TIME
    
    print_test "Checking trigger service logs for file detection..."
    if docker compose logs trigger | grep -q "$test_file"; then
        print_success "File was detected by trigger service"
        
        # Extract job ID from logs
        job_id=$(docker compose logs trigger | grep "$test_file" | grep -o 'job [a-f0-9-]*' | head -1 | awk '{print $2}')
        
        if [ -n "$job_id" ]; then
            print_info "Job ID: $job_id"
            
            # Wait for job completion
            if wait_for_job "$job_id" 30; then
                print_success "Folder watcher test PASSED"
                return 0
            else
                print_error "Folder watcher test FAILED (job did not complete)"
                return 1
            fi
        else
            print_error "Could not extract job ID from logs"
            return 1
        fi
    else
        print_error "File was not detected by trigger service"
        print_info "Check logs: docker compose logs trigger"
        return 1
    fi
}

###############################################################################
# Test 2: Confluence Webhook
###############################################################################

test_confluence_webhook() {
    print_header "Test 2: Confluence Webhook"
    ((TESTS_RUN++))
    
    local test_url="https://httpbin.org/html"
    local test_title="Test Confluence Page $(date +%s)"
    
    print_test "Sending webhook request to backend..."
    
    response=$(curl -s -X POST "$BACKEND_URL/api/webhook/confluence" \
        -H "Content-Type: application/json" \
        -d '{
            "event": "page_created",
            "page": {
                "id": "test123",
                "title": "'"$test_title"'",
                "url": "'"$test_url"'"
            }
        }')
    
    print_info "Response: $response"
    
    status=$(echo $response | jq -r '.status')
    if [ "$status" = "success" ]; then
        print_success "Webhook request accepted"
        
        job_id=$(echo $response | jq -r '.job_id')
        print_info "Job ID: $job_id"
        
        # Wait for job completion
        if wait_for_job "$job_id" 30; then
            print_success "Confluence webhook test PASSED"
            return 0
        else
            print_error "Confluence webhook test FAILED (job did not complete)"
            return 1
        fi
    else
        print_error "Webhook request failed: $response"
        return 1
    fi
}

###############################################################################
# Test 3: Manual API Upload (Baseline Test)
###############################################################################

test_manual_upload() {
    print_header "Test 3: Manual API Upload (Baseline)"
    ((TESTS_RUN++))
    
    local test_file="${TEST_FILE_PREFIX}_api_$(date +%s).txt"
    local test_content="This is a test document for API upload. Generated at $(date)"
    
    print_test "Creating test file..."
    echo "$test_content" > "/tmp/${test_file}"
    print_success "Test file created: /tmp/${test_file}"
    
    print_test "Uploading file via API..."
    response=$(curl -s -X POST "$BACKEND_URL/api/ingest/upload" \
        -F "file=@/tmp/${test_file}")
    
    print_info "Response: $response"
    
    status=$(echo $response | jq -r '.status')
    if [ "$status" = "queued" ]; then
        print_success "File upload accepted"
        
        job_id=$(echo $response | jq -r '.job_id')
        print_info "Job ID: $job_id"
        
        # Wait for job completion
        if wait_for_job "$job_id" 30; then
            print_success "Manual API upload test PASSED"
            rm -f "/tmp/${test_file}"
            return 0
        else
            print_error "Manual API upload test FAILED"
            rm -f "/tmp/${test_file}"
            return 1
        fi
    else
        print_error "File upload failed: $response"
        rm -f "/tmp/${test_file}"
        return 1
    fi
}

###############################################################################
# Test 4: Job Status API
###############################################################################

test_job_status_api() {
    print_header "Test 4: Job Status API"
    ((TESTS_RUN++))
    
    print_test "Testing invalid job ID..."
    response=$(curl -s "$BACKEND_URL/api/ingest/status/invalid-job-id")
    status=$(echo $response | jq -r '.status')
    
    if [ "$status" = "not_found" ] || [ "$status" = "null" ]; then
        print_success "Invalid job ID handled correctly"
        return 0
    else
        print_error "Invalid job ID not handled correctly"
        return 1
    fi
}

###############################################################################
# Main Test Runner
###############################################################################

main() {
    print_header "🚀 RAG Enterprise - Auto-Trigger Ingestion Test Suite"
    
    # Parse arguments
    test_type="${1:-all}"
    
    # Run preflight checks
    preflight_checks
    
    # Run tests based on argument
    case $test_type in
        folder)
            test_folder_watcher
            ;;
        webhook)
            test_confluence_webhook
            ;;
        api)
            test_manual_upload
            test_job_status_api
            ;;
        all)
            test_manual_upload
            test_job_status_api
            test_confluence_webhook
            test_folder_watcher
            ;;
        *)
            echo "Usage: $0 [folder|webhook|api|all]"
            echo ""
            echo "  folder  - Test folder watcher only"
            echo "  webhook - Test Confluence webhook only"
            echo "  api     - Test manual API upload only"
            echo "  all     - Run all tests (default)"
            exit 1
            ;;
    esac
    
    # Cleanup
    if [ "$test_type" = "all" ] || [ "$test_type" = "folder" ]; then
        cleanup_test_files
    fi
    
    # Print summary
    print_header "Test Summary"
    echo -e "Total tests run: ${TESTS_RUN}"
    echo -e "${GREEN}Passed: ${TESTS_PASSED}${NC}"
    echo -e "${RED}Failed: ${TESTS_FAILED}${NC}"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        print_success "All tests passed! 🎉"
        exit 0
    else
        print_error "Some tests failed. Check logs above for details."
        exit 1
    fi
}

# Run main function
main "$@"
