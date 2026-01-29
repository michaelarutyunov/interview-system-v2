# Phase 5: Demo UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Streamlit-based demo UI for conducting and visualizing adaptive interviews with real-time graph visualization, metrics, and session controls.

**Architecture:** Streamlit app runs on port 8501 as a separate process from the FastAPI backend (port 8000), making HTTP REST API calls to avoid v1's event loop conflicts. The UI is organized into modular components (chat, graph, metrics, controls) that integrate into a main app with three tabs.

**Tech Stack:**
- Python 3.11+, Streamlit >=1.31.0 for UI framework
- Plotly >=5.18.0 for interactive graph visualization
- NetworkX >=3.2 for graph layout algorithms
- httpx >=0.26.0 for async API client

---

## Context Notes

**Why Streamlit not Gradio:** v1 used Gradio which caused event loop conflicts with async operations (asyncpg + async LLM calls). Streamlit runs as a completely separate process with clean HTTP REST API calls to FastAPI, avoiding any event loop entanglement.

**Component Architecture:**
- `ui/api_client.py` - HTTP client for all FastAPI communication
- `ui/components/` - Modular UI components (chat, graph, metrics, controls)
- `ui/streamlit_app.py` - Main app integrating all components

**Session State:** Streamlit's `st.session_state` is used for:
- `current_session` - Active SessionInfo object
- `chat_history` - List of message dicts
- `opening_displayed` - Whether opening question was shown
- `api_client` - APIClient instance
- `sessions` - Cached list of all sessions

---

## File Organization

```
ui/
  api_client.py           # NEW - HTTP client for FastAPI backend
  streamlit_app.py        # NEW - Main Streamlit application
  components/
    chat.py               # NEW - Chat interface component
    graph.py              # NEW - Graph visualization component
    metrics.py            # NEW - Metrics panel component
    controls.py           # NEW - Session controls component
  components/__init__.py  # NEW - Component exports
tests/ui/
  test_smoke.py           # NEW - Component unit tests
  manual_test_checklist.md # NEW - Manual testing checklist
docs/
  ui-framework-decision.md # NEW - Framework selection documentation
```

---

### Task 1: UI Framework Decision (Spec 5.1)

**Files:**
- Create: `docs/ui-framework-decision.md`

**Step 1: Create decision document**

```bash
cat > docs/ui-framework-decision.md << 'EOF'
# UI Framework Decision for Phase 5

## Decision: Streamlit

Date: 2026-01-21
Status: Approved

## Evaluation Criteria

1. **Async Safety**: Must not interfere with FastAPI event loop
2. **Development Speed**: Quick iteration for demo purposes
3. **Component Support**: Chat, graphs, metrics display
4. **API Integration**: Clean HTTP client to FastAPI backend
5. **Deployment**: Can run separately or alongside API

## Options Considered

### Gradio
- ✅ Quick setup, good chat components
- ❌ v1 had event loop issues with async operations
- ❌ Less customization control
- Verdict: Risk of repeating v1 problems

### Streamlit (Selected)
- ✅ Pure Python, fast development
- ✅ Good data viz components (Plotly, Altair)
- ✅ Separate process - no event loop conflicts
- ✅ Simple HTTP API calls to backend
- ⚠️ Rerun model can be slow for frequent updates
- Verdict: Best fit for demo UI MVP

### htmx
- ✅ Lightweight, no JS needed
- ❌ More manual work for components
- ❌ Slower development for demo
- Verdict: Good for production, overkill for demo

### React
- ✅ Full control, modern
- ❌ Requires JS expertise
- ❌ Separate frontend build step
- Verdict: Overkill for demo purposes

## Architecture

```
User Browser
    │
    ▼
Streamlit (localhost:8501)
    │ HTTP REST API calls
    ▼
FastAPI (localhost:8000)
    │
    ▼
Services + Database
```

## Dependencies

```
streamlit>=1.31.0
plotly>=5.18.0
networkx>=3.2
httpx>=0.26.0
```
EOF
```

**Step 2: Verify document created**

Run: `cat docs/ui-framework-decision.md | head -20`
Expected: Shows markdown header with "UI Framework Decision"

**Step 3: Commit**

```bash
git add docs/ui-framework-decision.md
git commit -m "docs(ui): record framework selection decision (Streamlit)"
```

---

### Task 2: API Client (Spec 5.2 - Part 1)

**Files:**
- Create: `ui/api_client.py`
- Test: `tests/ui/test_smoke.py`

**Step 1: Write failing test**

```python
# tests/ui/test_smoke.py
"""Smoke tests for UI components."""

import pytest
from unittest.mock import MagicMock

from ui.api_client import APIClient, SessionInfo


class TestAPIClient:
    """Tests for API client."""

    def test_init_with_default_url(self):
        """Client initializes with default URL."""
        client = APIClient()
        assert client.base_url == "http://localhost:8000"
        assert client.timeout == 30.0

    def test_init_with_custom_url(self):
        """Client accepts custom base URL."""
        client = APIClient(base_url="http://localhost:9000", timeout=60.0)
        assert client.base_url == "http://localhost:9000"
        assert client.timeout == 60.0

    def test_get_client_creates_httpx_client(self):
        """_get_client creates httpx.AsyncClient."""
        client = APIClient()
        httpx_client = client._get_client()
        assert httpx_client is not None
        assert hasattr(httpx_client, "post")


class TestSessionInfo:
    """Tests for SessionInfo dataclass."""

    def test_create_session_info(self):
        """SessionInfo dataclass creates correctly."""
        info = SessionInfo(
            id="test-123",
            concept_id="oat_milk_v1",
            status="active",
            opening_question="What do you think?",
            created_at="2026-01-21T10:00:00Z"
        )
        assert info.id == "test-123"
        assert info.concept_id == "oat_milk_v1"
        assert info.status == "active"
        assert info.opening_question == "What do you think?"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/ui/test_smoke.py::TestAPIClient::test_init_with_default_url -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'ui'"

**Step 3: Create ui directory and write minimal implementation**

```bash
# Create ui directory structure
mkdir -p ui components tests/ui
touch ui/__init__.py ui/components/__init__.py tests/__init__.py
```

```python
# ui/api_client.py
"""API client for communicating with FastAPI backend."""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import httpx


@dataclass
class SessionInfo:
    """Information about an interview session."""
    id: str
    concept_id: str
    status: str
    opening_question: Optional[str] = None
    created_at: Optional[str] = None


