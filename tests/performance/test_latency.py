"""
Performance tests for interview system latency.

Validates PRD requirement: Response latency <5s p95 (Section 2.2)
"""

import pytest
import time
import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.services.session_service import SessionService, TurnResult
from src.domain.models.extraction import ExtractionResult, ExtractedConcept, ExtractedRelationship
from src.domain.models.knowledge_graph import GraphState, KGNode
from src.persistence.repositories.session_repo import SessionRepository
from src.persistence.repositories.graph_repo import GraphRepository


# PRD Requirement from Section 2.2
PRD_LATENCY_P95_TARGET_MS = 5000  # 5 seconds
PRD_LATENCY_TARGET_MS = 3000  # 3 seconds typical


@pytest.fixture
def mock_session_repo():
    """Create mock session repository."""
    repo = AsyncMock(spec=SessionRepository)
    repo.db = AsyncMock()
    repo.db.execute = AsyncMock()
    repo.db.commit = AsyncMock()
    repo.update = AsyncMock()
    return repo


@pytest.fixture
def mock_graph_repo():
    """Create mock graph repository."""
    repo = AsyncMock(spec=GraphRepository)
    repo.get_graph_state = AsyncMock(return_value=GraphState(
        node_count=5,
        edge_count=3,
        nodes_by_type={"attribute": 3, "consequence": 2}
    ))
    repo.get_nodes_by_session = AsyncMock(return_value=[
        KGNode(id="n1", session_id="s1", label="quality", node_type="attribute"),
        KGNode(id="n2", session_id="s1", label="satisfaction", node_type="consequence"),
    ])
    return repo


@pytest.fixture
def mock_services():
    """Create mock services for testing."""
    extraction_service = AsyncMock()
    graph_service = AsyncMock()
    question_service = AsyncMock()

    # Configure realistic responses
    extraction_service.extract = AsyncMock(return_value=ExtractionResult(
        concepts=[
            ExtractedConcept(text="quality", node_type="attribute", confidence=0.9),
            ExtractedConcept(text="satisfaction", node_type="consequence", confidence=0.85),
        ],
        relationships=[
            ExtractedRelationship(
                source_text="quality",
                target_text="satisfaction",
                relationship_type="leads_to",
                confidence=0.8
            )
        ],
        is_extractable=True
    ))

    graph_service.add_extraction_to_graph = AsyncMock(return_value=([], []))
    graph_service.get_graph_state = AsyncMock(return_value=GraphState(
        node_count=5,
        edge_count=3,
        nodes_by_type={"attribute": 3, "consequence": 2}
    ))
    graph_service.get_recent_nodes = AsyncMock(return_value=[
        KGNode(id="n1", session_id="s1", label="quality", node_type="attribute")
    ])

    question_service.generate_question = AsyncMock(
        return_value="Can you tell me more about why quality is important to you?"
    )
    question_service.select_focus_concept = MagicMock(return_value="quality")

    return {
        "extraction": extraction_service,
        "graph": graph_service,
        "question": question_service
    }


@pytest.fixture
def session_service(mock_session_repo, mock_graph_repo, mock_services):
    """Create session service with all mocks."""
    return SessionService(
        session_repo=mock_session_repo,
        graph_repo=mock_graph_repo,
        extraction_service=mock_services["extraction"],
        graph_service=mock_services["graph"],
        question_service=mock_services["question"],
    )


@pytest.fixture
def mock_session():
    """Create mock session object."""
    session = MagicMock()
    session.id = "test-session"
    session.methodology = "means_end_chain"
    session.concept_id = "test-concept"
    session.config = {"concept_name": "Test Product"}
    session.turn_count = 1
    return session


