"""Integration tests for turn processing API."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.persistence.database import init_database


@pytest.fixture
async def test_db():
    """Create test database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        await init_database(db_path)

        # Patch settings to use test db
        with patch("src.core.config.settings") as mock_settings:
            mock_settings.database_path = db_path
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.llm_model = "claude-sonnet-4-20250514"
            mock_settings.llm_timeout_seconds = 30.0
            mock_settings.llm_temperature = 0.7
            mock_settings.llm_max_tokens = 1024
            mock_settings.llm_provider = "anthropic"
            yield db_path


@pytest.fixture
async def client(test_db):
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def session_id(client):
    """Create a test session."""
    response = await client.post(
        "/sessions",
        json={
            "concept_id": "test-concept",
            "config": {"concept_name": "Test Product"},
        },
    )
    return response.json()["id"]


class TestProcessTurnEndpoint:
    """Tests for POST /sessions/{id}/turns."""

    @pytest.mark.asyncio
    async def test_process_turn_returns_200(self, client, session_id):
        """Returns 200 with turn result."""
        # Mock LLM calls
        with patch(
            "src.services.extraction_service.ExtractionService.extract"
        ) as mock_extract:
            with patch(
                "src.services.question_service.QuestionService.generate_question"
            ) as mock_question:
                mock_extract.return_value = AsyncMock(
                    concepts=[],
                    relationships=[],
                    is_extractable=True,
                    discourse_markers=[],
                    latency_ms=100,
                )()
                mock_question.return_value = "Why is that important?"

                response = await client.post(
                    f"/sessions/{session_id}/turns",
                    json={"text": "I like the taste"},
                )

        assert response.status_code == 200
        data = response.json()
        assert "turn_number" in data
        assert "next_question" in data
        assert "should_continue" in data

    @pytest.mark.asyncio
    async def test_process_turn_404_for_unknown_session(self, client):
        """Returns 404 for unknown session."""
        response = await client.post(
            "/sessions/nonexistent/turns",
            json={"text": "Hello"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_process_turn_validates_text(self, client, session_id):
        """Validates text is not empty."""
        response = await client.post(
            f"/sessions/{session_id}/turns",
            json={"text": ""},
        )

        assert response.status_code == 422  # Validation error


class TestStartSessionEndpoint:
    """Tests for POST /sessions/{id}/start."""

    @pytest.mark.asyncio
    async def test_start_session_returns_question(self, client, session_id):
        """Returns opening question."""
        with patch(
            "src.services.question_service.QuestionService.generate_opening_question"
        ) as mock:
            mock.return_value = "What do you think about Test Product?"

            response = await client.post(f"/sessions/{session_id}/start")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "opening_question" in data

    @pytest.mark.asyncio
    async def test_start_session_404_for_unknown(self, client):
        """Returns 404 for unknown session."""
        response = await client.post("/sessions/unknown/start")

        assert response.status_code == 404
