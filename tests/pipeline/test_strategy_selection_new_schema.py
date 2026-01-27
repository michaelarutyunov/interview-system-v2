"""Tests for StrategySelectionResult new schema usage (ADR-010 Phase 2).

Tests demonstrating how to use the new type-safe schema in pipeline stages.
"""

import pytest
from unittest.mock import AsyncMock

from src.services.turn_pipeline.stages.strategy_selection_stage import (
    StrategySelectionStage,
)
from src.services.turn_pipeline.context import PipelineContext
from src.domain.models.knowledge_graph import GraphState, DepthMetrics, CoverageState
from src.domain.models.pipeline_contracts import StrategySelectionResult


class TestStrategySelectionNewSchema:
    """Tests for using the new StrategySelectionResult schema."""

    @pytest.fixture
    def context(self):
        """Create a test pipeline context."""
        return PipelineContext(
            session_id="test-session",
            user_input="I like oat milk",
            turn_number=1,
            mode="coverage_driven",
            graph_state=GraphState(
                node_count=5,
                edge_count=3,
                depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.0),
                coverage_state=CoverageState(),
                current_phase="exploratory",
                turn_count=1,
            ),
        )

    @pytest.fixture
    def strategy_service(self):
        """Create a mock strategy service."""
        mock_service = AsyncMock()

        # Create a mock SelectionResult with proper fields
        from src.services.strategy_service import SelectionResult

        # Create mock scoring result
        from src.services.scoring.two_tier.engine import ScoringResult

        mock_scoring_result = ScoringResult(
            strategy={"id": "deepen", "name": "Deepen"},
            focus={"focus_type": "element_coverage", "element_id": 42},
            final_score=0.65,
            tier1_outputs=[],
            tier2_outputs=[],
            vetoed_by=None,
            reasoning_trace=["Scored: 0.65"],
            scorer_sum=0.50,
            phase_multiplier=1.3,
        )

        mock_selection = SelectionResult(
            selected_strategy={"id": "deepen", "name": "Deepen"},
            selected_focus={"focus_type": "element_coverage", "element_id": 42},
            final_score=0.65,
            scoring_result=mock_scoring_result,
            alternative_strategies=[],
        )

        mock_service.select = AsyncMock(return_value=mock_selection)
        return mock_service

    @pytest.mark.asyncio
    async def test_populates_session_context_fields(self, context, strategy_service):
        """Should populate session context fields on SelectionResult."""
        stage = StrategySelectionStage(strategy_service)
        result_context = await stage.process(context)

        # Verify selection_result has session context populated
        assert result_context.selection_result is not None
        assert result_context.selection_result.session_id == "test-session"
        assert result_context.selection_result.turn_number == 1
        assert result_context.selection_result.phase == "exploratory"
        assert result_context.selection_result.phase_multiplier == 1.3

    @pytest.mark.asyncio
    async def test_can_convert_to_new_schema(self, context, strategy_service):
        """Should be able to convert to StrategySelectionResult Pydantic model."""
        stage = StrategySelectionStage(strategy_service)
        result_context = await stage.process(context)

        # Convert to new schema
        new_schema = result_context.selection_result.to_strategy_selection_result(
            session_id="test-session",
            turn_number=1,
            phase="exploratory",
            phase_multiplier=1.3,
        )

        # Verify conversion succeeded
        assert isinstance(new_schema, StrategySelectionResult)
        assert new_schema.session_id == "test-session"
        assert new_schema.phase == "exploratory"
        assert new_schema.selected_strategy.strategy_id == "deepen"

        # Verify element_id is preserved (CRITICAL for cover_element)
        assert new_schema.selected_strategy.focus.element_id == 42

    @pytest.mark.asyncio
    async def test_new_schema_provides_aggregate_stats(self, context, strategy_service):
        """New schema should provide aggregate statistics."""
        stage = StrategySelectionStage(strategy_service)
        result_context = await stage.process(context)

        new_schema = result_context.selection_result.to_strategy_selection_result(
            session_id="test-session",
            turn_number=1,
            phase="exploratory",
            phase_multiplier=1.3,
        )

        # Verify aggregate stats are available
        assert new_schema.total_candidates >= 1  # At least the selected one
        assert new_schema.vetoed_count >= 0
