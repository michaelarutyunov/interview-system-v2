"""Integration tests for synthetic API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock

from src.main import app
from src.llm.client import LLMResponse


class TestSyntheticRespondEndpoint:
    """Tests for POST /synthetic/respond."""

    @pytest.mark.asyncio
    async def test_generate_synthetic_response_success(self):
        """Endpoint returns synthetic response."""
        mock_llm_response = LLMResponse(
            content="I really like the creamy texture because it feels satisfying.",
            model="claude-sonnet-4-20250514",
            usage={"input_tokens": 100, "output_tokens": 20},
            latency_ms=150.0,
        )

        with patch("src.services.synthetic_service.get_llm_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.complete.return_value = mock_llm_response
            mock_get_client.return_value = mock_client

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/synthetic/respond",
                    json={
                        "question": "Why is creamy texture important to you?",
                        "session_id": "test-session-123",
                        "persona": "health_conscious",
                    },
                )

            assert response.status_code == 200
            data = response.json()
            assert data["response"] == "I really like the creamy texture because it feels satisfying."
            assert data["persona"] == "health_conscious"
            assert "Health-Conscious" in data["persona_name"]
            assert data["latency_ms"] == 150.0

    @pytest.mark.asyncio
    async def test_invalid_persona_returns_400(self):
        """Endpoint returns 400 for invalid persona."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/synthetic/respond",
                json={
                    "question": "Test question?",
                    "session_id": "test-session",
                    "persona": "invalid_persona",
                },
            )

        assert response.status_code == 400
        assert "Unknown persona" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_with_interview_context(self):
        """Endpoint includes interview context in generation."""
        mock_llm_response = LLMResponse(
            content="I think it's great.",
            model="claude-sonnet-4-20250514",
            usage={"input_tokens": 90, "output_tokens": 15},
            latency_ms=120.0,
        )

        with patch("src.services.synthetic_service.get_llm_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.complete.return_value = mock_llm_response
            mock_get_client.return_value = mock_client

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/synthetic/respond",
                    json={
                        "question": "What do you think?",
                        "session_id": "test-session",
                        "interview_context": {
                            "product_name": "Oat Milk",
                            "turn_number": 5,
                            "coverage_achieved": 0.6,
                        },
                    },
                )

            assert response.status_code == 200


class TestMultiSyntheticEndpoint:
    """Tests for POST /synthetic/respond/multi."""

    @pytest.mark.asyncio
    async def test_generate_multi_response(self):
        """Endpoint returns multiple responses."""
        mock_llm_response = LLMResponse(
            content="It's important because...",
            model="claude-sonnet-4-20250514",
            usage={"input_tokens": 100, "output_tokens": 20},
            latency_ms=150.0,
        )

        with patch("src.services.synthetic_service.get_llm_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.complete.return_value = mock_llm_response
            mock_get_client.return_value = mock_client

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/synthetic/respond/multi",
                    json={
                        "question": "Why does quality matter?",
                        "session_id": "test-session",
                        "personas": ["health_conscious", "price_sensitive"],
                    },
                )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2
            assert data[0]["persona"] == "health_conscious"
            assert data[1]["persona"] == "price_sensitive"


class TestInterviewSequenceEndpoint:
    """Tests for POST /synthetic/respond/sequence."""

    @pytest.mark.asyncio
    async def test_generate_interview_sequence(self):
        """Endpoint returns full interview sequence."""
        mock_llm_response = LLMResponse(
            content="That's a good question.",
            model="claude-sonnet-4-20250514",
            usage={"input_tokens": 100, "output_tokens": 20},
            latency_ms=150.0,
        )

        with patch("src.services.synthetic_service.get_llm_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.complete.return_value = mock_llm_response
            mock_get_client.return_value = mock_client

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/synthetic/respond/sequence",
                    json={
                        "questions": [
                            "What comes to mind?",
                            "Why is that important?",
                            "What else matters?",
                        ],
                        "session_id": "test-session",
                        "persona": "quality_focused",
                        "product_name": "Oat Milk",
                    },
                )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 3
            assert all(r["persona"] == "quality_focused" for r in data)


class TestListPersonasEndpoint:
    """Tests for GET /synthetic/personas."""

    @pytest.mark.asyncio
    async def test_list_personas(self):
        """Endpoint returns available personas."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/synthetic/personas")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "health_conscious" in data
        assert data["health_conscious"] == "Health-Conscious Millennial"
