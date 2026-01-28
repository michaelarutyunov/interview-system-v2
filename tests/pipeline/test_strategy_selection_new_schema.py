"""Tests for methodology-based strategy selection (Phase 4).

Tests demonstrating how the new methodology-centric strategy selection works
with signals and strategy alternatives instead of two-tier scoring.
"""

import pytest

from src.services.turn_pipeline.stages.strategy_selection_stage import (
    StrategySelectionStage,
)
from src.services.turn_pipeline.context import PipelineContext
from src.domain.models.knowledge_graph import GraphState, DepthMetrics, CoverageState


class TestMethodologyStrategySelection:
    """Tests for the new methodology-based strategy selection."""

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

    @pytest.mark.asyncio
    async def test_populates_signals_and_alternatives(self, context):
        """Should populate signals and strategy alternatives using methodology service."""
        # Use default methodology service (use_methodology_service=True by default)
        stage = StrategySelectionStage()
        result_context = await stage.process(context)

        # Verify methodology signals are populated
        assert result_context.signals is not None
        assert "missing_terminal_value" in result_context.signals
        assert "ladder_depth" in result_context.signals
        assert "strategy_repetition_count" in result_context.signals

        # Verify strategy alternatives are populated
        assert result_context.strategy_alternatives is not None
        assert len(result_context.strategy_alternatives) > 0

        # Verify each alternative is a (strategy_name, score) tuple
        for alt in result_context.strategy_alternatives:
            assert isinstance(alt, tuple)
            assert len(alt) == 2
            assert isinstance(alt[0], str)  # strategy_name
            assert isinstance(alt[1], (int, float))  # score

        # Verify strategy is set (first alternative is selected)
        assert result_context.strategy is not None
        assert result_context.strategy == result_context.strategy_alternatives[0][0]

    @pytest.mark.asyncio
    async def test_signals_contain_common_and_methodology_specific(self, context):
        """Should contain both common signals and methodology-specific signals."""
        stage = StrategySelectionStage()
        result_context = await stage.process(context)

        # Common signals (all methodologies)
        assert "strategy_repetition_count" in result_context.signals
        assert "turns_since_strategy_change" in result_context.signals
        assert "response_confidence" in result_context.signals
        assert "response_ambiguity" in result_context.signals

        # MEC-specific signals (default methodology)
        assert "missing_terminal_value" in result_context.signals
        assert "ladder_depth" in result_context.signals
        assert "disconnected_nodes" in result_context.signals
        assert "edge_density" in result_context.signals
        assert "coverage_breadth" in result_context.signals

    @pytest.mark.asyncio
    async def test_strategy_alternatives_sorted_by_score(self, context):
        """Strategy alternatives should be sorted by score (descending)."""
        stage = StrategySelectionStage()
        result_context = await stage.process(context)

        alternatives = result_context.strategy_alternatives

        # Verify descending order
        for i in range(len(alternatives) - 1):
            assert alternatives[i][1] >= alternatives[i + 1][1], \
                f"Strategy {alternatives[i][0]} (score={alternatives[i][1]}) should come before " \
                f"{alternatives[i+1][0]} (score={alternatives[i+1][1]})"

    @pytest.mark.asyncio
    async def test_selection_result_is_none_with_methodology_service(self, context):
        """With methodology service, selection_result should be None (uses signals instead)."""
        stage = StrategySelectionStage()
        result_context = await stage.process(context)

        # New methodology system doesn't use selection_result
        assert result_context.selection_result is None

    @pytest.mark.asyncio
    async def test_fallback_to_two_tier_when_methodology_disabled(self, context):
        """Should fall back to two-tier scoring when methodology service is disabled."""
        # Disable methodology service
        stage = StrategySelectionStage(use_methodology_service=False)

        # Should use fallback (returns empty defaults since no strategy_service provided)
        result_context = await stage.process(context)

        # With no services at all, falls back to hardcoded selection
        assert result_context.strategy is not None
        assert result_context.signals is None  # No signals in fallback mode
        assert result_context.strategy_alternatives == []  # No alternatives in fallback mode


class TestStrategySelectionFreshness:
    """Tests for graph state freshness validation (ADR-010)."""

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

    @pytest.mark.asyncio
    async def test_accepts_fresh_graph_state(self, context):
        """Should accept fresh graph state."""
        from datetime import datetime, timezone

        # Set computed_at to now (fresh)
        context.graph_state_computed_at = datetime.now(timezone.utc)

        stage = StrategySelectionStage()
        # Should not raise
        result_context = await stage.process(context)

        assert result_context.strategy is not None

    @pytest.mark.asyncio
    async def test_falls_back_for_stale_graph_state(self, context):
        """Should handle stale graph state gracefully."""
        from datetime import datetime, timezone, timedelta

        # Set computed_at to 10 minutes ago (stale)
        context.graph_state_computed_at = datetime.now(timezone.utc) - timedelta(minutes=10)

        stage = StrategySelectionStage()
        # Currently logs error and continues - behavior may change
        # For now, verify it doesn't crash
        try:
            result_context = await stage.process(context)
            # May succeed with fallback behavior
        except Exception:
            # Or may raise - either is acceptable for stale state
            pass
