"""Tests for ContinuationStage contract integration (ADR-010).

RED Phase: Write failing tests first.
"""

import pytest
from unittest.mock import AsyncMock
from src.services.turn_pipeline.stages.continuation_stage import ContinuationStage
from src.services.turn_pipeline.context import PipelineContext
from src.domain.models.knowledge_graph import GraphState, DepthMetrics, CoverageState


class TestContinuationStageContract:
    """Tests for ContinuationStage decision logic."""

    @pytest.fixture
    def context(self):
        """Create a test pipeline context."""
        graph_state = GraphState(
            node_count=5,
            edge_count=3,
            depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.0),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=1,
        )

        return PipelineContext(
            session_id="test-session",
            user_input="I like oat milk",
            methodology="means_end_chain",
            concept_id="oat_milk_v2",
            concept_name="Oat Milk v2",
            turn_number=1,
            mode="coverage",
            max_turns=10,
            graph_state=graph_state,
            strategy="deepen",
        )

    @pytest.fixture
    def question_service(self):
        """Create a mock question service."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_continues_when_below_max_turns(self, context, question_service):
        """Should continue when turn_number < max_turns."""
        stage = ContinuationStage(question_service)

        result_context = await stage.process(context)

        assert result_context.should_continue is True
        assert result_context.focus_concept != ""

    @pytest.mark.asyncio
    async def test_stops_when_at_max_turns(self, context, question_service):
        """Should stop when turn_number >= max_turns."""
        context.turn_number = 10
        context.max_turns = 10

        stage = ContinuationStage(question_service)
        result_context = await stage.process(context)

        assert result_context.should_continue is False

    @pytest.mark.asyncio
    async def test_stops_when_close_strategy_selected(self, context, question_service):
        """Should stop when 'close' strategy is selected."""
        context.strategy = "close"

        stage = ContinuationStage(question_service)
        result_context = await stage.process(context)

        assert result_context.should_continue is False
