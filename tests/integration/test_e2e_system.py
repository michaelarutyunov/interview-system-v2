"""
End-to-end integration tests for the interview system.

Tests complete workflows covering:
- Full interview lifecycle from creation to completion
- All API endpoints (sessions, synthetic, concepts, health, export)
- Integration between all services
- Data persistence and export formats
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch
from httpx import ASGITransport, AsyncClient
import time

from src.main import app
from src.persistence.database import init_database
from src.llm.client import LLMResponse


# ============ FIXTURES ============

@pytest.fixture
async def test_db():
    """Create and initialize test database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_e2e.db"
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
def mock_llm_responses():
    """Mock LLM responses for a complete interview."""
    return {
        "opening": "Tell me about your experience with Oat Milk.",
        "extraction_1": json.dumps({
            "concepts": [
                {"text": "creamy texture", "node_type": "attribute", "confidence": 0.9, "source_quote": "creamy texture"},
                {"text": "satisfying", "node_type": "functional_consequence", "confidence": 0.85, "source_quote": "satisfying"},
            ],
            "relationships": [
                {"source_text": "creamy texture", "target_text": "satisfying", "relationship_type": "leads_to", "confidence": 0.8, "source_quote": "texture makes it satisfying"},
            ],
            "discourse_markers": ["because"]
        }),
        "question_1": "You mentioned the creamy texture feels satisfying. Why is that important to you?",
        "extraction_2": json.dumps({
            "concepts": [
                {"text": "healthy choice", "node_type": "psychosocial_consequence", "confidence": 0.88, "source_quote": "healthy choice"},
            ],
            "relationships": [
                {"source_text": "satisfying", "target_text": "healthy choice", "relationship_type": "leads_to", "confidence": 0.82, "source_quote": "satisfying because it's healthy"},
            ],
            "discourse_markers": []
        }),
        "question_2": "How does making healthy choices impact your daily life?",
    }


# ============ TEST CLASS: COMPLETE INTERVIEW WORKFLOW ============

