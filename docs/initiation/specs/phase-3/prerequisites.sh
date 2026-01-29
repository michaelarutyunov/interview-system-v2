#!/bin/bash
# Auto-generated prerequisites for Phase 3: Scoring & Strategy
# Run this before Ralph execution
# Usage: bash prerequisites.sh

set -e

echo "🔍 Checking Phase 3 prerequisites..."

# ========================================
# SYSTEM TOOLS (check only - manual install)
# ========================================

# Python3
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ python3 not found"
    echo "   Install with: apt install python3  # Ubuntu/Debian"
    echo "             brew install python3     # macOS"
    exit 1
fi
echo "✓ python3"

# pip
if ! command -v pip3 >/dev/null 2>&1; then
    echo "❌ pip3 not found"
    echo "   Install with: apt install python3-pip  # Ubuntu/Debian"
    exit 1
fi
echo "✓ pip3"

# git
if ! command -v git >/dev/null 2>&1; then
    echo "❌ git not found"
    echo "   Install with: apt install git  # Ubuntu/Debian"
    echo "             brew install git     # macOS"
    exit 1
fi
echo "✓ git"

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

# pytest (test framework)
if ! command -v pytest >/dev/null 2>&1; then
    echo "📦 Installing pytest..."
    pip3 install $PIP_FLAGS pytest pytest-asyncio >/dev/null 2>&1
fi
echo "✓ pytest"

# Python modules
check_python_module() {
    local module=$1
    local package=$2
    if ! python3 -c "import $module" >/dev/null 2>&1; then
        echo "📦 Installing $package..."
        pip3 install $PIP_FLAGS "$package" >/dev/null 2>&1
    fi
    echo "✓ $module"
}

# Phase 3 specific dependencies
check_python_module "structlog" "structlog"
check_python_module "pydantic" "pydantic"

# ========================================
# PHASE 3 SPECIFIC CHECKS
# ========================================

# Check if Phase 2 dependencies are available
echo ""
echo "🔍 Checking Phase 2 dependencies..."

check_python_module "aiosqlite" "aiosqlite"

# Verify Phase 2 models exist
if [ ! -f "src/domain/models/knowledge_graph.py" ]; then
    echo "❌ Phase 2 models not found"
    echo "   Please complete Phase 2 first"
    exit 1
fi
echo "✓ Phase 2 models present"

# Verify Phase 2 services exist
if [ ! -f "src/services/session_service.py" ]; then
    echo "❌ Phase 2 services not found"
    echo "   Please complete Phase 2 first"
    exit 1
fi
echo "✓ Phase 2 services present"

echo ""
echo "✅ All Phase 3 prerequisites satisfied!"
echo "   Ready to run Ralph."