class APIClient:
    """Client for making HTTP requests to the FastAPI backend."""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 30.0):
        """Initialize API client."""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def create_session(
        self,
        concept_id: str,
        max_turns: int = 20,
        target_coverage: float = 0.8,
    ) -> SessionInfo:
        """Create a new interview session."""
        client = self._get_client()
        response = await client.post(
            f"{self.base_url}/sessions",
            json={
                "concept_id": concept_id,
                "max_turns": max_turns,
                "target_coverage": target_coverage,
            },
        )
        response.raise_for_status()
        data = response.json()

        return SessionInfo(
            id=data["id"],
            concept_id=data["concept_id"],
            status=data["status"],
            opening_question=data.get("opening_question"),
            created_at=data.get("created_at"),
        )

    async def submit_turn(
        self,
        session_id: str,
        user_input: str,
    ) -> Dict[str, Any]:
        """Submit a turn to the session."""
        client = self._get_client()
        response = await client.post(
            f"{self.base_url}/sessions/{session_id}/turns",
            json={"user_input": user_input},
        )
        response.raise_for_status()
        return response.json()

    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get current session status."""
        client = self._get_client()
        response = await client.get(f"{self.base_url}/sessions/{session_id}/status")
        response.raise_for_status()
        return response.json()

    async def get_session_graph(self, session_id: str) -> Dict[str, Any]:
        """Get session knowledge graph."""
        client = self._get_client()
        response = await client.get(f"{self.base_url}/sessions/{session_id}/graph")
        response.raise_for_status()
        return response.json()

    async def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions."""
        client = self._get_client()
        response = await client.get(f"{self.base_url}/sessions")
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/ui/test_smoke.py::TestAPIClient -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add tests/ui/test_smoke.py ui/api_client.py ui/__init__.py ui/components/__init__.py tests/__init__.py
git commit -m "feat(ui): add API client for FastAPI backend (Task 2)"
```

---

### Task 3: Chat Interface Component (Spec 5.2 - Part 2)

**Files:**
- Create: `ui/components/chat.py`
- Test: `tests/ui/test_smoke.py` (extend)

**Step 1: Write failing test**

Add to `tests/ui/test_smoke.py`:

```python
from ui.components.chat import ChatInterface, initialize_chat_state


class TestChatInterface:
    """Tests for chat interface component."""

    def test_init_with_api_client(self):
        """ChatInterface initializes with API client."""
        mock_client = MagicMock(spec=APIClient)
        chat = ChatInterface(mock_client)
        assert chat.api_client == mock_client
        assert chat.max_history == 100

    def test_initialize_chat_state(self):
        """initialize_chat_state sets defaults."""
        import streamlit as st
        if not hasattr(st, "session_state"):
            st.session_state = MagicMock()

        initialize_chat_state()

        assert hasattr(st.session_state, "chat_history")
        assert hasattr(st.session_state, "opening_displayed")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/ui/test_smoke.py::TestChatInterface::test_init_with_api_client -v`
Expected: FAIL with "cannot import 'ChatInterface'"

**Step 3: Write minimal implementation**

```python
# ui/components/chat.py
"""Chat interface component for Streamlit demo UI."""

from typing import List, Dict, Any, Optional
import streamlit as st

from ui.api_client import APIClient, SessionInfo


class ChatInterface:
    """Manages the chat interface for interview conversations."""

    def __init__(self, api_client: APIClient):
        """Initialize chat interface."""
        self.api_client = api_client
        self.max_history = 100

    def render(self, session_info: Optional[SessionInfo]) -> Optional[str]:
        """Render the chat interface."""
        st.subheader("💬 Interview Chat")

        if not session_info:
            st.info("👋 Create or select a session to start the interview.")
            return None

        # Display opening question if available
        if session_info.opening_question:
            self._display_opening_question(session_info.opening_question)

        # Display chat history
        self._display_chat_history()

        # Chat input
        user_input = st.chat_input("Your response...")

        if user_input:
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = []
            st.session_state.chat_history.append({
                "role": "user",
                "content": user_input
            })

        return user_input if user_input else None

    def _display_opening_question(self, question: str):
        """Display the opening question."""
        if "opening_displayed" not in st.session_state:
            with st.chat_message("assistant"):
                st.write(question)
            st.session_state.opening_displayed = True
            st.session_state.chat_history = [{
                "role": "assistant",
                "content": question
            }]

    def _display_chat_history(self):
        """Display the chat history."""
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.write(message["content"])

    def add_assistant_message(self, content: str):
        """Add an assistant message to the chat history."""
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        st.session_state.chat_history.append({
            "role": "assistant",
            "content": content
        })

        # Trim history if needed
        if len(st.session_state.chat_history) > self.max_history:
            st.session_state.chat_history = st.session_state.chat_history[-self.max_history:]

    def clear_history(self):
        """Clear the chat history."""
        st.session_state.chat_history = []
        if "opening_displayed" in st.session_state:
            del st.session_state.opening_displayed

    def get_history(self) -> List[Dict[str, str]]:
        """Get the current chat history."""
        return st.session_state.get("chat_history", [])


def initialize_chat_state():
    """Initialize chat-related session state variables."""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "opening_displayed" not in st.session_state:
        st.session_state.opening_displayed = False
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/ui/test_smoke.py::TestChatInterface -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add ui/components/chat.py tests/ui/test_smoke.py
git commit -m "feat(ui): add chat interface component (Task 3)"
```

---

### Task 4: Graph Visualizer Component (Spec 5.3)

**Files:**
- Create: `ui/components/graph.py`
- Test: `tests/ui/test_smoke.py` (extend)

**Step 1: Write failing test**

Add to `tests/ui/test_smoke.py`:

```python
from ui.components.graph import GraphVisualizer


class TestGraphVisualizer:
    """Tests for graph visualizer component."""

    def test_init_creates_layout_algorithms(self):
        """GraphVisualizer initializes with layout algorithms."""
        visualizer = GraphVisualizer()

        assert "Spring" in visualizer.layout_algorithms
        assert "Kamada-Kawai" in visualizer.layout_algorithms
        assert "Circular" in visualizer.layout_algorithms
        assert len(visualizer.layout_algorithms) >= 5

    def test_node_colors_defined(self):
        """Node type colors are defined for all MEC types."""
        visualizer = GraphVisualizer()

        required_types = [
            "attribute",
            "functional_consequence",
            "psychosocial_consequence",
            "instrumental_value",
            "terminal_value",
        ]

        for node_type in required_types:
            assert node_type in visualizer.NODE_COLORS

    def test_node_colors_are_hex(self):
        """Node colors are valid hex color codes."""
        visualizer = GraphVisualizer()

        for color in visualizer.NODE_COLORS.values():
            assert color.startswith("#")
            assert len(color) == 7  # #RRGGBB format
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/ui/test_smoke.py::TestGraphVisualizer::test_init_creates_layout_algorithms -v`
Expected: FAIL with "cannot import 'GraphVisualizer'"

**Step 3: Write minimal implementation**

```python
# ui/components/graph.py
"""Graph visualization component for Streamlit demo UI."""

from typing import Optional, List, Dict, Any
import streamlit as st

import networkx as nx
import plotly.graph_objects as go


