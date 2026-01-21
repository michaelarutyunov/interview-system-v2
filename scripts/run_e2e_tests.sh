#!/bin/bash
#
# E2E Test Runner Script
#
# This script:
# 1. Starts the backend server in the background
# 2. Waits for the server to be ready
# 3. Runs E2E tests
# 4. Cleans up by stopping the background server
#
# Usage:
#   ./scripts/run_e2e_tests.sh [test_file_pattern]
#
# Examples:
#   ./scripts/run_e2e_tests.sh                    # Run all E2E tests
#   ./scripts/run_e2e_tests.sh test_e2e_system    # Run system E2E tests
#   ./scripts/run_e2e_tests.sh test_e2e_performance  # Run performance tests

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
SERVER_URL="http://${HOST}:${PORT}"
LOG_FILE="${PROJECT_ROOT}/logs/e2e_server.log"
PID_FILE="${PROJECT_ROOT}/logs/e2e_server.pid"

# Create logs directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$(dirname "$PID_FILE")"

# Test file pattern (optional)
TEST_PATTERN="${1:-test_e2e}"

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}  E2E Test Runner${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Function to check if server is ready
check_server_ready() {
    local max_attempts=30
    local attempt=1

    echo -e "${YELLOW}Waiting for server to be ready...${NC}"

    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "${SERVER_URL}/health/live" > /dev/null 2>&1; then
            echo -e "${GREEN}Server is ready!${NC}"
            return 0
        fi

        echo -n "."
        sleep 1
        ((attempt++))
    done

    echo -e "\n${RED}Server failed to start within ${max_attempts} seconds${NC}"
    return 1
}

# Function to cleanup background processes
cleanup() {
    echo ""
    echo -e "${YELLOW}Cleaning up...${NC}"

    if [ -f "$PID_FILE" ]; then
        SERVER_PID=$(cat "$PID_FILE")
        if kill -0 "$SERVER_PID" 2>/dev/null; then
            echo -e "${YELLOW}Stopping server (PID: $SERVER_PID)...${NC}"
            kill "$SERVER_PID" 2>/dev/null || true
            wait "$SERVER_PID" 2>/dev/null || true
        fi
        rm -f "$PID_FILE"
    fi

    # Additional cleanup: kill any uvicorn processes on the port
    if command -v lsof >/dev/null 2>&1; then
        lsof -ti:${PORT} | xargs kill -9 2>/dev/null || true
    fi

    echo -e "${GREEN}Cleanup complete${NC}"
}

# Register cleanup function to run on exit
trap cleanup EXIT

# Check if server is already running
if curl -s -f "${SERVER_URL}/health/live" > /dev/null 2>&1; then
    echo -e "${YELLOW}Server is already running at ${SERVER_URL}${NC}"
    echo -e "${YELLOW}Skipping server startup...${NC}"
    SERVER_ALREADY_RUNNING=true
else
    SERVER_ALREADY_RUNNING=false

    # Start the server in background
    echo -e "${BLUE}Starting server at ${SERVER_URL}...${NC}"

    # Activate virtual environment if it exists
    if [ -f "${PROJECT_ROOT}/.venv/bin/activate" ]; then
        source "${PROJECT_ROOT}/.venv/bin/activate"
    elif [ -f "${PROJECT_ROOT}/venv/bin/activate" ]; then
        source "${PROJECT_ROOT}/venv/bin/activate"
    fi

    # Start server and capture PID
    cd "${PROJECT_ROOT}"

    # Use a temporary test database
    export TEST_DB="${PROJECT_ROOT}/.test_e2e_db.sqlite"
    rm -f "$TEST_DB"  # Remove old test database

    # Start server in background
    nohup uvicorn src.main:app \
        --host "$HOST" \
        --port "$PORT" \
        --log-level info \
        > "$LOG_FILE" 2>&1 &

    SERVER_PID=$!
    echo "$SERVER_PID" > "$PID_FILE"

    echo -e "${GREEN}Server started with PID: $SERVER_PID${NC}"
    echo -e "${BLUE}Logs: $LOG_FILE${NC}"

    # Wait for server to be ready
    if ! check_server_ready; then
        echo -e "${RED}Server logs:${NC}"
        tail -20 "$LOG_FILE"
        exit 1
    fi
fi

# Run health check
echo ""
echo -e "${BLUE}Running health check...${NC}"
HEALTH_RESPONSE=$(curl -s "${SERVER_URL}/health")
echo -e "${GREEN}Health check response:${NC}"
echo "$HEALTH_RESPONSE" | python3 -m json.tool || echo "$HEALTH_RESPONSE"
echo ""

# Run E2E tests
echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}  Running E2E Tests${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

cd "${PROJECT_ROOT}"

# Run pytest with E2E tests
if [ "$TEST_PATTERN" = "test_e2e" ]; then
    # Run all E2E tests
    echo -e "${BLUE}Running all E2E tests...${NC}"
    python3 -m pytest \
        tests/integration/test_e2e_*.py \
        -v \
        --tb=short \
        --color=yes \
        -k "test_e2e" \
        "$@"
else
    # Run specific test pattern
    echo -e "${BLUE}Running tests matching: $TEST_PATTERN${NC}"
    python3 -m pytest \
        tests/integration/"${TEST_PATTERN}".py \
        -v \
        --tb=short \
        --color=yes \
        "$@"
fi

TEST_EXIT_CODE=$?

echo ""

# Report results
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}======================================${NC}"
    echo -e "${GREEN}  All E2E tests passed!${NC}"
    echo -e "${GREEN}======================================${NC}"
else
    echo -e "${RED}======================================${NC}"
    echo -e "${RED}  Some E2E tests failed!${NC}"
    echo -e "${RED}======================================${NC}"
fi

# Exit with test exit code
exit $TEST_EXIT_CODE
