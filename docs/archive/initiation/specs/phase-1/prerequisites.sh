#!/bin/bash
# Auto-generated prerequisites for Phase 1
# Run this before Ralph execution
# Usage: bash scripts/ralph/prerequisites.sh

set -e

echo "🔍 Checking prerequisites for interview-system-v2..."

# ========================================
# SYSTEM TOOLS (check only - manual install)
# ========================================

# Python 3.11+
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ python3 not found"
    echo "   Install with: apt install python3 python3-pip  # Ubuntu/Debian"
    echo "             brew install python3                # macOS"
    echo "   This requires sudo/admin access."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo "❌ Python 3.11+ required (found $PYTHON_VERSION)"
    exit 1
fi
echo "✓ python3 $PYTHON_VERSION"

# git (required for version control)
if ! command -v git >/dev/null 2>&1; then
    echo "❌ git not found"
    echo "   Install with: apt install git  # Ubuntu/Debian"
    echo "             brew install git     # macOS"
    exit 1
fi
echo "✓ git"

# curl (required for API testing)
if ! command -v curl >/dev/null 2>&1; then
    echo "❌ curl not found"
    echo "   Install with: apt install curl  # Ubuntu/Debian"
    echo "             brew install curl     # macOS"
    exit 1
fi
echo "✓ curl"

# sqlite3 (required for database operations)
if ! command -v sqlite3 >/dev/null 2>&1; then
    echo "❌ sqlite3 not found"
    echo "   Install with: apt install sqlite3  # Ubuntu/Debian"
    echo "             brew install sqlite3     # macOS"
    echo "   This requires sudo/admin access."
    exit 1
fi
echo "✓ sqlite3"

# ========================================
# PYTHON PACKAGES (auto-install, no sudo)
# ========================================

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ] && [ ! -f "pyproject.toml" ] && [ ! -f "requirements.txt" ]; then
    # Not in venv and no project file - use --user flag
    PIP_FLAGS="--user"
    # Ensure ~/.local/bin is in PATH
    if ! echo $PATH | grep -q "$HOME/.local/bin"; then
        export PATH="$HOME/.local/bin:$PATH"
    fi
else
    # In venv or project has deps file - let pip handle it
    PIP_FLAGS=""
fi

# pytest (test framework)
if ! command -v pytest >/dev/null 2>&1; then
    echo "📦 Installing pytest..."
    pip3 install $PIP_FLAGS -q pytest pytest-asyncio
fi
echo "✓ pytest"

# Python modules
check_python_module() {
    local module=$1
    local package=$2
    if ! python3 -c "import $module" >/dev/null 2>&1; then
        echo "📦 Installing $package..."
        pip3 install $PIP_FLAGS -q "$package"
    fi
    echo "✓ $module"
}

check_python_module "aiosqlite" "aiosqlite"
check_python_module "pydantic" "pydantic"
check_python_module "pydantic_settings" "pydantic-settings"
check_python_module "structlog" "structlog"
check_python_module "fastapi" "fastapi"
check_python_module "uvicorn" "uvicorn[standard]"
check_python_module "httpx" "httpx"

echo ""
echo "✅ All prerequisites satisfied!"
echo "   Ready to run Ralph."