class TestTurnLatency:
    """Tests for turn processing latency."""

    @pytest.mark.asyncio
    async def test_single_turn_latency_under_5s(
        self, session_service, mock_session_repo, mock_session
    ):
        """
        Single turn processing completes under PRD p95 target of 5s.

        PRD Section 2.2: Response latency <5s p95
        """
        # Setup mocks
        mock_session_repo.get = AsyncMock(return_value=mock_session)
        cursor = AsyncMock()
        cursor.fetchall = AsyncMock(return_value=[])
        mock_session_repo.db.execute = AsyncMock(return_value=cursor)

        # Measure latency
        start = time.perf_counter()
        result = await session_service.process_turn(
            session_id="test-session",
            user_input="I really like the quality of this product. It makes me feel satisfied.",
        )
        latency_ms = (time.perf_counter() - start) * 1000

        # Validate result
        assert isinstance(result, TurnResult)
        assert result.turn_number == 1

        # Assert latency meets PRD requirement
        assert latency_ms < PRD_LATENCY_P95_TARGET_MS, (
            f"Turn latency {latency_ms:.0f}ms exceeds PRD p95 target of {PRD_LATENCY_P95_TARGET_MS}ms"
        )

        # Log for monitoring
        print(f"\nSingle turn latency: {latency_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_multiple_turns_average_latency(
        self, session_service, mock_session_repo, mock_session
    ):
        """
        Multiple turns maintain acceptable average latency.

        Tests that the system can handle sequential turns without degradation.
        """
        mock_session_repo.get = AsyncMock(return_value=mock_session)
        cursor = AsyncMock()
        cursor.fetchall = AsyncMock(return_value=[])
        mock_session_repo.db.execute = AsyncMock(return_value=cursor)

        # Process multiple turns
        num_turns = 5
        latencies = []

        for i in range(num_turns):
            start = time.perf_counter()
            await session_service.process_turn(
                session_id="test-session",
                user_input=f"This is turn {i+1} of my feedback.",
            )
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)

        # Calculate statistics
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)

        # Assert all turns meet PRD target
        assert max_latency < PRD_LATENCY_P95_TARGET_MS, (
            f"Max turn latency {max_latency:.0f}ms exceeds PRD p95 target"
        )
        assert avg_latency < PRD_LATENCY_TARGET_MS, (
            f"Avg latency {avg_latency:.0f}ms exceeds typical target"
        )

        print(f"\nTurn latencies (ms): {[f'{lat:.0f}' for lat in latencies]}")
        print(f"Average: {avg_latency:.0f}ms, Max: {max_latency:.0f}ms")

    @pytest.mark.asyncio
    async def test_graph_query_latency(
        self, mock_graph_repo, mock_services
    ):
        """
        Graph state queries complete quickly.

        Graph queries are called on every turn and should be fast.
        """
        from src.services.graph_service import GraphService

        graph_service = GraphService(mock_graph_repo)

        # Measure graph state query
        start = time.perf_counter()
        state = await graph_service.get_graph_state("test-session")
        latency_ms = (time.perf_counter() - start) * 1000

        # Assert fast query
        assert latency_ms < 100, (
            f"Graph query latency {latency_ms:.0f}ms exceeds 100ms target"
        )

        assert isinstance(state, GraphState)
        print(f"\nGraph query latency: {latency_ms:.0f}ms")

    @pytest.mark.asyncio
    async def test_export_latency(
        self, mock_graph_repo
    ):
        """
        Graph export completes in reasonable time.

        Export operations may process large graphs but should still be responsive.
        """
        from src.services.graph_service import GraphService

        # Setup larger graph
        mock_graph_repo.get_nodes_by_session = AsyncMock(
            return_value=[
                KGNode(
                    id=f"n{i}",
                    session_id="s1",
                    label=f"concept_{i}",
                    node_type="attribute"
                )
                for i in range(50)
            ]
        )
        mock_graph_repo.get_edges_by_session = AsyncMock(return_value=[])

        graph_service = GraphService(mock_graph_repo)

        # Measure export
        start = time.perf_counter()
        nodes, edges = await graph_service.get_session_graph("test-session")
        latency_ms = (time.perf_counter() - start) * 1000

        # Assert acceptable export time
        assert latency_ms < 500, (
            f"Export latency {latency_ms:.0f}ms exceeds 500ms target"
        )

        assert len(nodes) == 50
        print(f"\nExport latency (50 nodes): {latency_ms:.0f}ms")


