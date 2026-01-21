#!/bin/bash
# Auto-generated prerequisites for Phase 5: Demo UI
# Run this before Ralph execution
# Usage: bash prerequisites.sh

set -e

echo "🔍 Checking Phase 5 prerequisites..."

# ========================================
# SYSTEM TOOLS (check only - manual install)
# ========================================

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

# curl (required for API testing)
if ! command -v curl >/dev/null 2>&1; then
    echo "❌ curl not found"
    echo "   Install with: apt install curl  # Ubuntu/Debian"
    echo "             brew install curl     # macOS"
    exit 1
fi
echo "✓ curl"

# ========================================
# PYTHON PACKAGES (auto-install, no sudo)
# ========================================

# Check if we're in a virtual environment
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

# Streamlit (UI framework)
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

check_python_module "streamlit" "streamlit>=1.31.0"

# Plotly (graph visualization)
check_python_module "plotly" "plotly>=5.18.0"

# NetworkX (graph algorithms)
check_python_module "networkx" "networkx>=3.2"

# httpx (API client)
check_python_module "httpx" "httpx>=0.26.0"

# pandas (optional, for data handling)
check_python_module "pandas" "pandas>=2.0.0"

# ========================================
# PHASE 5 SPECIFIC CHECKS
# ========================================

# Check that previous phase prerequisites are met
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

# Check that UI components can be imported
echo ""
echo "Checking UI components..."

if ! python3 -c "from ui.api_client import APIClient" 2>/dev/null; then
    echo "⚠️  UI API client not yet created (expected for Phase 5)"
else
    echo "✓ UI API client"
fi

if ! python3 -c "from ui.components.chat import ChatInterface" 2>/dev/null; then
    echo "⚠️  Chat interface not yet created (expected for Phase 5)"
else
    echo "✓ Chat interface"
fi

if ! python3 -c "from ui.components.graph import GraphVisualizer" 2>/dev/null; then
    echo "⚠️  Graph visualizer not yet created (expected for Phase 5)"
else
    echo "✓ Graph visualizer"
fi

if ! python3 -c "from ui.components.metrics import MetricsPanel" 2>/dev/null; then
    echo "⚠️  Metrics panel not yet created (expected for Phase 5)"
else
    echo "✓ Metrics panel"
fi

if ! python3 -c "from ui.components.controls import SessionControls" 2>/dev/null; then
    echo "⚠️  Session controls not yet created (expected for Phase 5)"
else
    echo "✓ Session controls"
fi

# Check that backend API is accessible (optional)
echo ""
echo "Checking backend API (optional)..."

API_URL="${API_URL:-http://localhost:8000}"

if curl -s -f "$API_URL/health" >/dev/null 2>&1; then
    echo "✓ Backend API accessible at $API_URL"
else
    echo "⚠️  Backend API not accessible at $API_URL"
    echo "   Start the backend with: uvicorn src.main:app --reload"
fi

# ========================================
# UI-SPECIFIC CHECKS
# ========================================

echo ""
echo "Checking UI-specific dependencies..."

# Check if Streamlit can run basic app
if command -v streamlit >/dev/null 2>&1; then
    echo "✓ streamlit command available"
    
    # Verify Streamlit can create a basic app
    if python3 -c "import streamlit; print(streamlit.__version__)" >/dev/null 2>&1; then
        STREAMLIT_VERSION=$(python3 -c "import streamlit; print(streamlit.__version__)")
        echo "  Version: $STREAMLIT_VERSION"
    fi
else
    echo "⚠️  streamlit command not in PATH"
    echo "   You may need to add ~/.local/bin to PATH"
fi

# Check Plotly for graph visualization
if python3 -c "import plotly.graph_objects; print('OK')" >/dev/null 2>&1; then
    PLOTLY_VERSION=$(python3 -c "import plotly; print(plotly.__version__)")
    echo "✓ Plotly $PLOTLY_VERSION (graph visualization)"
fi

# Check NetworkX for graph algorithms
if python3 -c "import networkx; print('OK')" >/dev/null 2>&1; then
    NETWORKX_VERSION=$(python3 -c "import networkx; print(networkx.__version__)")
    echo "✓ NetworkX $NETWORKX_VERSION (graph algorithms)"
fi

echo ""
echo "✅ All Phase 5 prerequisites satisfied!"
echo ""
echo "Phase 5 adds:"
echo "  - Streamlit demo UI"
echo "  - Chat interface component"
echo "  - Graph visualization component"
echo "  - Metrics panel component"
echo "  - Session controls component"
echo "  - Main Streamlit app"
echo "  - UI integration tests"
echo ""
echo "To run the UI:"
echo "  1. Start backend: uvicorn src.main:app --reload"
echo "  2. Start UI: streamlit run ui/streamlit_app.py"
echo "  3. Open browser: http://localhost:8501"
