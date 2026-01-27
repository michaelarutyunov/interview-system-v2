"""Tests for StrategySelectionStage freshness validation (ADR-010).

RED Phase: Write failing tests first to prove they test the right thing.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

from src.domain.models.pipeline_contracts import StrategySelectionInput
from src.domain.models.knowledge_graph import GraphState, DepthMetrics, CoverageState
from src.services.turn_pipeline.context import PipelineContext


class TestStrategySelectionStageFreshnessValidation:
    """Tests for StrategySelectionStage freshness validation (ADR-010)."""

    @pytest.fixture
    def context_with_extraction(self):
        """Create a test pipeline context with extraction."""

        # Mock extraction with timestamp
        class MockExtraction:
            timestamp = datetime.now(timezone.utc)

        return PipelineContext(
            session_id="test-session",
            user_input="I like oat milk",
            methodology="means_end_chain",
            concept_id="oat_milk_v2",
            concept_name="Oat Milk v2",
            turn_number=1,
            mode="coverage",
            max_turns=10,
            extraction=MockExtraction(),  # type: ignore
        )

    @pytest.fixture
    def fresh_graph_state(self):
        """Create a fresh graph state."""
        return GraphState(
            node_count=5,
            edge_count=3,
            depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.0),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=1,
        )

    @pytest.fixture
    def graph_service(self):
        """Create a mock graph service."""
        mock_service = AsyncMock()
        mock_service.get_graph_state = AsyncMock(return_value=None)
        mock_service.get_recent_nodes = AsyncMock(return_value=[])
        return mock_service

    @pytest.mark.asyncio
    async def test_accepts_fresh_graph_state(
        self, context_with_extraction, fresh_graph_state, graph_service
    ):
        """Should accept fresh graph state (computed after extraction)."""
        # Set computed_at to AFTER extraction timestamp
        extraction_time = context_with_extraction.extraction.timestamp
        computed_at = extraction_time + timedelta(milliseconds=100)

        context_with_extraction.graph_state = fresh_graph_state

        # Create StrategySelectionInput to validate freshness
        # This should NOT raise - state is fresh
        input_data = StrategySelectionInput(
            graph_state=fresh_graph_state,
            recent_nodes=[],
            extraction=context_with_extraction.extraction,  # type: ignore
            conversation_history=[],
            turn_number=1,
            mode="coverage",
            computed_at=computed_at,
        )

        assert input_data.graph_state.node_count == 5
        assert input_data.computed_at > extraction_time

    @pytest.mark.asyncio
    async def test_rejects_stale_graph_state(
        self, context_with_extraction, fresh_graph_state
    ):
        """Should REJECT stale graph state (computed before extraction).

        This is the ADR-010 fix for the stale coverage_state bug.
        """
        # Set computed_at to BEFORE extraction timestamp (stale!)
        extraction_time = context_with_extraction.extraction.timestamp
        computed_at = extraction_time - timedelta(seconds=5)  # 5 seconds BEFORE

        context_with_extraction.graph_state = fresh_graph_state

        # Create StrategySelectionInput - should raise ValidationError
        with pytest.raises(Exception) as exc_info:
            StrategySelectionInput(
                graph_state=fresh_graph_state,
                recent_nodes=[],
                extraction=context_with_extraction.extraction,  # type: ignore
                conversation_history=[],
                turn_number=1,
                mode="coverage",
                computed_at=computed_at,
            )

        # Verify error message mentions stale state
        assert "stale" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_allows_simultaneous_timestamps(
        self, context_with_extraction, fresh_graph_state
    ):
        """Should allow state and extraction at same time (not stale)."""
        now = datetime.now(timezone.utc)

        # Mock extraction with timestamp
        class MockExtraction:
            timestamp = now

        context_with_extraction.extraction = MockExtraction()
        context_with_extraction.graph_state = fresh_graph_state

        # Same time is acceptable
        input_data = StrategySelectionInput(
            graph_state=fresh_graph_state,
            recent_nodes=[],
            extraction=context_with_extraction.extraction,  # type: ignore
            conversation_history=[],
            turn_number=1,
            mode="coverage",
            computed_at=now,  # Same time as extraction
        )

        assert input_data.computed_at == now
