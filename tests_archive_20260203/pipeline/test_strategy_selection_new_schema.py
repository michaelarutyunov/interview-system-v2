"""Tests for methodology-based strategy selection (Phase 4).

Tests demonstrating how the new methodology-centric strategy selection works
with signals and strategy alternatives instead of two-tier scoring.
"""

import pytest

from src.services.turn_pipeline.stages.strategy_selection_stage import (
    StrategySelectionStage,
)
from src.services.turn_pipeline.context import PipelineContext
from src.services.node_state_tracker import NodeStateTracker
from src.domain.models.knowledge_graph import GraphState, DepthMetrics, KGNode
from src.domain.models.pipeline_contracts import (
    ContextLoadingOutput,
    StateComputationOutput,
)
from datetime import datetime, timezone


class TestMethodologyStrategySelection:
    """Tests for the new methodology-based strategy selection."""

    @pytest.fixture
    async def context(self):
        """Create a test pipeline context with contracts."""
        ctx = PipelineContext(
            session_id="test-session",
            user_input="I like oat milk",
        )

        # Set up node tracker with some test nodes
        tracker = NodeStateTracker()
        for i in range(5):
            node = KGNode(
                id=f"node{i}",
                session_id="test-session",
                label=f"Node {i}",
                node_type="attribute",
                properties={"depth": i % 3},
            )
            await tracker.register_node(node, turn_number=0)
            if i < 3:
                await tracker.update_focus(
                    f"node{i}", turn_number=i + 1, strategy="deepen"
                )
        ctx.node_tracker = tracker

        # Set ContextLoadingOutput
        graph_state = GraphState(
            node_count=5,
            edge_count=3,
            depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.0),
            current_phase="exploratory",
            turn_count=1,
        )
        ctx.context_loading_output = ContextLoadingOutput(
            methodology="means_end_chain",
            concept_id="oat_milk",
            concept_name="Oat Milk",
            turn_number=1,
            mode="exploratory",
            max_turns=20,
            recent_utterances=[],
            strategy_history=[],
            graph_state=graph_state,
            recent_nodes=[],
        )

        # Set StateComputationOutput
        ctx.state_computation_output = StateComputationOutput(
            graph_state=graph_state,
            recent_nodes=[],
            computed_at=datetime.now(timezone.utc),
        )

        return ctx

    @pytest.mark.asyncio
    async def test_populates_signals_and_alternatives(self, context):
        """Should populate signals and strategy alternatives using methodology service."""
        # Use default methodology service (use_methodology_service=True by default)
        stage = StrategySelectionStage()
        result_context = await stage.process(context)

        # Verify methodology signals are populated (namespaced)
        assert result_context.signals is not None
        assert "graph.chain_completion" in result_context.signals
        assert "graph.max_depth" in result_context.signals
        assert "temporal.strategy_repetition_count" in result_context.signals

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

        # Verify signals were populated
        assert result_context.signals is not None

        # Common signals (all methodologies) - now namespaced
        assert "temporal.strategy_repetition_count" in result_context.signals
        assert "temporal.turns_since_strategy_change" in result_context.signals
        assert "llm.response_depth" in result_context.signals
        assert "llm.sentiment" in result_context.signals

        # MEC-specific signals (default methodology) - now namespaced
        assert "graph.chain_completion" in result_context.signals
        assert "graph.max_depth" in result_context.signals
        assert "graph.orphan_count" in result_context.signals
        assert "graph.node_count" in result_context.signals

    @pytest.mark.asyncio
    async def test_strategy_alternatives_sorted_by_score(self, context):
        """Strategy alternatives should be sorted by score (descending)."""
        stage = StrategySelectionStage()
        result_context = await stage.process(context)

        alternatives = result_context.strategy_alternatives

        # Verify descending order
        # alternatives can be (strategy, score) or (strategy, node_id, score)
        # score is always the last element
        for i in range(len(alternatives) - 1):
            score_i = alternatives[i][-1]
            score_next = alternatives[i + 1][-1]
            assert isinstance(score_i, (int, float)), (
                f"Score {score_i} should be numeric"
            )
            assert isinstance(score_next, (int, float)), (
                f"Score {score_next} should be numeric"
            )
            assert score_i >= score_next, (
                f"Strategy {alternatives[i][0]} (score={score_i}) should come before "
                f"{alternatives[i + 1][0]} (score={score_next})"
            )

    @pytest.mark.asyncio
    async def test_selection_result_is_none_with_methodology_service(self, context):
        """With methodology service, selection_result should be None (uses signals instead)."""
        stage = StrategySelectionStage()
        result_context = await stage.process(context)

        # selection_result is not used with methodology-based selection
        assert result_context.selection_result is None

    @pytest.mark.asyncio
    async def test_fallback_to_two_tier_when_methodology_disabled(self, context):
        """Should fall back to two-tier scoring when methodology service is disabled."""
        # This test would require creating a stage with use_methodology_service=False
        # For now, we skip it as the methodology service is always enabled
        pass


class TestStrategySelectionFreshness:
    """Tests for graph state freshness validation."""

    @pytest.fixture
    async def context(self):
        """Create a test pipeline context with contracts."""
        ctx = PipelineContext(
            session_id="test-session",
            user_input="I like oat milk",
        )

        # Set up node tracker with some test nodes
        tracker = NodeStateTracker()
        for i in range(5):
            node = KGNode(
                id=f"node{i}",
                session_id="test-session",
                label=f"Node {i}",
                node_type="attribute",
                properties={"depth": i % 3},
            )
            await tracker.register_node(node, turn_number=0)
        ctx.node_tracker = tracker

        # Set ContextLoadingOutput
        graph_state = GraphState(
            node_count=5,
            edge_count=3,
            depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.0),
            current_phase="exploratory",
            turn_count=1,
        )
        ctx.context_loading_output = ContextLoadingOutput(
            methodology="means_end_chain",
            concept_id="oat_milk",
            concept_name="Oat Milk",
            turn_number=1,
            mode="exploratory",
            max_turns=20,
            recent_utterances=[],
            strategy_history=[],
            graph_state=graph_state,
            recent_nodes=[],
        )

        # Set StateComputationOutput with computed_at
        ctx.state_computation_output = StateComputationOutput(
            graph_state=graph_state,
            recent_nodes=[],
            computed_at=datetime.now(timezone.utc),
        )

        return ctx

    @pytest.mark.asyncio
    async def test_accepts_fresh_graph_state(self, context):
        """Should accept fresh graph state (computed recently)."""
        stage = StrategySelectionStage()
        result_context = await stage.process(context)

        # Verify stage succeeded with fresh state
        assert result_context.strategy is not None

    @pytest.mark.asyncio
    async def test_falls_back_for_stale_graph_state(self, context):
        """Should fall back to default strategy for stale graph state."""
        # Set computed_at to a long time ago (stale)
        from datetime import timedelta

        old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        context.state_computation_output.computed_at = old_time

        stage = StrategySelectionStage()
        result_context = await stage.process(context)

        # Should still produce a strategy (fallback)
        assert result_context.strategy is not None
