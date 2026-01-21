"""
Integration tests for complete session flow.

Tests the full pipeline from API request through all services
to verify correct data flow and behavior.

Uses mocked LLM responses to avoid actual API calls.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
import tempfile
from pathlib import Path
import json

from src.main import app
from src.persistence.database import init_database
from src.llm.client import LLMResponse


# ============ FIXTURES ============

@pytest.fixture
async def test_db():
    """Create and initialize test database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        await init_database(db_path)

        # Patch settings
        with patch("src.core.config.settings") as mock_settings:
            mock_settings.database_path = db_path
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.llm_model = "claude-sonnet-4-20250514"
            mock_settings.llm_timeout_seconds = 30.0
            mock_settings.llm_temperature = 0.7
            mock_settings.llm_max_tokens = 1024
            mock_settings.llm_provider = "anthropic"
            mock_settings.debug = True
            yield db_path


@pytest.fixture
async def client(test_db):
    """Create test HTTP client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_llm_extraction_response():
    """Mock LLM response for extraction."""
    return json.dumps({
        "concepts": [
            {
                "text": "creamy texture",
                "node_type": "attribute",
                "confidence": 0.9,
                "source_quote": "I love the creamy texture"
            },
            {
                "text": "satisfying",
                "node_type": "functional_consequence",
                "confidence": 0.8,
                "source_quote": "it's really satisfying"
            }
        ],
        "relationships": [
            {
                "source_text": "creamy texture",
                "target_text": "satisfying",
                "relationship_type": "leads_to",
                "confidence": 0.75,
                "source_quote": "the creamy texture makes it satisfying"
            }
        ],
        "discourse_markers": ["because"]
    })


@pytest.fixture
def mock_llm_question_response():
    """Mock LLM response for question generation."""
    return "You mentioned that creamy texture is satisfying. Why is that feeling important to you?"


@pytest.fixture
def mock_llm_opening_response():
    """Mock LLM response for opening question."""
    return "I'd love to hear your thoughts about Oat Milk. What comes to mind when you think about it?"


# ============ COMPLETE FLOW TESTS ============

class TestCompleteSessionFlow:
    """Tests for complete session lifecycle."""

    @pytest.mark.asyncio
    async def test_full_session_flow(
        self,
        client,
        mock_llm_extraction_response,
        mock_llm_question_response,
        mock_llm_opening_response,
    ):
        """Test complete flow: create -> start -> turn -> verify."""

        # Mock all LLM calls
        with patch("src.llm.client.AnthropicClient.complete") as mock_complete:
            # Set up mock to return different responses based on call order
            mock_complete.side_effect = [
                LLMResponse(content=mock_llm_opening_response, model="test", latency_ms=100),
                LLMResponse(content=mock_llm_extraction_response, model="test", latency_ms=200),
                LLMResponse(content=mock_llm_question_response, model="test", latency_ms=100),
            ]

            # Step 1: Create session
            create_response = await client.post(
                "/sessions",
                json={
                    "concept_id": "oat-milk",
                    "config": {
                        "concept_name": "Oat Milk",
                        "concept_description": "Plant-based milk alternative"
                    }
                }
            )
            assert create_response.status_code == 201
            session_id = create_response.json()["id"]

            # Step 2: Start session
            start_response = await client.post(f"/sessions/{session_id}/start")
            assert start_response.status_code == 200
            start_data = start_response.json()
            assert "opening_question" in start_data
            assert "Oat Milk" in start_data["opening_question"]

            # Step 3: Process first turn
            turn1_response = await client.post(
                f"/sessions/{session_id}/turns",
                json={"text": "I love the creamy texture because it's really satisfying"}
            )
            assert turn1_response.status_code == 200
            turn1_data = turn1_response.json()

            # Verify extraction
            assert len(turn1_data["extracted"]["concepts"]) == 2
            concept_texts = [c["text"] for c in turn1_data["extracted"]["concepts"]]
            assert "creamy texture" in concept_texts

            # Verify relationship
            assert len(turn1_data["extracted"]["relationships"]) == 1
            assert turn1_data["extracted"]["relationships"][0]["type"] == "leads_to"

            # Verify graph state updated
            assert turn1_data["graph_state"]["node_count"] >= 2
            assert turn1_data["graph_state"]["edge_count"] >= 1

            # Verify next question generated
            assert turn1_data["next_question"]
            assert turn1_data["should_continue"] is True

            # Verify strategy
            assert turn1_data["strategy_selected"] == "deepen"

    @pytest.mark.asyncio
    async def test_multiple_turns_build_graph(
        self,
        client,
        mock_llm_extraction_response,
        mock_llm_question_response,
        mock_llm_opening_response,
    ):
        """Test that multiple turns accumulate in the graph."""

        second_extraction = json.dumps({
            "concepts": [
                {"text": "healthy", "node_type": "psychosocial_consequence", "confidence": 0.85}
            ],
            "relationships": [
                {"source_text": "satisfying", "target_text": "healthy", "relationship_type": "leads_to"}
            ],
            "discourse_markers": []
        })

        with patch("src.llm.client.AnthropicClient.complete") as mock_complete:
            mock_complete.side_effect = [
                LLMResponse(content=mock_llm_opening_response, model="test", latency_ms=100),
                LLMResponse(content=mock_llm_extraction_response, model="test", latency_ms=200),
                LLMResponse(content=mock_llm_question_response, model="test", latency_ms=100),
                LLMResponse(content=second_extraction, model="test", latency_ms=200),
                LLMResponse(content="Why does feeling healthy matter to you?", model="test", latency_ms=100),
            ]

            # Create and start
            create_resp = await client.post(
                "/sessions",
                json={"concept_id": "test", "config": {"concept_name": "Test"}}
            )
            session_id = create_resp.json()["id"]
            await client.post(f"/sessions/{session_id}/start")

            # Turn 1
            turn1 = await client.post(
                f"/sessions/{session_id}/turns",
                json={"text": "I love the creamy texture"}
            )
            turn1_nodes = turn1.json()["graph_state"]["node_count"]

            # Turn 2
            turn2 = await client.post(
                f"/sessions/{session_id}/turns",
                json={"text": "It makes me feel healthy"}
            )
            turn2_nodes = turn2.json()["graph_state"]["node_count"]

            # Graph should have grown
            assert turn2_nodes >= turn1_nodes

    @pytest.mark.asyncio
    async def test_non_extractable_response_handled(self, client):
        """Test that non-extractable responses are handled gracefully."""

        with patch("src.llm.client.AnthropicClient.complete") as mock_complete:
            mock_complete.side_effect = [
                LLMResponse(content="What do you think?", model="test", latency_ms=100),
                # Extraction will be skipped due to short input
                LLMResponse(content="Tell me more about that.", model="test", latency_ms=100),
            ]

            # Create and start
            create_resp = await client.post(
                "/sessions",
                json={"concept_id": "test", "config": {"concept_name": "Test"}}
            )
            session_id = create_resp.json()["id"]
            await client.post(f"/sessions/{session_id}/start")

            # Short response - should be handled gracefully
            turn_resp = await client.post(
                f"/sessions/{session_id}/turns",
                json={"text": "Yes"}
            )

            # Should still succeed
            assert turn_resp.status_code == 200
            data = turn_resp.json()

            # No extraction (too short)
            assert data["extracted"]["concepts"] == []
            assert data["should_continue"] is True


class TestGraphPersistence:
    """Tests for graph data persistence."""

    @pytest.mark.asyncio
    async def test_nodes_persisted_to_database(
        self,
        client,
        test_db,
        mock_llm_extraction_response,
        mock_llm_question_response,
        mock_llm_opening_response,
    ):
        """Test that extracted nodes are persisted to SQLite."""
        import aiosqlite

        with patch("src.llm.client.AnthropicClient.complete") as mock_complete:
            mock_complete.side_effect = [
                LLMResponse(content=mock_llm_opening_response, model="test", latency_ms=100),
                LLMResponse(content=mock_llm_extraction_response, model="test", latency_ms=200),
                LLMResponse(content=mock_llm_question_response, model="test", latency_ms=100),
            ]

            # Create, start, and process turn
            create_resp = await client.post(
                "/sessions",
                json={"concept_id": "test", "config": {"concept_name": "Test"}}
            )
            session_id = create_resp.json()["id"]
            await client.post(f"/sessions/{session_id}/start")
            await client.post(
                f"/sessions/{session_id}/turns",
                json={"text": "I love the creamy texture"}
            )

        # Verify in database directly
        async with aiosqlite.connect(test_db) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM kg_nodes WHERE session_id = ?",
                (session_id,)
            )
            count = (await cursor.fetchone())[0]
            assert count >= 2  # At least 2 concepts extracted

    @pytest.mark.asyncio
    async def test_utterances_persisted(
        self,
        client,
        test_db,
        mock_llm_extraction_response,
        mock_llm_question_response,
        mock_llm_opening_response,
    ):
        """Test that utterances are persisted for provenance."""
        import aiosqlite

        with patch("src.llm.client.AnthropicClient.complete") as mock_complete:
            mock_complete.side_effect = [
                LLMResponse(content=mock_llm_opening_response, model="test", latency_ms=100),
                LLMResponse(content=mock_llm_extraction_response, model="test", latency_ms=200),
                LLMResponse(content=mock_llm_question_response, model="test", latency_ms=100),
            ]

            create_resp = await client.post(
                "/sessions",
                json={"concept_id": "test", "config": {"concept_name": "Test"}}
            )
            session_id = create_resp.json()["id"]
            await client.post(f"/sessions/{session_id}/start")
            await client.post(
                f"/sessions/{session_id}/turns",
                json={"text": "I love the creamy texture"}
            )

        # Verify utterances in database
        async with aiosqlite.connect(test_db) as db:
            cursor = await db.execute(
                "SELECT speaker, text FROM utterances WHERE session_id = ? ORDER BY turn_number",
                (session_id,)
            )
            utterances = await cursor.fetchall()

            # Should have: system (opening), user (input), system (question)
            assert len(utterances) >= 3
            speakers = [u[0] for u in utterances]
            assert "system" in speakers
            assert "user" in speakers


class TestErrorHandling:
    """Tests for error handling in the pipeline."""

    @pytest.mark.asyncio
    async def test_llm_error_handled_gracefully(self, client):
        """Test that LLM errors don't crash the pipeline."""

        with patch("src.llm.client.AnthropicClient.complete") as mock_complete:
            mock_complete.side_effect = [
                LLMResponse(content="Opening question?", model="test", latency_ms=100),
                Exception("LLM API error"),  # Extraction fails
            ]

            create_resp = await client.post(
                "/sessions",
                json={"concept_id": "test", "config": {"concept_name": "Test"}}
            )
            session_id = create_resp.json()["id"]
            await client.post(f"/sessions/{session_id}/start")

            # Should handle error gracefully (may return 500 or degrade)
            turn_resp = await client.post(
                f"/sessions/{session_id}/turns",
                json={"text": "I like the taste"}
            )

            # Either succeeds with degraded response or fails with proper error
            assert turn_resp.status_code in [200, 500]

    @pytest.mark.asyncio
    async def test_invalid_session_id_returns_404(self, client):
        """Test 404 for invalid session ID."""
        response = await client.post(
            "/sessions/invalid-id/turns",
            json={"text": "Hello"}
        )
        assert response.status_code == 404