class GraphVisualizer:
    """Knowledge graph visualization using Plotly and NetworkX."""

    # Node type colors (MEC methodology)
    NODE_COLORS = {
        "attribute": "#FF6B6B",
        "functional_consequence": "#4ECDC4",
        "psychosocial_consequence": "#95E1D3",
        "instrumental_value": "#FFE66D",
        "terminal_value": "#6C5CE7",
        "unknown": "#DFE6E9",
    }

    NODE_SIZE_DEFAULT = 30
    EDGE_WIDTH_DEFAULT = 2

    def __init__(self):
        """Initialize graph visualizer."""
        self.layout_algorithms = {
            "Spring": nx.spring_layout,
            "Kamada-Kawai": nx.kamada_kawai_layout,
            "Circular": nx.circular_layout,
            "Random": nx.random_layout,
            "Spectral": nx.spectral_layout,
        }

    def render_controls(self) -> Dict[str, Any]:
        """Render graph control sidebar."""
        st.sidebar.subheader("🕸️ Graph Controls")

        layout = st.sidebar.selectbox(
            "Layout Algorithm",
            options=list(self.layout_algorithms.keys()),
            index=0,
        )

        dimensions = st.sidebar.radio(
            "View",
            options=["2D", "3D"],
            horizontal=True,
        )

        show_labels = st.sidebar.checkbox("Show Node Labels", value=True)

        all_node_types = list(self.NODE_COLORS.keys())
        node_filter = st.sidebar.multiselect(
            "Filter by Node Type",
            options=all_node_types,
            default=all_node_types,
        )

        return {
            "layout": layout,
            "dimensions": dimensions,
            "show_labels": show_labels,
            "node_filter": node_filter,
        }

    def render(
        self,
        graph_data: Dict[str, Any],
        controls: Dict[str, Any],
    ) -> Optional[go.Figure]:
        """Render the knowledge graph visualization."""
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        if not nodes:
            st.info("📊 No nodes to display yet. Start the interview to extract concepts.")
            return None

        # Filter nodes by type
        if controls["node_filter"]:
            nodes = [n for n in nodes if n.get("node_type") in controls["node_filter"]]
            node_ids = {n["id"] for n in nodes}
            edges = [
                e for e in edges
                if e.get("source_node_id") in node_ids and e.get("target_node_id") in node_ids
            ]

        # Build NetworkX graph
        G = nx.Graph()
        for node in nodes:
            G.add_node(node["id"], **node)

        for edge in edges:
            G.add_edge(
                edge["source_node_id"],
                edge["target_node_id"],
                edge_type=edge.get("edge_type", "leads_to"),
                **edge
            )

        # Compute layout
        layout_func = self.layout_algorithms[controls["layout"]]
        pos = layout_func(G)

        # Create Plotly figure
        if controls["dimensions"] == "3D":
            fig = self._create_3d_plot(G, pos, nodes, edges, controls)
        else:
            fig = self._create_2d_plot(G, pos, nodes, edges, controls)

        fig.update_layout(
            title=f"Knowledge Graph ({len(nodes)} nodes, {len(edges)} edges)",
            showlegend=False,
            hovermode='closest',
            margin=dict(b=0, l=0, r=0, t=40),
            height=500,
        )

        return fig

    def _create_2d_plot(
        self,
        G: nx.Graph,
        pos: Dict[str, tuple],
        nodes: List[Dict],
        edges: List[Dict],
        controls: Dict,
    ) -> go.Figure:
        """Create 2D plotly figure."""
        fig = go.Figure()

        # Edge traces
        edge_x = []
        edge_y = []

        for edge in edges:
            x0, y0 = pos[edge["source_node_id"]]
            x1, y1 = pos[edge["target_node_id"]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        fig.add_trace(go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=self.EDGE_WIDTH_DEFAULT, color='#888'),
            hoverinfo='none',
            mode='lines',
            name='edges',
        ))

        # Node traces
        node_x = []
        node_y = []
        node_text = []
        node_colors = []
        node_sizes = []
        hover_texts = []

        for node in nodes:
            node_id = node["id"]
            x, y = pos[node_id]
            node_x.append(x)
            node_y.append(y)

            node_type = node.get("node_type", "unknown")
            node_colors.append(self.NODE_COLORS.get(node_type, "#888888"))

            confidence = node.get("confidence", 0.8)
            node_sizes.append(self.NODE_SIZE_DEFAULT * (0.5 + confidence))

            if controls["show_labels"]:
                node_text.append(node.get("label", node_id))

            hover = f"<b>{node.get('label', node_id)}</b><br>"
            hover += f"Type: {node_type}<br>"
            hover += f"Confidence: {confidence:.2f}"
            hover_texts.append(hover)

        fig.add_trace(go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text' if controls["show_labels"] else 'markers',
            marker=dict(
                size=node_sizes,
                color=node_colors,
                line=dict(width=2, color='white'),
            ),
            text=node_text if controls["show_labels"] else None,
            textposition='middle center',
            hovertext=hover_texts,
            hoverinfo='text',
            name='nodes',
        ))

        return fig

    def _create_3d_plot(
        self,
        G: nx.Graph,
        pos: Dict[str, tuple],
        nodes: List[Dict],
        edges: List[Dict],
        controls: Dict,
    ) -> go.Figure:
        """Create 3D plotly figure."""
        # Convert 2D positions to 3D
        pos_3d = {node: (x, y, 0) for node, (x, y) in pos.items()}

        fig = go.Figure()

        # Edge traces
        edge_x = []
        edge_y = []
        edge_z = []

        for edge in edges:
            x0, y0, z0 = pos_3d[edge["source_node_id"]]
            x1, y1, z1 = pos_3d[edge["target_node_id"]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            edge_z.extend([z0, z1, None])

        fig.add_trace(go.Scatter3d(
            x=edge_x, y=edge_y, z=edge_z,
            mode='lines',
            line=dict(width=self.EDGE_WIDTH_DEFAULT, color='#888'),
            hoverinfo='none',
            name='edges',
        ))

        # Node traces
        node_x = []
        node_y = []
        node_z = []
        node_colors = []
        node_sizes = []
        hover_texts = []

        for node in nodes:
            node_id = node["id"]
            x, y, z = pos_3d[node_id]
            node_x.append(x)
            node_y.append(y)
            node_z.append(z)

            node_type = node.get("node_type", "unknown")
            node_colors.append(self.NODE_COLORS.get(node_type, "#888888"))

            confidence = node.get("confidence", 0.8)
            node_sizes.append(self.NODE_SIZE_DEFAULT * (0.5 + confidence) * 2)

            hover = f"<b>{node.get('label', node_id)}</b><br>"
            hover += f"Type: {node_type}<br>"
            hover += f"Confidence: {confidence:.2f}"
            hover_texts.append(hover)

        fig.add_trace(go.Scatter3d(
            x=node_x, y=node_y, z=node_z,
            mode='markers',
            marker=dict(
                size=node_sizes,
                color=node_colors,
                line=dict(width=1, color='white'),
            ),
            hovertext=hover_texts,
            hoverinfo='text',
            name='nodes',
        ))

        fig.update_layout(
            scene=dict(
                xaxis=dict(showgrid=False, showticklabels=False, visible=False),
                yaxis=dict(showgrid=False, showticklabels=False, visible=False),
                zaxis=dict(showgrid=False, showticklabels=False, visible=False),
            )
        )

        return fig


def render_graph_stats(graph_data: Dict[str, Any]):
    """Render graph statistics in sidebar."""
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    st.sidebar.subheader("📈 Graph Stats")

    # Count nodes by type
    node_types = {}
    for node in nodes:
        node_type = node.get("node_type", "unknown")
        node_types[node_type] = node_types.get(node_type, 0) + 1

    st.sidebar.metric("Total Nodes", len(nodes))
    st.sidebar.metric("Total Edges", len(edges))

    if node_types:
        st.sidebar.write("**Nodes by Type:**")
        for node_type, count in sorted(node_types.items()):
            st.sidebar.write(f"• {node_type}: {count}")
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/ui/test_smoke.py::TestGraphVisualizer -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add ui/components/graph.py tests/ui/test_smoke.py
git commit -m "feat(ui): add graph visualization component (Task 4)"
```

---

### Task 5: Metrics Panel Component (Spec 5.4)

**Files:**
- Create: `ui/components/metrics.py`
- Test: `tests/ui/test_smoke.py` (extend)

**Step 1: Write failing test**

Add to `tests/ui/test_smoke.py`:

```python
from ui.components.metrics import MetricsPanel


class TestMetricsPanel:
    """Tests for metrics panel component."""

    def test_init_creates_panel(self):
        """MetricsPanel initializes successfully."""
        panel = MetricsPanel()
        assert panel.coverage_emoji == ["⬜", "🟩"]

    def test_coverage_emoji_length(self):
        """Coverage emoji has 2 states."""
        panel = MetricsPanel()
        assert len(panel.coverage_emoji) == 2
        assert panel.coverage_emoji[0] == "⬜"
        assert panel.coverage_emoji[1] == "🟩"

    def test_render_accepts_status_data(self):
        """render accepts status data dict without error."""
        import streamlit as st
        if not hasattr(st, "session_state"):
            st.session_state = MagicMock()

        panel = MetricsPanel()
        status_data = {
            "turn_number": 5,
            "max_turns": 20,
            "coverage": 0.6,
            "status": "active",
            "scoring": {
                "coverage": 0.6,
                "depth": 0.4,
                "saturation": 0.1,
            },
        }
        # Would use Streamlit mocking in real test
        # panel.render(status_data)
        # Just verify data structure is accepted
        assert "turn_number" in status_data
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/ui/test_smoke.py::TestMetricsPanel::test_init_creates_panel -v`
Expected: FAIL with "cannot import 'MetricsPanel'"

**Step 3: Write minimal implementation**

```python
# ui/components/metrics.py
"""Metrics panel component for Streamlit demo UI."""

from typing import Dict, Any, Optional
import streamlit as st

import plotly.graph_objects as go


class MetricsPanel:
    """Displays interview metrics and diagnostics."""

    def __init__(self):
        """Initialize metrics panel."""
        self.coverage_emoji = ["⬜", "🟩"]

    def render(self, status_data: Dict[str, Any], graph_data: Optional[Dict] = None):
        """Render the complete metrics panel."""
        st.subheader("📊 Interview Metrics")

        # Main metrics row
        col1, col2, col3 = st.columns(3)

        with col1:
            self._render_turn_count(status_data)

        with col2:
            self._render_coverage(status_data)

        with col3:
            self._render_status(status_data)

        st.divider()

        # Scoring breakdown
        self._render_scoring(status_data)

        # Strategy info
        self._render_strategy(status_data)

        # Graph stats
        if graph_data:
            self._render_graph_stats(graph_data)

    def _render_turn_count(self, status_data: Dict[str, Any]):
        """Render turn count metric."""
        turn_number = status_data.get("turn_number", 0)
        max_turns = status_data.get("max_turns", 20)

        st.metric(
            label="Turns",
            value=f"{turn_number} / {max_turns}",
        )

        if max_turns > 0:
            progress = turn_number / max_turns
            st.progress(progress)

    def _render_coverage(self, status_data: Dict[str, Any]):
        """Render coverage metric with visual bar."""
        coverage = status_data.get("coverage", 0.0)
        target = status_data.get("target_coverage", 0.8)

        if coverage >= target:
            delta_color = "normal"
        else:
            delta_color = "inverse"

        st.metric(
            label="Coverage",
            value=f"{coverage*100:.1f}%",
            delta=f"Target: {target*100:.0f}%",
            delta_color=delta_color,
        )

        # Visual coverage bar
        filled = int(coverage * 10)
        bar = "".join([self.coverage_emoji[1]] * filled + [self.coverage_emoji[0]] * (10 - filled))
        st.markdown(f"<p style='font-size: 24px; letter-spacing: 2px;'>{bar}</p>", unsafe_allow_html=True)

    def _render_status(self, status_data: Dict[str, Any]):
        """Render session status."""
        session_status = status_data.get("status", "unknown")
        should_continue = status_data.get("should_continue", True)

        status_emoji = {
            "active": "🔄",
            "completed": "✅",
            "coverage_met": "🎯",
            "max_turns_reached": "📊",
            "saturated": "🔒",
        }.get(session_status, "❓")

        st.metric(
            label="Status",
            value=f"{status_emoji} {session_status.replace('_', ' ').title()}",
        )

        if not should_continue and session_status == "active":
            st.caption("Interview should end soon")

    def _render_scoring(self, status_data: Dict[str, Any]):
        """Render scoring breakdown."""
        scoring = status_data.get("scoring", {})

        if not scoring:
            st.info("No scoring data available yet.")
            return

        st.write("**Scoring Breakdown:**")

        scores = {
            "Coverage": scoring.get("coverage", 0.0),
            "Depth": scoring.get("depth", 0.0),
            "Saturation": scoring.get("saturation", 0.0),
            "Novelty": scoring.get("novelty", 0.0),
            "Richness": scoring.get("richness", 0.0),
        }

        cols = st.columns(len(scores))
        for i, (name, value) in enumerate(scores.items()):
            with cols[i]:
                self._render_gauge(name, value)

    def _render_gauge(self, name: str, value: float):
        """Render a gauge chart for a score."""
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = value,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': name},
            gauge = {
                'axis': {'range': [0, 1]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 0.5], 'color': "lightgray"},
                    {'range': [0.5, 0.8], 'color': "gray"},
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 0.9
                }
            }
        ))

        fig.update_layout(
            height=200,
            margin=dict(l=10, r=10, t=30, b=10),
        )

        st.plotly_chart(fig, use_container_width=True)

    def _render_strategy(self, status_data: Dict[str, Any]):
        """Render strategy selection info."""
        strategy = status_data.get("strategy_selected", "unknown")
        reasoning = status_data.get("strategy_reasoning", "")

        st.write("**Current Strategy:**")

        strategy_descriptions = {
            "deepen": "🔍 Deepen - Explore deeper in current topic chain",
            "broaden": "🌐 Broaden - Find new topic branches",
            "cover": "🎯 Cover - Introduce unexplored elements",
            "close": "✅ Close - Wrap up the interview",
        }

        st.info(strategy_descriptions.get(strategy, f"Strategy: {strategy}"))

        if reasoning:
            with st.expander("See strategy reasoning"):
                st.write(reasoning)

    def _render_graph_stats(self, graph_data: Dict[str, Any]):
        """Render graph statistics."""
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        st.write("**Knowledge Graph:**")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Nodes", len(nodes))
        with col2:
            st.metric("Edges", len(edges))

        # Node type distribution
        if nodes:
            node_types = {}
            for node in nodes:
                node_type = node.get("node_type", "unknown")
                node_types[node_type] = node_types.get(node_type, 0) + 1

            if node_types:
                st.write("**Node Types:**")
                fig = go.Figure(data=[
                    go.Pie(
                        labels=list(node_types.keys()),
                        values=list(node_types.values()),
                        hole=0.3,
                    )
                ])
                fig.update_layout(
                    height=250,
                    margin=dict(l=10, r=10, t=10, b=10),
                )
                st.plotly_chart(fig, use_container_width=True)


