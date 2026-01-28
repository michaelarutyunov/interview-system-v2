"""Tests for ContinuationStage contract integration (ADR-010).

RED Phase: Write failing tests first.
"""

import pytest
from unittest.mock import AsyncMock
from src.services.turn_pipeline.stages.continuation_stage import ContinuationStage
from src.services.turn_pipeline.context import PipelineContext
from src.domain.models.knowledge_graph import GraphState, DepthMetrics, CoverageState
from src.domain.models.pipeline_contracts import (
    ContextLoadingOutput,
    StrategySelectionOutput,
    ContinuationOutput,
)


async def mock_select_focus_concept(**kwargs):
    """Mock async function that returns a focus concept string."""
    return "oat milk"


class TestContinuationStageContract:
    """Tests for ContinuationStage decision logic."""

    @pytest.fixture
    def context(self):
        """Create a test pipeline context with contracts."""
        ctx = PipelineContext(
            session_id="test-session",
            user_input="I like oat milk",
        )

        # Create graph_state
        graph_state = GraphState(
            node_count=5,
            edge_count=3,
            depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.0),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=1,
        )

        # Set ContextLoadingOutput
        ctx.context_loading_output = ContextLoadingOutput(
            methodology="means_end_chain",
            concept_id="oat_milk_v2",
            concept_name="Oat Milk v2",
            turn_number=1,
            mode="coverage",
            max_turns=10,
            recent_utterances=[],
            strategy_history=[],
            graph_state=graph_state,
            recent_nodes=[],
        )

        # Set StrategySelectionOutput
        ctx.strategy_selection_output = StrategySelectionOutput(
            strategy="deepen",
            focus=None,
        )

        return ctx

    @pytest.fixture
    def continuation_stage_initial_context(self):
        """Create a context with ContinuationOutput for tests that need it."""
        ctx = PipelineContext(
            session_id="test-session",
            user_input="I like oat milk",
        )

        # Create graph_state
        graph_state = GraphState(
            node_count=5,
            edge_count=3,
            depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.0),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=1,
        )

        # Set ContextLoadingOutput
        ctx.context_loading_output = ContextLoadingOutput(
            methodology="means_end_chain",
            concept_id="oat_milk_v2",
            concept_name="Oat Milk v2",
            turn_number=1,
            mode="coverage",
            max_turns=10,
            recent_utterances=[],
            strategy_history=[],
            graph_state=graph_state,
            recent_nodes=[],
        )

        # Set StrategySelectionOutput
        ctx.strategy_selection_output = StrategySelectionOutput(
            strategy="deepen",
            focus=None,
        )

        # Set ContinuationOutput
        ctx.continuation_output = ContinuationOutput(
            should_continue=True,
            focus_concept="oat milk",
            turns_remaining=9,
        )

        return ctx

    @pytest.fixture
    def question_service(self):
        """Create a mock question service."""
        mock_service = AsyncMock()
        mock_service.select_focus_concept = AsyncMock(
            side_effect=mock_select_focus_concept
        )
        mock_service.generate_question = AsyncMock(
            return_value="Tell me more about oat milk."
        )
        return mock_service

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
        # Update the contract to have turn_number = max_turns
        context.context_loading_output.turn_number = 10
        context.context_loading_output.max_turns = 10

        stage = ContinuationStage(question_service)
        result_context = await stage.process(context)

        assert result_context.should_continue is False

    @pytest.mark.asyncio
    async def test_stops_when_close_strategy_selected(self, context, question_service):
        """Should stop when 'close' strategy is selected."""
        context.strategy_selection_output.strategy = "close"

        stage = ContinuationStage(question_service)
        result_context = await stage.process(context)

        assert result_context.should_continue is False