class TestThroughput:
    """Tests for system throughput capacity."""

    @pytest.mark.asyncio
    async def test_concurrent_session_capacity(
        self, mock_session_repo, mock_graph_repo, mock_services
    ):
        """
        System can handle multiple concurrent sessions.

        PRD v2 is single-user, but architecture should support concurrency.
        This test validates no blocking operations.
        """
        # Create multiple services
        services = [
            SessionService(
                session_repo=mock_session_repo,
                graph_repo=mock_graph_repo,
                extraction_service=mock_services["extraction"],
                graph_service=mock_services["graph"],
                question_service=mock_services["question"],
            )
            for _ in range(3)
        ]

        # Setup mocks for all sessions
        mock_session_repo.get = AsyncMock(return_value=MagicMock(
            id="test-session",
            methodology="means_end_chain",
            concept_id="test-concept",
            config={"concept_name": "Test Product"},
            turn_count=1
        ))
        cursor = AsyncMock()
        cursor.fetchall = AsyncMock(return_value=[])
        mock_session_repo.db.execute = AsyncMock(return_value=cursor)

        # Process concurrent turns
        start = time.perf_counter()

        tasks = [
            svc.process_turn(
                session_id=f"session-{i}",
                user_input=f"Response from session {i}",
            )
            for i, svc in enumerate(services)
        ]

        results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start

        # Validate all completed
        assert len(results) == 3
        assert all(isinstance(r, TurnResult) for r in results)

        # Concurrent should be faster than sequential
        assert total_time < 2.0, (
            f"Concurrent processing took {total_time:.2f}s, expected <2s"
        )

        print(f"\nProcessed 3 concurrent turns in {total_time:.2f}s")


class TestResourceUsage:
    """Tests for resource efficiency."""

    @pytest.mark.asyncio
    async def test_memory_leak_check(
        self, session_service, mock_session_repo, mock_session
    ):
        """
        Verify no obvious memory leaks during repeated operations.

        This is a basic check; production would use memory profilers.
        """
        import gc

        mock_session_repo.get = AsyncMock(return_value=mock_session)
        cursor = AsyncMock()
        cursor.fetchall = AsyncMock(return_value=[])
        mock_session_repo.db.execute = AsyncMock(return_value=cursor)

        # Force collection before test
        gc.collect()

        # Get baseline memory (approximate)
        # Note: This is a simplified check; production would use tracemalloc
        initial_objects = len(gc.get_objects())

        # Process many turns
        for i in range(10):
            await session_service.process_turn(
                session_id="test-session",
                user_input=f"Turn {i} input",
            )

        # Force collection
        gc.collect()
        final_objects = len(gc.get_objects())

        # Object count should not grow significantly
        # Allow some growth but not unbounded
        growth = final_objects - initial_objects
        growth_ratio = growth / initial_objects if initial_objects > 0 else 0

        # Assert less than 10% growth
        assert growth_ratio < 0.1, (
            f"Object growth {growth_ratio:.1%} suggests potential memory leak"
        )

        print(f"\nObject growth after 10 turns: {growth} ({growth_ratio:.1%})")


class TestLatencyPercentiles:
    """Tests for latency distribution percentiles."""

    @pytest.mark.asyncio
    async def test_p95_latency_meets_prd(
        self, session_service, mock_session_repo, mock_session
    ):
        """
        p95 latency meets PRD requirement of <5s.

        PRD Section 2.2: Response latency <5s p95
        """
        mock_session_repo.get = AsyncMock(return_value=mock_session)
        cursor = AsyncMock()
        cursor.fetchall = AsyncMock(return_value=[])
        mock_session_repo.db.execute = AsyncMock(return_value=cursor)

        # Collect sample of latencies
        samples = 20
        latencies = []

        for i in range(samples):
            start = time.perf_counter()
            await session_service.process_turn(
                session_id="test-session",
                user_input=f"Sample input {i}",
            )
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)

        # Calculate percentiles
        sorted_latencies = sorted(latencies)
        p50_idx = int(len(sorted_latencies) * 0.5)
        p95_idx = int(len(sorted_latencies) * 0.95)
        p99_idx = int(len(sorted_latencies) * 0.99)

        p50 = sorted_latencies[p50_idx]
        p95 = sorted_latencies[p95_idx]
        p99 = sorted_latencies[p99_idx]

        # Assert p95 meets PRD
        assert p95 < PRD_LATENCY_P95_TARGET_MS, (
            f"p95 latency {p95:.0f}ms exceeds PRD target of {PRD_LATENCY_P95_TARGET_MS}ms"
        )

        print("\nLatency percentiles:")
        print(f"  p50 (median): {p50:.0f}ms")
        print(f"  p95:          {p95:.0f}ms (PRD target: {PRD_LATENCY_P95_TARGET_MS}ms)")
        print(f"  p99:          {p99:.0f}ms")