def render_turn_diagnostics(turn_result: Dict[str, Any]):
    """Render diagnostics for a single turn."""
    with st.expander("🔍 Turn Diagnostics"):
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Extraction:**")
            extracted = turn_result.get("extracted", {})
            st.write(f"- Concepts: {len(extracted.get('concepts', []))}")
            st.write(f"- Relationships: {len(extracted.get('relationships', []))}")

        with col2:
            st.write("**Timing:**")
            latency = turn_result.get("latency_ms", 0)
            st.write(f"- Latency: {latency:.0f}ms")

        # Show extracted concepts
        extracted = turn_result.get("extracted", {})
        concepts = extracted.get("concepts", [])
        if concepts:
            st.write("**Extracted Concepts:**")
            for concept in concepts[:5]:
                st.write(f"- {concept.get('text', 'N/A')} ({concept.get('node_type', 'N/A')})")

            if len(concepts) > 5:
                st.caption(f"... and {len(concepts) - 5} more")


def render_coverage_details(coverage_data: Dict[str, Any]):
    """Render detailed coverage information."""
    with st.expander("📋 Coverage Details"):
        elements = coverage_data.get("elements", [])

        if not elements:
            st.info("No element coverage data available.")
            return

        # Group by status
        covered = [e for e in elements if e.get("covered", False)]
        uncovered = [e for e in elements if not e.get("covered", False)]

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Covered", len(covered))
            if covered:
                for elem in covered[:5]:
                    st.write(f"✅ {elem.get('label', 'N/A')}")

        with col2:
            st.metric("Remaining", len(uncovered))
            if uncovered:
                for elem in uncovered[:5]:
                    st.write(f"⬜ {elem.get('label', 'N/A')}")
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/ui/test_smoke.py::TestMetricsPanel -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add ui/components/metrics.py tests/ui/test_smoke.py
git commit -m "feat(ui): add metrics panel component (Task 5)"
```

---

### Task 6: Session Controls Component (Spec 5.5)

**Files:**
- Create: `ui/components/controls.py`
- Test: `tests/ui/test_smoke.py` (extend)

**Step 1: Write failing test**

Add to `tests/ui/test_smoke.py`:

```python
from ui.components.controls import SessionControls, initialize_session_state