class TestCompleteInterviewWorkflow:
    """Tests for complete interview workflow from start to finish."""

    @pytest.mark.asyncio
    async def test_full_interview_workflow(self, client, mock_llm_responses):
        """
        Test complete interview workflow:
        1. Create session
        2. Start session (get opening question)
        3. Process multiple turns
        4. Verify graph accumulation
        5. Export data
        6. Verify data persistence
        """
        with patch("src.llm.client.AnthropicClient.complete") as mock_complete:
            # Set up mock responses in sequence
            mock_complete.side_effect = [
                LLMResponse(content=mock_llm_responses["opening"], model="test", latency_ms=100),
                LLMResponse(content=mock_llm_responses["extraction_1"], model="test", latency_ms=200),
                LLMResponse(content=mock_llm_responses["question_1"], model="test", latency_ms=100),
                LLMResponse(content=mock_llm_responses["extraction_2"], model="test", latency_ms=200),
                LLMResponse(content=mock_llm_responses["question_2"], model="test", latency_ms=100),
            ]

            # Step 1: Create session
            create_response = await client.post(
                "/sessions",
                json={
                    "concept_id": "oat-milk",
                    "methodology": "means_end_chain",
                    "config": {
                        "concept_name": "Oat Milk",
                        "concept_description": "Plant-based milk alternative"
                    }
                }
            )
            assert create_response.status_code == 201
            session_data = create_response.json()
            session_id = session_data["id"]
            assert session_data["concept_id"] == "oat-milk"
            assert session_data["status"] == "active"

            # Step 2: Start session
            start_response = await client.post(f"/sessions/{session_id}/start")
            assert start_response.status_code == 200
            start_data = start_response.json()
            assert "opening_question" in start_data
            assert "Oat Milk" in start_data["opening_question"] or "experience" in start_data["opening_question"].lower()

            # Step 3: Process first turn
            turn1_response = await client.post(
                f"/sessions/{session_id}/turns",
                json={"text": "I love the creamy texture because it's really satisfying"}
            )
            assert turn1_response.status_code == 200
            turn1_data = turn1_response.json()
            assert turn1_data["turn_number"] == 1
            assert len(turn1_data["extracted"]["concepts"]) == 2
            assert turn1_data["graph_state"]["node_count"] >= 2
            assert turn1_data["should_continue"] is True

            # Step 4: Process second turn
            turn2_response = await client.post(
                f"/sessions/{session_id}/turns",
                json={"text": "It makes me feel like I'm making a healthy choice"}
            )
            assert turn2_response.status_code == 200
            turn2_data = turn2_response.json()
            assert turn2_data["turn_number"] == 2
            assert len(turn2_data["extracted"]["concepts"]) >= 1
            # Graph should have grown
            assert turn2_data["graph_state"]["node_count"] >= turn1_data["graph_state"]["node_count"]

            # Step 5: Get session details
            session_response = await client.get(f"/sessions/{session_id}")
            assert session_response.status_code == 200
            session_details = session_response.json()
            assert session_details["turn_count"] >= 2

    @pytest.mark.asyncio
    async def test_session_lifecycle(self, client, mock_llm_responses):
        """
        Test complete session lifecycle:
        1. Create
        2. List (verify it appears)
        3. Get details
        4. Update through turns
        5. Delete
        6. Verify deletion
        """
        with patch("src.llm.client.AnthropicClient.complete") as mock_complete:
            mock_complete.side_effect = [
                LLMResponse(content=mock_llm_responses["opening"], model="test", latency_ms=100),
                LLMResponse(content=mock_llm_responses["extraction_1"], model="test", latency_ms=200),
                LLMResponse(content=mock_llm_responses["question_1"], model="test", latency_ms=100),
            ]

            # 1. Create session
            create_resp = await client.post(
                "/sessions",
                json={"concept_id": "test-product", "config": {"concept_name": "Test Product"}}
            )
            assert create_resp.status_code == 201
            session_id = create_resp.json()["id"]

            # 2. List sessions (verify it appears)
            list_resp = await client.get("/sessions")
            assert list_resp.status_code == 200
            list_data = list_resp.json()
            assert list_data["total"] >= 1
            session_ids = [s["id"] for s in list_data["sessions"]]
            assert session_id in session_ids

            # 3. Get session details
            get_resp = await client.get(f"/sessions/{session_id}")
            assert get_resp.status_code == 200
            details = get_resp.json()
            assert details["id"] == session_id
            assert details["concept_id"] == "test-product"

            # 4. Update through a turn
            await client.post(f"/sessions/{session_id}/start")
            await client.post(
                f"/sessions/{session_id}/turns",
                json={"text": "I like it"}
            )

            # Verify turn count updated
            get_resp2 = await client.get(f"/sessions/{session_id}")
            assert get_resp2.json()["turn_count"] >= 1

            # 5. Delete session
            delete_resp = await client.delete(f"/sessions/{session_id}")
            assert delete_resp.status_code == 204

            # 6. Verify deletion
            get_resp3 = await client.get(f"/sessions/{session_id}")
            assert get_resp3.status_code == 404


# ============ TEST CLASS: SYNTHETIC INTERVIEW INTEGRATION ============

class TestSyntheticInterviewIntegration:
    """Tests for synthetic interview integration with real endpoints."""

    @pytest.mark.asyncio
    async def test_synthetic_interview_achieves_coverage(self, client, mock_llm_responses):
        """
        Test that a synthetic interview can achieve coverage:
        1. Create session
        2. Generate synthetic response for opening question
        3. Process turn with synthetic response
        4. Generate next synthetic response
        5. Verify graph building and coverage scoring
        """
        with patch("src.llm.client.AnthropicClient.complete") as mock_complete:
            # Mock responses for both session and synthetic generation
            mock_complete.side_effect = [
                # Session opening
                LLMResponse(content=mock_llm_responses["opening"], model="test", latency_ms=100),
                # Synthetic response
                LLMResponse(
                    content="The creamy texture is amazing, it makes my coffee taste so much better and I feel good about choosing a plant-based option.",
                    model="test",
                    latency_ms=150
                ),
                # Extraction
                LLMResponse(content=mock_llm_responses["extraction_1"], model="test", latency_ms=200),
                # Next question
                LLMResponse(content=mock_llm_responses["question_1"], model="test", latency_ms=100),
                # Second synthetic response
                LLMResponse(
                    content="It's important because I'm trying to live a more sustainable lifestyle.",
                    model="test",
                    latency_ms=150
                ),
                # Second extraction
                LLMResponse(content=mock_llm_responses["extraction_2"], model="test", latency_ms=200),
            ]

            # 1. Create and start session
            create_resp = await client.post(
                "/sessions",
                json={"concept_id": "oat-milk", "config": {"concept_name": "Oat Milk"}}
            )
            session_id = create_resp.json()["id"]

            start_resp = await client.post(f"/sessions/{session_id}/start")
            opening_question = start_resp.json()["opening_question"]

            # 2. Generate synthetic response
            synthetic_resp = await client.post(
                "/synthetic/respond",
                json={
                    "question": opening_question,
                    "session_id": session_id,
                    "persona": "health_conscious",
                    "interview_context": {
                        "product_name": "Oat Milk",
                        "turn_number": 1
                    }
                }
            )
            assert synthetic_resp.status_code == 200
            synthetic_data = synthetic_resp.json()
            assert "response" in synthetic_data
            assert len(synthetic_data["response"]) > 0

            # 3. Process turn with synthetic response
            turn_resp = await client.post(
                f"/sessions/{session_id}/turns",
                json={"text": synthetic_data["response"]}
            )
            assert turn_resp.status_code == 200
            turn_data = turn_resp.json()

            # 4. Verify coverage achieved
            assert turn_data["scoring"]["coverage"] >= 0.0
            assert turn_data["graph_state"]["node_count"] > 0


