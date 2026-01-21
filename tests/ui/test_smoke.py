# tests/ui/test_smoke.py
"""Smoke tests for UI components."""

import pytest

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
            created_at="2025-01-21T10:00:00Z"
        )
        assert info.id == "test-123"
        assert info.concept_id == "oat_milk_v1"
        assert info.status == "active"
        assert info.opening_question == "What do you think?"