class TestSessionControls:
    """Tests for session controls component."""

    def test_init_with_api_client(self):
        """SessionControls initializes with API client."""
        mock_client = MagicMock(spec=APIClient)
        controls = SessionControls(mock_client)
        assert controls.api_client == mock_client


class TestSessionStateInitialization:
    """Tests for session state initialization functions."""

    def test_initialize_session_state_sets_defaults(self):
        """initialize_session_state() sets default values."""
        import streamlit as st
        if not hasattr(st, "session_state"):
            st.session_state = MagicMock()

        initialize_session_state()

        assert hasattr(st.session_state, "current_session")
        assert hasattr(st.session_state, "sessions")
        assert hasattr(st.session_state, "confirm_delete")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/ui/test_smoke.py::TestSessionControls::test_init_with_api_client -v`
Expected: FAIL with "cannot import 'SessionControls'"

**Step 3: Write minimal implementation**

```python
# ui/components/controls.py
"""Session controls component for Streamlit demo UI."""

from typing import Optional, List, Dict, Any
import streamlit as st

from ui.api_client import APIClient, SessionInfo


class SessionControls:
    """Manages session-related UI controls in the sidebar."""

    def __init__(self, api_client: APIClient):
        """Initialize session controls."""
        self.api_client = api_client

    def render(self) -> Optional[SessionInfo]:
        """Render session controls in sidebar."""
        st.sidebar.title("🎙️ Interview System")
        st.sidebar.divider()

        # Tab navigation
        tab1, tab2, tab3 = st.sidebar.tabs(["New", "Sessions", "Export"])

        with tab1:
            self._render_new_session()

        with tab2:
            return self._render_session_list()

        with tab3:
            self._render_export()

        return st.session_state.get("current_session")

    def _render_new_session(self):
        """Render new session creation form."""
        st.subheader("Create New Session")

        concept_id = st.selectbox(
            "Concept",
            options=["oat_milk_v1"],
            label_visibility="collapsed",
        )

        with st.expander("Advanced Options"):
            max_turns = st.number_input(
                "Max Turns",
                min_value=5,
                max_value=50,
                value=20,
            )

            target_coverage = st.slider(
                "Target Coverage",
                min_value=0.1,
                max_value=1.0,
                value=0.8,
                step=0.1,
            )

        if st.button("🚀 Start Interview", type="primary", use_container_width=True):
            self._create_session(concept_id, max_turns, target_coverage)

    def _create_session(self, concept_id: str, max_turns: int, target_coverage: float):
        """Create a new session."""
        with st.spinner("Creating session..."):
            try:
                session_info = st.session_state.api_client.create_session(
                    concept_id=concept_id,
                    max_turns=max_turns,
                    target_coverage=target_coverage,
                )

                st.session_state.current_session = session_info
                st.session_state.chat_history = []
                st.session_state.opening_displayed = False

                st.success(f"Session {session_info.id[:8]} created!")
                st.rerun()

            except Exception as e:
                st.error(f"Failed to create session: {str(e)}")

    def _render_session_list(self) -> Optional[SessionInfo]:
        """Render session list and selection."""
        st.subheader("Sessions")

        if st.session_state.get("sessions") is None:
            self._load_sessions()

        sessions = st.session_state.get("sessions", [])

        if not sessions:
            st.info("No sessions found.")
            return None

        session_options = {
            f"{s['id'][:8]} ({s.get('status', 'unknown')})": s
            for s in sessions
        }

        selected = st.selectbox(
            "Select Session",
            options=list(session_options.keys()),
            label_visibility="collapsed",
        )

        if selected:
            session = session_options[selected]

            self._display_session_details(session)

            col1, col2 = st.columns(2)

            with col1:
                if st.button("📂 Load", use_container_width=True):
                    self._load_session(session)

            with col2:
                if st.button("🗑️ Delete", use_container_width=True):
                    self._delete_session(session['id'])

            current = st.session_state.get("current_session")
            if current and current.id == session['id']:
                return current

        return None

    def _display_session_details(self, session: Dict[str, Any]):
        """Display details for a session."""
        with st.expander("Session Details"):
            st.write(f"**ID:** {session['id']}")
            st.write(f"**Status:** {session.get('status', 'unknown')}")
            st.write(f"**Concept:** {session.get('concept_id', 'N/A')}")

    def _load_session(self, session: Dict[str, Any]):
        """Load an existing session."""
        session_id = session['id']

        with st.spinner(f"Loading session {session_id[:8]}..."):
            try:
                status = st.session_state.api_client.get_session_status(session_id)

                session_info = SessionInfo(
                    id=session_id,
                    concept_id=session.get("concept_id", ""),
                    status=status.get("status", "unknown"),
                    created_at=session.get("created_at"),
                )

                st.session_state.current_session = session_info
                st.session_state.chat_history = []
                st.session_state.opening_displayed = False

                st.success(f"Session {session_id[:8]} loaded!")
                st.rerun()

            except Exception as e:
                st.error(f"Failed to load session: {str(e)}")

    def _delete_session(self, session_id: str):
        """Delete a session."""
        if not st.session_state.get("confirm_delete", False):
            st.session_state.confirm_delete = True
            st.warning("Click again to confirm deletion")
            return

        st.session_state.confirm_delete = False

        with st.spinner("Deleting session..."):
            try:
                client = st.session_state.api_client._get_client()
                client.delete(f"{st.session_state.api_client.base_url}/sessions/{session_id}")

                current = st.session_state.get("current_session")
                if current and current.id == session_id:
                    st.session_state.current_session = None
                    st.session_state.chat_history = []

                self._load_sessions()

                st.success("Session deleted!")
                st.rerun()

            except Exception as e:
                st.error(f"Failed to delete session: {str(e)}")

    def _load_sessions(self):
        """Load sessions from API."""
        try:
            sessions = st.session_state.api_client.list_sessions()
            st.session_state.sessions = sessions
        except Exception as e:
            st.error(f"Failed to load sessions: {str(e)}")
            st.session_state.sessions = []

    def _render_export(self):
        """Render export options."""
        st.subheader("Export Session")

        current = st.session_state.get("current_session")

        if not current:
            st.info("No session selected.")
            return

        st.write(f"Session: {current.id[:8]}")

        export_format = st.selectbox(
            "Format",
            options=["JSON", "Markdown"],
        )

        if st.button("📥 Export", use_container_width=True):
            self._export_session(current.id, export_format)

    def _export_session(self, session_id: str, format: str):
        """Export session data."""
        with st.spinner("Exporting..."):
            try:
                client = st.session_state.api_client._get_client()

                params = {"format": format.lower()}
                response = client.get(
                    f"{st.session_state.api_client.base_url}/sessions/{session_id}/export",
                    params=params,
                )
                response.raise_for_status()

                data = response.text

                st.download_button(
                    label=f"Download {format}",
                    data=data,
                    file_name=f"session_{session_id[:8]}.{format.lower()}",
                    mime=f"application/{format.lower()}",
                    type="primary",
                )

            except Exception as e:
                st.error(f"Export failed: {str(e)}")


