#!/bin/bash
# Auto-generated prerequisites for Phase 4: Synthetic Respondent
# Run this before Ralph execution
# Usage: bash prerequisites.sh

set -e

echo "🔍 Checking Phase 4 prerequisites..."

# ========================================
# SYSTEM TOOLS (check only - manual install)
# ========================================

# curl (required for API testing)
if ! command -v curl >/dev/null 2>&1; then
    echo "❌ curl not found"
    echo "   Install with: apt install curl  # Ubuntu/Debian"
    echo "             brew install curl     # macOS"
    echo "   This requires sudo/admin access."
    exit 1
fi
echo "✓ curl"

# Python 3.11+ (required)
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ python3 not found"
    echo "   Install with: apt install python3  # Ubuntu/Debian"
    echo "             brew install python@3.11  # macOS"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo "❌ python3 version $PYTHON_VERSION is too old (requires 3.11+)"
    exit 1
fi
echo "✓ python3 $PYTHON_VERSION"

# ========================================
# PYTHON PACKAGES (auto-install, no sudo)
# ========================================

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ] && [ ! -f "pyproject.toml" ] && [ ! -f "requirements.txt" ]; then
    # Not in venv and no project file - use --user flag
    PIP_FLAGS="--user"
else
    # In venv or project has deps file - let pip handle it
    PIP_FLAGS=""
fi

# uv (package manager)
if ! command -v uv >/dev/null 2>&1; then
    echo "📦 Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi
echo "✓ uv"

# pytest (test framework)
if ! command -v pytest >/dev/null 2>&1; then
    echo "📦 Installing pytest..."
    if command -v uv >/dev/null 2>&1; then
        uv pip install $PIP_FLAGS pytest pytest-asyncio >/dev/null 2>&1
    else
        pip3 install $PIP_FLAGS pytest pytest-asyncio >/dev/null 2>&1
    fi
fi
echo "✓ pytest"

# httpx (async HTTP client - required for API calls and script)
check_python_module() {
    local module=$1
    local package=$2
    if ! python3 -c "import $module" >/dev/null 2>&1; then
        echo "📦 Installing $package..."
        if command -v uv >/dev/null 2>&1; then
            uv pip install $PIP_FLAGS "$package" >/dev/null 2>&1
        else
            pip3 install $PIP_FLAGS "$package" >/dev/null 2>&1
        fi
    fi
    echo "✓ $module"
}

check_python_module "httpx" "httpx"
check_python_module "pydantic" "pydantic"
check_python_module "fastapi" "fastapi"
check_python_module "structlog" "structlog"

# ========================================
# PROJECT-SPECIFIC CHECKS
# ========================================

# Check that Phase 1-3 prerequisites are met
if [ -f "../phase-1/prerequisites.sh" ]; then
    echo ""
    echo "Checking Phase 1 prerequisites..."
    bash ../phase-1/prerequisites.sh || exit 1
fi

if [ -f "../phase-2/prerequisites.sh" ]; then
    echo ""
    echo "Checking Phase 2 prerequisites..."
    bash ../phase-2/prerequisites.sh || exit 1
fi

if [ -f "../phase-3/prerequisites.sh" ]; then
    echo ""
    echo "Checking Phase 3 prerequisites..."
    bash ../phase-3/prerequisites.sh || exit 1
fi

# ========================================
# PHASE 4 SPECIFIC CHECKS
# ========================================

# Check that LLM client is available (from Phase 2)
if ! python3 -c "from src.llm.client import LLMClient" 2>/dev/null; then
    echo "❌ LLM client not available (Phase 2 incomplete)"
    echo "   Complete Phase 2 before running Phase 4"
    exit 1
fi
echo "✓ LLM client"

# Check that session service is available (from Phase 2)
if ! python3 -c "from src.services.session_service import SessionService" 2>/dev/null; then
    echo "❌ Session service not available (Phase 2 incomplete)"
    echo "   Complete Phase 2 before running Phase 4"
    exit 1
fi
echo "✓ Session service"

# Check that API routes are available (from Phase 1-2)
if ! python3 -c "from src.api.routes.sessions import router" 2>/dev/null; then
    echo "❌ API routes not available (Phase 1/2 incomplete)"
    echo "   Complete Phase 1-2 before running Phase 4"
    exit 1
fi
echo "✓ API routes"

# Check for ANTHROPIC_API_KEY
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️  ANTHROPIC_API_KEY not set"
    echo "   Set with: export ANTHROPIC_API_KEY=your-key-here"
    echo "   Or create .env file with: ANTHROPIC_API_KEY=your-key-here"
else
    echo "✓ ANTHROPIC_API_KEY configured"
fi

# ========================================
# OPTIONAL: Verify API can start
# ========================================

# Check if uvicorn is available for running the API
if ! python3 -c "import uvicorn" 2>/dev/null; then
    echo "📦 Installing uvicorn..."
    if command -v uv >/dev/null 2>&1; then
        uv pip install $PIP_FLAGS uvicorn[standard] >/dev/null 2>&1
    else
        pip3 install $PIP_FLAGS uvicorn[standard] >/dev/null 2>&1
    fi
fi
echo "✓ uvicorn"

echo ""
echo "✅ All Phase 4 prerequisites satisfied!"
echo ""
echo "Phase 4 adds:"
echo "  - Synthetic respondent prompts"
echo "  - Synthetic service for automated testing"
echo "  - Synthetic API endpoints"
echo "  - Test script for automated interviews"
echo "  - Integration tests for validation"
echo ""
echo "Ready to run Phase 4 specs."
