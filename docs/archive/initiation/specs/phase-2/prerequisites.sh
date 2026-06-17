#!/bin/bash
# Auto-generated prerequisites for Phase 2
# Run this before executing Phase 2 specs with Ralph
# Usage: bash specs/phase-2/prerequisites.sh

set -e

echo "🔍 Checking prerequisites for Phase 2..."

# ========================================
# SYSTEM TOOLS (check only - manual install)
# ========================================

# Python 3.11+ (required)
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ python3 not found"
    echo "   Install Python 3.11+ from https://python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✓ python3 ($PYTHON_VERSION)"

# SQLite3 (required for database operations)
if ! command -v sqlite3 >/dev/null 2>&1; then
    echo "❌ sqlite3 not found"
    echo "   Install with: apt install sqlite3  # Ubuntu/Debian"
    echo "             brew install sqlite3     # macOS"
    exit 1
fi
echo "✓ sqlite3"

# ========================================
# PYTHON PACKAGES (auto-install, no sudo)
# ========================================

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ] && [ ! -f "pyproject.toml" ]; then
    # Not in venv and no project file - use --user flag
    PIP_FLAGS="--user"
else
    # In venv or project has deps file - let pip handle it
    PIP_FLAGS=""
fi

# Function to check and install Python package
check_python_package() {
    local package=$1
    local import_name=$2

    if ! python3 -c "import $import_name" >/dev/null 2>&1; then
        echo "📦 Installing $package..."
        pip3 install $PIP_FLAGS "$package" >/dev/null 2>&1 || {
            echo "❌ Failed to install $package"
            exit 1
        }
    fi
    echo "✓ $import_name"
}

# Core dependencies (from Phase 1 + Phase 2)
check_python_package "fastapi>=0.109.0" "fastapi"
check_python_package "uvicorn[standard]>=0.27.0" "uvicorn"
check_python_package "pydantic>=2.0.0" "pydantic"
check_python_package "pydantic-settings>=2.0.0" "pydantic_settings"
check_python_package "aiosqlite>=0.19.0" "aiosqlite"
check_python_package "httpx>=0.26.0" "httpx"
check_python_package "structlog>=24.0.0" "structlog"
check_python_package "pyyaml>=6.0.0" "yaml"

# Test dependencies
check_python_package "pytest>=8.0.0" "pytest"
check_python_package "pytest-asyncio>=0.23.0" "pytest_asyncio"

# ========================================
# PROJECT STRUCTURE CHECK
# ========================================

echo ""
echo "🔍 Checking project structure..."

# Required directories
REQUIRED_DIRS=(
    "src/domain/models"
    "src/services"
    "src/llm/prompts"
    "src/persistence/repositories"
    "src/api/routes"
    "tests/unit"
    "tests/integration"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "❌ Missing directory: $dir"
        echo "   Run Phase 1 specs first, or create with: mkdir -p $dir"
        exit 1
    fi
done
echo "✓ All required directories exist"

# Required files from Phase 1
REQUIRED_FILES=(
    "src/__init__.py"
    "src/main.py"
    "src/core/config.py"
    "src/core/logging.py"
    "src/persistence/database.py"
    "src/persistence/migrations/001_initial.sql"
    "src/persistence/repositories/session_repo.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Missing file: $file"
        echo "   Run Phase 1 specs first"
        exit 1
    fi
done
echo "✓ All Phase 1 files exist"

# ========================================
# ENVIRONMENT CHECK
# ========================================

echo ""
echo "🔍 Checking environment..."

# Check for .env file
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "⚠️  No .env file found. Creating from .env.example..."
        cp .env.example .env
        echo "   Please edit .env and set ANTHROPIC_API_KEY"
    else
        echo "⚠️  No .env file found. Create one with ANTHROPIC_API_KEY"
    fi
else
    echo "✓ .env file exists"
fi

# ========================================
# FINAL STATUS
# ========================================

echo ""
echo "============================================"
echo "✅ All prerequisites satisfied!"
echo "============================================"
echo ""
echo "Phase 2 specs are ready to execute."
echo ""
echo "Dependency order:"
echo "  2.1 Domain Models (no dependencies)"
echo "  2.2 LLM Client (depends on 2.1)"
echo "  2.3 Extraction Prompts (depends on 2.1)"
echo "  2.4 Extraction Service (depends on 2.2, 2.3)"
echo "  2.5 Graph Repository (depends on 2.1)"
echo "  2.6 Graph Service (depends on 2.5)"
echo "  2.7 Question Prompts (depends on 2.1)"
echo "  2.8 Question Service (depends on 2.2, 2.7)"
echo "  2.9 Session Service (depends on 2.4, 2.6, 2.8)"
echo "  2.10 Turn Endpoint (depends on 2.9)"
echo "  2.11 Pipeline Test (depends on all above)"
echo ""
echo "Run tests after each spec:"
echo "  pytest tests/unit/test_<name>.py -v"
echo ""
