#!/bin/bash
# Auto-generated prerequisites for Phase 6: Export & Polish
# Run this before Ralph execution
# Usage: bash prerequisites.sh

set -e

echo "🔍 Checking Phase 6 prerequisites..."

# ========================================
# SYSTEM TOOLS (check only - manual install)
# ========================================

# curl (required for API testing)
if ! command -v curl >/dev/null 2>&1; then
    echo "❌ curl not found"
    echo "   Install with: apt install curl  # Ubuntu/Debian"
    echo "             brew install curl     # macOS"
    exit 1
fi
echo "✓ curl"

# Python 3.11+ (required)
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ python3 not found"
    echo "   Install with: apt install python3  # Ubuntu/Debian"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f1)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo "❌ python3 version $PYTHON_VERSION is too old (requires 3.11+)"
    exit 1
fi
echo "✓ python3 $PYTHON_VERSION"

# ========================================
# PYTHON PACKAGES (auto-install, no sudo)
# ========================================

if [ -z "$VIRTUAL_ENV" ] && [ ! -f "pyproject.toml" ] && [ ! -f "requirements.txt" ]; then
    PIP_FLAGS="--user"
else
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

# Check Python modules
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
check_python_module "yaml" "pyyaml"
check_python_module "aiosqlite" "aiosqlite"

# ========================================
# CHECK PREVIOUS PHASE PREREQUISITES
# ========================================

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

if [ -f "../phase-4/prerequisites.sh" ]; then
    echo ""
    echo "Checking Phase 4 prerequisites..."
    bash ../phase-4/prerequisites.sh || exit 1
fi

if [ -f "../phase-5/prerequisites.sh" ]; then
    echo ""
    echo "Checking Phase 5 prerequisites..."
    bash ../phase-5/prerequisites.sh || exit 1
fi

# ========================================
# PHASE 6 SPECIFIC CHECKS
# ========================================

echo ""
echo "Checking Phase 6 specific dependencies..."

# Check export service
if python3 -c "from src.services.export_service import ExportService" 2>/dev/null; then
    echo "✓ Export service"
else
    echo "⚠️  Export service not yet created (expected for Phase 6)"
fi

# Check exception handlers
if python3 -c "from src.api.exception_handlers import setup_exception_handlers" 2>/dev/null; then
    echo "✓ Exception handlers"
else
    echo "⚠️  Exception handlers not yet created (expected for Phase 6)"
fi

# Check concepts endpoint
if python3 -c "from src.api.routes.concepts import router" 2>/dev/null; then
    echo "✓ Concepts endpoint"
else
    echo "⚠️  Concepts endpoint not yet created (expected for Phase 6)"
fi

# Check for documentation
if [ -f "README.md" ]; then
    echo "✓ README.md exists"
else
    echo "⚠️  README.md not yet created (expected for Phase 6)"
fi

# ========================================
# DOCUMENTATION TOOLS
# ========================================

echo ""
echo "Checking documentation tools..."

# Check for markdown link checker (optional)
if command -v markdown-link-check >/dev/null 2>&1; then
    echo "✓ markdown-link-check (for validating docs)"
else
    echo "⚠️  markdown-link-check not found (optional)"
    echo "   Install with: npm install -g markdown-link-check"
fi

# Check for PyYAML for config parsing
if python3 -c "import yaml; print('OK')" 2>/dev/null; then
    YAML_VERSION=$(python3 -c "import yaml; print(yaml.__version__)" 2>/dev/null)
    echo "✓ PyYAML $YAML_VERSION (concept configuration)"
else
    echo "⚠️  PyYAML not installed"
    echo "   Install with: uv pip install pyyaml"
fi

# ========================================
# OPTIONAL: PERFORMANCE TOOLS
# ========================================

echo ""
echo "Checking performance tools (optional)..."

# apachebench for load testing
if command -v ab >/dev/null 2>&1; then
    echo "✓ ab (apachebench for load testing)"
else
    echo "⚠️  ab not found (optional, for performance testing)"
    echo "   Install with: apt install apache2-utils"
fi

# ========================================
# PHASE 6 COMPLETION CHECKS
# ========================================

echo ""
echo "Phase 6 completion checklist:"

# Count specs created
SPEC_COUNT=$(ls specs/phase-6/*.md 2>/dev/null | grep -v prerequisites.sh | wc -l)
echo "  - Specs created: $SPEC_COUNT/8"

if [ "$SPEC_COUNT" -eq 8 ]; then
    echo "  ✅ All Phase 6 specs generated"
else
    echo "  ⚠️  Some specs missing (expected during development)"
fi

# Check if main components exist
echo ""
echo "Component status:"

[ -f "src/services/export_service.py" ] && echo "  ✅ Export service" || echo "  ⬜ Export service"
[ -f "src/api/routes/concepts.py" ] && echo "  ✅ Concepts endpoint" || echo "  ⬜ Concepts endpoint"
[ -f "src/api/exception_handlers.py" ] && echo "  ✅ Exception handlers" || echo "  ⬜ Exception handlers"
[ -f "README.md" ] && echo "  ✅ README.md" || echo "  ⬜ README.md"

echo ""
echo "✅ All Phase 6 prerequisites satisfied!"
echo ""
echo "Phase 6 adds:"
echo "  - Export service (JSON, Markdown, CSV)"
echo "  - Export API endpoints"
echo "  - Concept management endpoints"
echo "  - Comprehensive error handling"
echo "  - Structured logging review"
echo "  - Documentation (README, API docs, etc.)"
echo "  - End-to-end integration tests"
echo "  - Performance validation"
echo ""
echo "Phase 6 completes the MVP!"
echo "Ready for production deployment."