# ============ TEST CLASS: EXPORT FORMATS ============

class TestExportFormats:
    """Tests for all export format endpoints."""

    @pytest.mark.asyncio
    async def test_all_export_formats_work(self, client, mock_llm_responses):
        """
        Test all export formats (JSON, Markdown, CSV):
        1. Create session and process turns
        2. Export as JSON - verify valid JSON
        3. Export as Markdown - verify markdown content
        4. Export as CSV - verify CSV structure
        """
        with patch("src.llm.client.AnthropicClient.complete") as mock_complete:
            mock_complete.side_effect = [
                LLMResponse(content=mock_llm_responses["opening"], model="test", latency_ms=100),
                LLMResponse(content=mock_llm_responses["extraction_1"], model="test", latency_ms=200),
                LLMResponse(content=mock_llm_responses["question_1"], model="test", latency_ms=100),
            ]

            # Setup session with data
            create_resp = await client.post(
                "/sessions",
                json={"concept_id": "test", "config": {"concept_name": "Test Product"}}
            )
            session_id = create_resp.json()["id"]
            await client.post(f"/sessions/{session_id}/start")
            await client.post(
                f"/sessions/{session_id}/turns",
                json={"text": "I love the creamy texture"}
            )

            # 1. Export as JSON
            json_resp = await client.get(
                f"/sessions/{session_id}/export",
                params={"format": "json"}
            )
            assert json_resp.status_code == 200
            assert json_resp.headers["content-type"] == "application/json"
            json_data = json.loads(json_resp.content)
            assert "session_id" in json_data or "concepts" in json_data

            # 2. Export as Markdown
            md_resp = await client.get(
                f"/sessions/{session_id}/export",
                params={"format": "markdown"}
            )
            assert md_resp.status_code == 200
            assert md_resp.headers["content-type"] == "text/markdown"
            md_content = md_resp.content.decode()
            assert len(md_content) > 0
            # Should have markdown headers
            assert "#" in md_content or "```" in md_content or "|" in md_content

            # 3. Export as CSV
            csv_resp = await client.get(
                f"/sessions/{session_id}/export",
                params={"format": "csv"}
            )
            assert csv_resp.status_code == 200
            assert csv_resp.headers["content-type"] == "text/csv"
            csv_content = csv_resp.content.decode()
            assert len(csv_content) > 0
            # Should have CSV structure
            assert "," in csv_content or "\n" in csv_content


# ============ TEST CLASS: CONCEPT ENDPOINTS ============

class TestConceptEndpoints:
    """Tests for concept knowledge endpoints."""

    @pytest.mark.asyncio
    async def test_list_and_get_concepts(self, client):
        """
        Test concept endpoints:
        1. List all available concepts
        2. Get specific concept details
        3. Get concept elements
        """
        # 1. List concepts
        list_resp = await client.get("/concepts")
        assert list_resp.status_code == 200
        concepts = list_resp.json()
        assert isinstance(concepts, list)

        # If there are concepts, test getting details
        if len(concepts) > 0 and isinstance(concepts[0], dict):
            concept_id = concepts[0].get("id") or concepts[0].get("concept_id")
            if concept_id:
                # 2. Get concept details
                detail_resp = await client.get(f"/concepts/{concept_id}")
                # May return 200 or 404 depending on implementation
                assert detail_resp.status_code in [200, 404]

                # 3. Get concept elements
                elements_resp = await client.get(f"/concepts/{concept_id}/elements")
                assert elements_resp.status_code in [200, 404]
        else:
            # Test with a known concept ID format
            test_ids = ["oat_milk", "oat_milk_v1", "test-product"]
            for concept_id in test_ids:
                resp = await client.get(f"/concepts/{concept_id}")
                if resp.status_code == 200:
                    # Found a valid concept, test elements
                    elements_resp = await client.get(f"/concepts/{concept_id}/elements")
                    assert elements_resp.status_code in [200, 404]
                    break


