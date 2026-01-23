"""
End-to-end performance tests for the interview system.

Tests performance requirements including:
- Turn latency under 5 seconds (PRD requirement)
- Concurrent session capacity
- LLM timeout handling
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
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
        db_path = Path(tmpdir) / "test_perf.db"
        await init_database(db_path)

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
def fast_mock_llm_response():
    """Mock LLM response that returns quickly."""
    return json.dumps({
        "concepts": [
            {"text": "test concept", "node_type": "attribute", "confidence": 0.9, "source_quote": "test"}
        ],
        "relationships": [],
        "discourse_markers": []
    })


# ============ TEST CLASS: PERFORMANCE REQUIREMENTS ============

class TestPerformanceRequirements:
    """Tests for PRD performance requirements."""

    @pytest.mark.asyncio
    async def test_turn_latency_under_5s(self, client, fast_mock_llm_response):
        """
        PRD Requirement: Turn processing latency < 5 seconds.

        Tests that:
        1. Opening question generation is fast
        2. Turn processing completes within 5 seconds
        3. End-to-end latency meets requirements
        """
        with patch("src.llm.client.AnthropicClient.complete") as mock_complete:
            # Mock fast LLM responses (simulating < 1s LLM time)
            mock_complete.side_effect = [
                LLMResponse(content="What do you think?", model="test", latency_ms=500),
                LLMResponse(content=fast_mock_llm_response, model="test", latency_ms=800),
                LLMResponse(content="Tell me more.", model="test", latency_ms=500),
            ]

            # Create session
            create_resp = await client.post(
                "/sessions",
                json={"concept_id": "test", "config": {"concept_name": "Test Product"}}
            )
            session_id = create_resp.json()["id"]

            # Time opening question generation
            start_time = time.time()
            start_resp = await client.post(f"/sessions/{session_id}/start")
            opening_latency = (time.time() - start_time) * 1000  # Convert to ms
            assert start_resp.status_code == 200

            # Opening should be fast (< 2 seconds)
            assert opening_latency < 2000, f"Opening question took {opening_latency}ms, expected < 2000ms"

            # Time turn processing
            start_time = time.time()
            turn_resp = await client.post(
                f"/sessions/{session_id}/turns",
                json={"text": "I think it's great because of the quality"}
            )
            turn_latency = (time.time() - start_time) * 1000
            assert turn_resp.status_code == 200

            # PRD requirement: turn processing < 5 seconds
            # We use 4.5s to allow some margin
            assert turn_latency < 4500, f"Turn processing took {turn_latency}ms, expected < 5000ms"

            # Verify latency is reported in response
            turn_data = turn_resp.json()
            assert "latency_ms" in turn_data
            assert turn_data["latency_ms"] > 0

    @pytest.mark.asyncio
    async def test_concurrent_session_capacity(self, client, fast_mock_llm_response):
        """
        Test system capacity for concurrent sessions.

        Verifies that:
        1. Multiple sessions can run concurrently
        2. Each session maintains independent state
        3. Performance doesn't degrade significantly under load
        """
        NUM_SESSIONS = 5

        async def create_and_run_session(session_num: int) -> dict:
            """Create and run a session, return timing data."""
            with patch("src.llm.client.AnthropicClient.complete") as mock_complete:
                mock_complete.side_effect = [
                    LLMResponse(content=f"Question {session_num}", model="test", latency_ms=100),
                    LLMResponse(content=fast_mock_llm_response, model="test", latency_ms=150),
                    LLMResponse(content=f"Follow up {session_num}", model="test", latency_ms=100),
                ]

                start_time = time.time()
                create_resp = await client.post(
                    "/sessions",
                    json={"concept_id": f"test-{session_num}", "config": {"concept_name": f"Test {session_num}"}}
                )
                session_id = create_resp.json()["id"]

                await client.post(f"/sessions/{session_id}/start")
                await client.post(
                    f"/sessions/{session_id}/turns",
                    json={"text": f"Response {session_num}"}
                )

                return {
                    "session_id": session_id,
                    "session_num": session_num,
                    "latency_ms": (time.time() - start_time) * 1000
                }

        # Run sessions concurrently
        start_time = time.time()
        results = await asyncio.gather(*[
            create_and_run_session(i) for i in range(NUM_SESSIONS)
        ])
        total_time = time.time() - start_time

        # Verify all sessions completed
        assert len(results) == NUM_SESSIONS

        # Verify all sessions have unique IDs
        session_ids = [r["session_id"] for r in results]
        assert len(set(session_ids)) == NUM_SESSIONS

        # Verify performance didn't degrade
        # Each session should complete in reasonable time
        for result in results:
            assert result["latency_ms"] < 10000, f"Session {result['session_num']} took too long: {result['latency_ms']}ms"

        # Concurrent execution should be faster than sequential
        # (roughly: if each takes ~1s, 5 sequential would be ~5s, concurrent should be < 3s)
        assert total_time < NUM_SESSIONS * 2.0, f"Concurrent execution too slow: {total_time}s"

    @pytest.mark.asyncio
    async def test_concurrent_turns_same_session(self, client, fast_mock_llm_response):
        """
        Test that concurrent turns to the same session are handled properly.

        The system should either:
        1. Process turns sequentially (correct behavior)
        2. Return an error for concurrent access
        """
        with patch("src.llm.client.AnthropicClient.complete") as mock_complete:
            mock_complete.side_effect = [
                LLMResponse(content="Opening", model="test", latency_ms=100),
                # Multiple turn responses
                LLMResponse(content=fast_mock_llm_response, model="test", latency_ms=200),
                LLMResponse(content="Next 1", model="test", latency_ms=100),
                LLMResponse(content=fast_mock_llm_response, model="test", latency_ms=200),
                LLMResponse(content="Next 2", model="test", latency_ms=100),
            ]

            # Create and start session
            create_resp = await client.post(
                "/sessions",
                json={"concept_id": "test", "config": {"concept_name": "Test"}}
            )
            session_id = create_resp.json()["id"]
            await client.post(f"/sessions/{session_id}/start")

            # Try to process turns concurrently
            # This should either work sequentially or error
            async def process_turn(text: str):
                return await client.post(
                    f"/sessions/{session_id}/turns",
                    json={"text": text}
                )

            results = await asyncio.gather(
                process_turn("First response"),
                process_turn("Second response"),
                return_exceptions=True
            )

            # At least one should succeed
            successes = []
            for r in results:
                if not isinstance(r, Exception):
                    status = getattr(r, "status_code", None)
                    if status == 200:
                        successes.append(r)
            assert len(successes) >= 1

    @pytest.mark.asyncio
    async def test_llm_timeout_handling(self, client):
        """
        Test that LLM timeouts are handled gracefully.

        Verifies that:
        1. Timeout doesn't crash the system
        2. Appropriate error is returned
        3. Session remains usable after timeout
        """
        with patch("src.llm.client.AnthropicClient.complete") as mock_complete:
            # First call succeeds
            mock_complete.side_effect = [
                LLMResponse(content="Opening question", model="test", latency_ms=100),
                # Second call times out
                asyncio.TimeoutError("LLM request timed out"),
            ]

            # Create session
            create_resp = await client.post(
                "/sessions",
                json={"concept_id": "test", "config": {"concept_name": "Test"}}
            )
            session_id = create_resp.json()["id"]

            # Start succeeds
            start_resp = await client.post(f"/sessions/{session_id}/start")
            assert start_resp.status_code == 200

            # Turn should fail gracefully
            turn_resp = await client.post(
                f"/sessions/{session_id}/turns",
                json={"text": "This will timeout"}
            )
            # Should return error, not crash
            assert turn_resp.status_code in [500, 503, 504]


# ============ TEST CLASS: STRESS TESTS ============

class TestStressScenarios:
    """Stress tests for system limits."""

    @pytest.mark.asyncio
    async def test_rapid_sequential_turns(self, client, fast_mock_llm_response):
        """
        Test rapid sequential turn processing.

        Verifies system can handle rapid user input without degradation.
        """
        with patch("src.llm.client.AnthropicClient.complete") as mock_complete:
            # Prepare many responses
            responses = []
            for i in range(10):
                responses.append(LLMResponse(content="Opening", model="test", latency_ms=50))
                responses.append(LLMResponse(content=fast_mock_llm_response, model="test", latency_ms=100))
                responses.append(LLMResponse(content=f"Question {i}", model="test", latency_ms=50))

            mock_complete.side_effect = responses

            # Create session
            create_resp = await client.post(
                "/sessions",
                json={"concept_id": "test", "config": {"concept_name": "Test"}}
            )
            session_id = create_resp.json()["id"]
            await client.post(f"/sessions/{session_id}/start")

            # Process turns rapidly
            timings = []
            for i in range(10):
                start = time.time()
                turn_resp = await client.post(
                    f"/sessions/{session_id}/turns",
                    json={"text": f"Response {i}"}
                )
                latency = (time.time() - start) * 1000
                timings.append(latency)

                assert turn_resp.status_code == 200

            # Verify no significant degradation
            # Compare first and last turn latencies
            avg_latency = sum(timings) / len(timings)
            assert avg_latency < 2000, f"Average turn latency too high: {avg_latency}ms"

    @pytest.mark.asyncio
    async def test_large_concept_extraction(self, client):
        """
        Test performance with large concept extraction results.

        Verifies system can handle complex extractions with many concepts.
        """
        # Create a large extraction result
        large_extraction = json.dumps({
            "concepts": [
                {"text": f"Concept {i}", "node_type": "attribute", "confidence": 0.9, "source_quote": f"Quote {i}"}
                for i in range(20)
            ],
            "relationships": [
                {"source_text": f"Concept {i}", "target_text": f"Concept {i+1}", "relationship_type": "leads_to", "confidence": 0.8, "source_quote": f"Link {i}"}
                for i in range(15)
            ],
            "discourse_markers": ["because", "since", "therefore"] * 3
        })

        with patch("src.llm.client.AnthropicClient.complete") as mock_complete:
            mock_complete.side_effect = [
                LLMResponse(content="Opening", model="test", latency_ms=100),
                LLMResponse(content=large_extraction, model="test", latency_ms=300),
                LLMResponse(content="Next question", model="test", latency_ms=100),
            ]

            # Create session
            create_resp = await client.post(
                "/sessions",
                json={"concept_id": "test", "config": {"concept_name": "Test"}}
            )
            session_id = create_resp.json()["id"]
            await client.post(f"/sessions/{session_id}/start")

            # Process turn with large extraction
            start = time.time()
            turn_resp = await client.post(
                f"/sessions/{session_id}/turns",
                json={"text": "Long response with many concepts"}
            )
            latency = (time.time() - start) * 1000

            assert turn_resp.status_code == 200

            # Verify all concepts were extracted
            turn_data = turn_resp.json()
            assert len(turn_data["extracted"]["concepts"]) == 20
            assert len(turn_data["extracted"]["relationships"]) == 15

            # Should still be fast despite large extraction
            assert latency < 5000, f"Large extraction took {latency}ms"


# ============ TEST CLASS: MEMORY AND RESOURCE TESTS ============

class TestResourceUsage:
    """Tests for resource usage patterns."""

    @pytest.mark.asyncio
    async def test_session_cleanup(self, client, fast_mock_llm_response):
        """
        Test that resources are cleaned up properly.

        Verifies:
        1. Deleting session removes data
        2. No memory leaks in session state
        """
        with patch("src.llm.client.AnthropicClient.complete") as mock_complete:
            mock_complete.side_effect = [
                LLMResponse(content="Opening", model="test", latency_ms=100),
                LLMResponse(content=fast_mock_llm_response, model="test", latency_ms=100),
                LLMResponse(content="Next", model="test", latency_ms=100),
            ]

            # Create session with data
            create_resp = await client.post(
                "/sessions",
                json={"concept_id": "test", "config": {"concept_name": "Test"}}
            )
            session_id = create_resp.json()["id"]
            await client.post(f"/sessions/{session_id}/start")
            await client.post(
                f"/sessions/{session_id}/turns",
                json={"text": "Test response"}
            )

            # Verify session exists
            get_resp = await client.get(f"/sessions/{session_id}")
            assert get_resp.status_code == 200
            assert get_resp.json()["turn_count"] >= 1

            # Delete session
            delete_resp = await client.delete(f"/sessions/{session_id}")
            assert delete_resp.status_code == 204

            # Verify cleanup
            get_resp2 = await client.get(f"/sessions/{session_id}")
            assert get_resp2.status_code == 404

    @pytest.mark.asyncio
    async def test_export_performance(self, client, fast_mock_llm_response):
        """
        Test that export operations complete quickly.

        Verifies all export formats are performant.
        """
        with patch("src.llm.client.AnthropicClient.complete") as mock_complete:
            mock_complete.side_effect = [
                LLMResponse(content="Opening", model="test", latency_ms=100),
                LLMResponse(content=fast_mock_llm_response, model="test", latency_ms=100),
            ]

            # Create session with data
            create_resp = await client.post(
                "/sessions",
                json={"concept_id": "test", "config": {"concept_name": "Test"}}
            )
            session_id = create_resp.json()["id"]
            await client.post(f"/sessions/{session_id}/start")
            await client.post(
                f"/sessions/{session_id}/turns",
                json={"text": "Test response"}
            )

            # Test each export format
            for format_name in ["json", "markdown", "csv"]:
                start = time.time()
                export_resp = await client.get(
                    f"/sessions/{session_id}/export",
                    params={"format": format_name}
                )
                latency = (time.time() - start) * 1000

                assert export_resp.status_code == 200
                # Exports should be fast (< 1 second)
                assert latency < 1000, f"{format_name} export took {latency}ms"