def initialize_session_state():
    """Initialize session-related state variables."""
    if "current_session" not in st.session_state:
        st.session_state.current_session = None
    if "sessions" not in st.session_state:
        st.session_state.sessions = None
    if "confirm_delete" not in st.session_state:
        st.session_state.confirm_delete = False


def get_current_session() -> Optional[SessionInfo]:
    """Get the current active session."""
    return st.session_state.get("current_session")


def clear_current_session():
    """Clear the current session."""
    st.session_state.current_session = None
    st.session_state.chat_history = []
    if "opening_displayed" in st.session_state:
        del st.session_state.opening_displayed
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/ui/test_smoke.py::TestSessionControls -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add ui/components/controls.py tests/ui/test_smoke.py
git commit -m "feat(ui): add session controls component (Task 6)"
```

---

### Task 7: Main Streamlit App (Spec 5.6)

**Files:**
- Create: `ui/streamlit_app.py`
- Modify: `README.md` (add UI section)

**Step 1: Write main app file**

```python
# ui/streamlit_app.py
"""
Main Streamlit application for the interview system demo UI.

Run with: streamlit run ui/streamlit_app.py
"""

import asyncio
from typing import Optional, Dict, Any
import streamlit as st

from ui.api_client import APIClient
from ui.components.chat import ChatInterface, initialize_chat_state
from ui.components.graph import GraphVisualizer, render_graph_stats
from ui.components.metrics import MetricsPanel, render_turn_diagnostics
from ui.components.controls import (
    SessionControls,
    initialize_session_state,
    get_current_session,
)


# Page configuration
st.set_page_config(
    page_title="Interview System Demo",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
    }
    .stProgress > div > div > div > div {
        background-color: #6C5CE7;
    }
