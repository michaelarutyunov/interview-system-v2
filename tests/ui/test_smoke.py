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