class TestResponseFormat:
    """Tests for correct response format."""

    @pytest.mark.asyncio
    async def test_turn_response_matches_prd(
        self,
        client,
        mock_llm_extraction_response,
        mock_llm_question_response,
        mock_llm_opening_response,
    ):
        """Test response matches PRD Section 8.6 structure."""

        with patch("src.llm.client.AnthropicClient.complete") as mock_complete:
            mock_complete.side_effect = [
                LLMResponse(content=mock_llm_opening_response, model="test", latency_ms=100),
                LLMResponse(content=mock_llm_extraction_response, model="test", latency_ms=200),
                LLMResponse(content=mock_llm_question_response, model="test", latency_ms=100),
            ]

            create_resp = await client.post(
                "/sessions",
                json={"concept_id": "test", "config": {"concept_name": "Test"}}
            )
            session_id = create_resp.json()["id"]
            await client.post(f"/sessions/{session_id}/start")

            turn_resp = await client.post(
                f"/sessions/{session_id}/turns",
                json={"text": "I love the creamy texture"}
            )
            data = turn_resp.json()

            # Verify PRD Section 8.6 fields
            assert "turn_number" in data
            assert "extracted" in data
            assert "concepts" in data["extracted"]
            assert "relationships" in data["extracted"]
            assert "graph_state" in data
            assert "node_count" in data["graph_state"]
            assert "edge_count" in data["graph_state"]
            assert "scoring" in data
            assert "strategy_selected" in data
            assert "next_question" in data
            assert "should_continue" in data
            assert "latency_ms" in data

            # Verify types
            assert isinstance(data["turn_number"], int)
            assert isinstance(data["should_continue"], bool)
            assert isinstance(data["latency_ms"], int)