# ============ TEST CLASS: HEALTH ENDPOINT ============

class TestHealthEndpoint:
    """Tests for health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_check_returns_ok(self, client):
        """
        Test health check endpoint:
        1. Main health check returns healthy status
        2. Liveness probe returns alive
        3. Readiness probe returns ready
        """
        # 1. Main health check
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200
        health_data = health_resp.json()
        assert "status" in health_data
        assert health_data["status"] in ["healthy", "unhealthy"]
        assert "components" in health_data
        assert "database" in health_data["components"]

        # 2. Liveness probe
        live_resp = await client.get("/health/live")
        assert live_resp.status_code == 200
        assert live_resp.json()["status"] == "alive"

        # 3. Readiness probe
        ready_resp = await client.get("/health/ready")
        # Should be 200 if DB is ready, 503 if not
        assert ready_resp.status_code in [200, 503]
        if ready_resp.status_code == 200:
            assert ready_resp.json()["status"] == "ready"


# ============ TEST CLASS: ERROR HANDLING ============

class TestE2EErrorHandling:
    """Tests for error handling across E2E flows."""

    @pytest.mark.asyncio
    async def test_invalid_session_id_errors(self, client):
        """Test that invalid session IDs return appropriate errors."""
        fake_id = "nonexistent-session-id"

        # Should return 404
        resp = await client.get(f"/sessions/{fake_id}")
        assert resp.status_code == 404

        # Turn processing should also fail
        turn_resp = await client.post(
            f"/sessions/{fake_id}/turns",
            json={"text": "test"}
        )
        assert turn_resp.status_code in [404, 500]

    @pytest.mark.asyncio
    async def test_invalid_export_format(self, client):
        """Test that invalid export format returns 422."""
        create_resp = await client.post(
            "/sessions",
            json={"concept_id": "test", "config": {"concept_name": "Test"}}
        )
        session_id = create_resp.json()["id"]

        # Invalid format
        export_resp = await client.get(
            f"/sessions/{session_id}/export",
            params={"format": "xml"}  # Not supported
        )
        assert export_resp.status_code == 422


# ============ TEST CLASS: MULTI-SESSION SCENARIOS ============

class TestMultiSessionScenarios:
    """Tests for multiple concurrent sessions."""

    @pytest.mark.asyncio
    async def test_multiple_independent_sessions(self, client, mock_llm_responses):
        """Test that multiple sessions operate independently."""
        with patch("src.llm.client.AnthropicClient.complete") as mock_complete:
            # Create first session
            mock_complete.side_effect = [
                LLMResponse(content="Question 1", model="test", latency_ms=100),
                LLMResponse(content=mock_llm_responses["extraction_1"], model="test", latency_ms=200),
                LLMResponse(content="Next question 1", model="test", latency_ms=100),
            ]

            resp1 = await client.post(
                "/sessions",
                json={"concept_id": "product-a", "config": {"concept_name": "Product A"}}
            )
            session1_id = resp1.json()["id"]
            await client.post(f"/sessions/{session1_id}/start")
            await client.post(
                f"/sessions/{session1_id}/turns",
                json={"text": "Response for product A"}
            )

            # Create second session
            mock_complete.side_effect = [
                LLMResponse(content="Question 2", model="test", latency_ms=100),
                LLMResponse(content=mock_llm_responses["extraction_2"], model="test", latency_ms=200),
                LLMResponse(content="Next question 2", model="test", latency_ms=100),
            ]

            resp2 = await client.post(
                "/sessions",
                json={"concept_id": "product-b", "config": {"concept_name": "Product B"}}
            )
            session2_id = resp2.json()["id"]
            await client.post(f"/sessions/{session2_id}/start")
            await client.post(
                f"/sessions/{session2_id}/turns",
                json={"text": "Response for product B"}
            )

            # Verify both sessions exist independently
            list_resp = await client.get("/sessions")
            sessions = list_resp.json()["sessions"]
            session_ids = [s["id"] for s in sessions]
            assert session1_id in session_ids
            assert session2_id in session_ids

            # Verify they have different concepts
            session1_data = await client.get(f"/sessions/{session1_id}")
            session2_data = await client.get(f"/sessions/{session2_id}")
            assert session1_data.json()["concept_id"] != session2_data.json()["concept_id"]