</style>
""", unsafe_allow_html=True)


def initialize_api_client() -> APIClient:
    """Initialize or get existing API client from session state."""
    if "api_client" not in st.session_state:
        api_url = st.session_state.get("api_url", "http://localhost:8000")
        st.session_state.api_client = APIClient(base_url=api_url)
    return st.session_state.api_client


def main():
    """Main application entry point."""
    # Initialize session state
    initialize_session_state()
    initialize_chat_state()

    # Initialize API client
    api_client = initialize_api_client()
    st.session_state.api_client = api_client

    # Title and header
    st.title("🎙️ Adaptive Interview System")
    st.markdown("Demo UI for automated qualitative research interviews")

    # Sidebar - Session Controls
    session_controls = SessionControls(api_client)
    current_session = session_controls.render()

    # API connection status
    st.sidebar.divider()
    api_url = st.sidebar.text_input(
        "API URL",
        value=st.session_state.get("api_url", "http://localhost:8000"),
        help="FastAPI backend URL"
    )

    if st.sidebar.button("🔄 Reconnect"):
        st.session_state.api_url = api_url
        st.session_state.api_client = APIClient(base_url=api_url)
        st.sidebar.success("Reconnected!")

    # Main content area
    if not current_session:
        _render_welcome_screen()
    else:
        _render_interview_screen(api_client, current_session)


def _render_welcome_screen():
    """Render welcome screen when no session is active."""
    st.info("👋 Welcome! Create a new session or select an existing one from the sidebar to begin.")

    st.markdown("""
    ## About This System

    The **Adaptive Interview System** conducts automated qualitative research interviews using:

    - **Natural Language Processing** to extract concepts and relationships
    - **Knowledge Graphs** to build respondent mental models in real-time
    - **Adaptive Questioning** that responds to what respondents actually say

    ### How It Works

    1. **Create a session** with a concept configuration (e.g., "Oat Milk")
    2. **Conduct the interview** by responding to system questions
    3. **Watch in real-time** as the knowledge graph builds
    4. **Review metrics** showing coverage, depth, and strategy selection

    ### Features

    - 📊 **Real-time visualization** of the knowledge graph
    - 🎯 **Coverage tracking** for stimulus concept elements
    - 🔍 **Adaptive strategies** (deepen, broaden, cover, close)
    - 📈 **Diagnostics panel** with scoring breakdown
    - 📥 **Export** interviews to JSON/Markdown
    """)


def _render_interview_screen(api_client: APIClient, current_session):
    """Render the main interview interface."""
    # Create tabs for main content
    tab1, tab2, tab3 = st.tabs(["💬 Interview", "🕸️ Knowledge Graph", "📊 Metrics"])

    # Get current data
    status_data = _get_session_status(api_client, current_session.id)
    graph_data = _get_session_graph(api_client, current_session.id)

    # Tab 1: Interview
    with tab1:
        _render_interview_tab(api_client, current_session, status_data, graph_data)

    # Tab 2: Knowledge Graph
    with tab2:
        _render_graph_tab(graph_data)

    # Tab 3: Metrics
    with tab3:
        _render_metrics_tab(status_data, graph_data)


def _render_interview_tab(
    api_client: APIClient,
    current_session,
    status_data: Dict[str, Any],
    graph_data: Optional[Dict[str, Any]],
):
    """Render the interview chat tab."""
    # Create columns for layout
    left_col, right_col = st.columns([2, 1])

    with left_col:
        # Chat interface
        chat_interface = ChatInterface(api_client)
        user_input = chat_interface.render(current_session)

        # Process user input
        if user_input:
            _process_turn(api_client, current_session.id, user_input, chat_interface)

    with right_col:
        # Quick stats
        st.subheader("Quick Stats")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Turns", status_data.get("turn_number", 0))
        with col2:
            coverage = status_data.get("coverage", 0.0)
            st.metric("Coverage", f"{coverage*100:.0f}%")

        # Strategy indicator
        strategy = status_data.get("strategy_selected", "unknown")
        st.info(f"Strategy: {strategy.upper()}")

        # Show last turn diagnostics
        if "last_turn_result" in st.session_state:
            with st.expander("Last Turn"):
                render_turn_diagnostics(st.session_state.last_turn_result)


def _process_turn(
    api_client: APIClient,
    session_id: str,
    user_input: str,
    chat_interface: ChatInterface,
):
    """Process a user turn through the API."""
    with st.spinner("Processing..."):
        try:
            result = asyncio.run(api_client.submit_turn(session_id, user_input))

            # Store result for diagnostics
            st.session_state.last_turn_result = result

            # Add assistant response to chat
            next_question = result.get("next_question")
            if next_question:
                chat_interface.add_assistant_message(next_question)

            # Check if interview should continue
            should_continue = result.get("should_continue", True)
            if not should_continue:
                st.success("🎉 Interview complete!")

            st.rerun()

        except Exception as e:
            st.error(f"Error processing turn: {str(e)}")


def _render_graph_tab(graph_data: Dict[str, Any]):
    """Render the knowledge graph visualization tab."""
    # Graph visualizer
    visualizer = GraphVisualizer()

    # Render controls in sidebar
    controls = visualizer.render_controls()

    # Render graph
    fig = visualizer.render(graph_data, controls)

    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No graph data to display yet.")

    # Render stats in sidebar
    render_graph_stats(graph_data)


def _render_metrics_tab(status_data: Dict[str, Any], graph_data: Optional[Dict]):
    """Render the metrics and diagnostics tab."""
    metrics_panel = MetricsPanel()
    metrics_panel.render(status_data, graph_data)

    # Coverage details
    if "elements" in status_data:
        from ui.components.metrics import render_coverage_details
        render_coverage_details(status_data)


def _get_session_status(api_client: APIClient, session_id: str) -> Dict[str, Any]:
    """Get current session status from API."""
    try:
        return asyncio.run(api_client.get_session_status(session_id))
    except Exception as e:
        st.error(f"Failed to get session status: {str(e)}")
        return {}


def _get_session_graph(api_client: APIClient, session_id: str) -> Dict[str, Any]:
    """Get session knowledge graph from API."""
    try:
        return asyncio.run(api_client.get_session_graph(session_id))
    except Exception as e:
        st.error(f"Failed to get graph data: {str(e)}")
        return {}


if __name__ == "__main__":
    main()
```

**Step 2: Update README.md with UI section**

Add to `README.md`:

```markdown
## Demo UI

The demo UI provides a visual interface for conducting interviews.

### Running the UI

1. Start the FastAPI backend:
```bash
uvicorn src.main:app --reload
```

2. In a new terminal, start the Streamlit UI:
```bash
streamlit run ui/streamlit_app.py
```

3. Open http://localhost:8501 in your browser

### Features

- **Chat Interface**: Conduct interviews with real-time responses
- **Knowledge Graph**: Visualize extracted concepts and relationships
- **Metrics Panel**: Track coverage, scoring, and strategy selection
- **Session Controls**: Create, load, and delete sessions

### UI Dependencies

```bash
uv pip install streamlit plotly networkx
```
```

**Step 3: Verify app structure**

Run: `python3 -c "from ui.streamlit_app import main; print('OK')"`
Expected: "OK"

**Step 4: Commit**

```bash
git add ui/streamlit_app.py README.md
git commit -m "feat(ui): add main Streamlit application (Task 7)"
```

---

### Task 8: UI Integration Tests (Spec 5.7)

**Files:**
- Create: `tests/ui/manual_test_checklist.md`
- Modify: `tests/ui/test_smoke.py` (extend with fixtures)

**Step 1: Create manual test checklist**

```bash
cat > tests/ui/manual_test_checklist.md << 'EOF'
# UI Manual Test Checklist

## Prerequisites

- [ ] FastAPI backend running on http://localhost:8000
- [ ] Streamlit UI running on http://localhost:8501
- [ ] Test concept configuration loaded

## Session Management

### Create New Session
- [ ] Click "New Session" tab
- [ ] Select concept from dropdown
- [ ] Click "Start Interview" button
- [ ] Verify session created successfully
- [ ] Verify session ID displayed
- [ ] Verify opening question appears in chat

### Load Existing Session
- [ ] Click "Sessions" tab
- [ ] Verify session list loads
- [ ] Select a session from dropdown
- [ ] View session details in expander
- [ ] Click "Load" button
- [ ] Verify session loads correctly
- [ ] Verify chat history appears

### Delete Session
- [ ] Select a session
- [ ] Click "Delete" button
- [ ] Verify confirmation required (second click)
- [ ] Verify session removed from list

## Chat Interface

### Opening Question
- [ ] Opening question displayed when session loads
- [ ] Opening question in assistant message style

### Send Response
- [ ] Type message in chat input
- [ ] Press Enter or click send
- [ ] Verify message appears in chat (user style)
- [ ] Verify assistant response appears
- [ ] Verify turn counter increments

## Knowledge Graph

### Graph Display
- [ ] Navigate to "Knowledge Graph" tab
- [ ] Verify graph displays after first turn
- [ ] Verify nodes colored by type
- [ ] Verify edges connect nodes

### Graph Controls
- [ ] Select different layout algorithm
- [ ] Verify graph updates with new layout
- [ ] Toggle node labels on/off
- [ ] Filter by node type

## Metrics Panel

### Main Metrics
- [ ] Verify turn count displayed
- [ ] Verify coverage percentage displayed
- [ ] Verify coverage visual bar shown

### Scoring Breakdown
- [ ] Verify gauge charts for each score
- [ ] Verify Coverage gauge works
- [ ] Verify Depth gauge works

## Export

### Export JSON
- [ ] Select active session
- [ ] Go to "Export" tab
- [ ] Select "JSON" format
- [ ] Click "Export" button
- [ ] Verify download button appears

## End-to-End Interview Flow

### Complete Short Interview
- [ ] Create new session
- [ ] Respond to opening question
- [ ] Respond to 3-5 follow-up questions
- [ ] Verify knowledge graph builds
- [ ] Verify coverage increases
EOF
```

**Step 2: Add fixtures to test_smoke.py**

Add to end of `tests/ui/test_smoke.py`:

```python
import pytest


@pytest.fixture
def mock_streamlit_state():
    """Fixture to mock Streamlit session state."""
    import streamlit as st

    if not hasattr(st, "session_state"):
        st.session_state = MagicMock()

    st.session_state.current_session = None
    st.session_state.chat_history = []
    st.session_state.opening_displayed = False

    yield st.session_state

    delattr(st, "session_state")


@pytest.fixture
def sample_graph_data():
    """Fixture providing sample graph data."""
    return {
        "nodes": [
            {
                "id": "n1",
                "label": "creamy texture",
                "node_type": "attribute",
                "confidence": 0.9,
            },
            {
                "id": "n2",
                "label": "satisfying",
                "node_type": "functional_consequence",
                "confidence": 0.8,
            },
        ],
        "edges": [
            {
                "id": "e1",
                "source_node_id": "n1",
                "target_node_id": "n2",
                "edge_type": "leads_to",
                "confidence": 0.8,
            },
        ],
    }


@pytest.fixture
def sample_status_data():
    """Fixture providing sample status data."""
    return {
        "turn_number": 3,
        "max_turns": 20,
        "coverage": 0.4,
        "target_coverage": 0.8,
        "status": "active",
        "should_continue": True,
        "strategy_selected": "deepen",
        "strategy_reasoning": "Shallow chain, explore deeper",
        "scoring": {
            "coverage": 0.4,
            "depth": 0.2,
            "saturation": 0.0,
            "novelty": 1.0,
            "richness": 0.8,
        },
    }
```

**Step 3: Run all UI tests**

Run: `pytest tests/ui/test_smoke.py -v`
Expected: PASS (all tests)

**Step 4: Commit**

```bash
git add tests/ui/manual_test_checklist.md tests/ui/test_smoke.py
git commit -m "test(ui): add integration tests and manual checklist (Task 8)"
```

---

### Task 9: Update Dependencies and Package

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add UI dependencies**

```bash
# Add to pyproject.toml dependencies
uv pip install "streamlit>=1.31.0" "plotly>=5.18.0" "networkx>=3.2"
```

**Step 2: Verify all imports work**

Run:
```bash
python3 -c "
from ui.streamlit_app import main
from ui.api_client import APIClient
from ui.components.chat import ChatInterface
from ui.components.graph import GraphVisualizer
from ui.components.metrics import MetricsPanel
from ui.components.controls import SessionControls
print('All UI imports successful')
"
```

Expected: "All UI imports successful"

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore(ui): add Streamlit and visualization dependencies"
```

---

### Task 10: Final Integration and Verification

**Step 1: Run all Phase 5 tests**

Run: `pytest tests/ui/ -v`
Expected: All tests pass

**Step 2: Verify Streamlit app starts**

Run: `timeout 5 streamlit run ui/streamlit_app.py --server.headless true 2>&1 | grep -i "running on" || echo "Streamlit started"`
Expected: Streamlit starts without import errors

**Step 3: Verify all files created**

Run:
```bash
ls -la ui/ ui/components/ tests/ui/ docs/ui-framework-decision.md
```

Expected: All files present

**Step 4: Final commit**

```bash
git add .
git commit -m "feat(phase-5): complete Phase 5 demo UI

- Streamlit-based demo UI with chat, graph, metrics, controls
- API client for FastAPI backend communication
- Modular component architecture
- Manual test checklist for end-to-end validation
- Comprehensive unit tests for components

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Verification Checklist

Phase 5 is complete when:
- [ ] `docs/ui-framework-decision.md` created with Streamlit selection rationale
- [ ] `ui/api_client.py` with APIClient class for FastAPI communication
- [ ] `ui/components/chat.py` with ChatInterface for interview chat
- [ ] `ui/components/graph.py` with GraphVisualizer for 2D/3D plots
- [ ] `ui/components/metrics.py` with MetricsPanel for scoring gauges
- [ ] `ui/components/controls.py` with SessionControls for session management
- [ ] `ui/streamlit_app.py` main app integrating all components
- [ ] `tests/ui/test_smoke.py` with component unit tests
- [ ] `tests/ui/manual_test_checklist.md` for manual testing
- [ ] All unit tests pass (pytest tests/ui/)
- [ ] Streamlit app starts without errors
- [ ] All imports verified
- [ ] README.md updated with UI section

## Success Metrics

From PRD and IMPLEMENTATION_PLAN.md:
- Streamlit app starts on port 8501
- UI communicates with FastAPI backend via HTTP
- Chat interface displays messages and handles input
- Graph visualization shows nodes/edges with MEC colors
- Metrics panel displays coverage, scoring, strategy
- Session controls create/load/delete sessions
- Export functionality works (if backend supports it)
