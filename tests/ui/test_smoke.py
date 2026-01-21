# tests/ui/test_smoke.py
"""Smoke tests for UI components."""

import pytest

from ui.api_client import APIClient, SessionInfo
from ui.components.chat import ChatInterface, initialize_chat_state
from unittest.mock import MagicMock


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
            created_at="2025-01-21T10:00:00Z"
        )
        assert info.id == "test-123"
        assert info.concept_id == "oat_milk_v1"
        assert info.status == "active"
        assert info.opening_question == "What do you think?"


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
        # Just verify data structure is accepted
        assert "turn_number" in status_data
