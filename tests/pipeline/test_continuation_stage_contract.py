"""Tests for ContinuationStage contract integration (ADR-010).

RED Phase: Write failing tests first.
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timezone
from src.services.turn_pipeline.stages.continuation_stage import ContinuationStage
from src.services.turn_pipeline.context import PipelineContext
from src.domain.models.knowledge_graph import GraphState, DepthMetrics, CoverageState
from src.domain.models.pipeline_contracts import (
    ContextLoadingOutput,
    StateComputationOutput,
    GraphUpdateOutput,
    StrategySelectionOutput,
    ContinuationOutput,
)
from src.services.node_state_tracker import NodeStateTracker
from src.domain.models.node_state import NodeState


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
        from unittest.mock import Mock

        mock_service = AsyncMock()
        # select_focus_concept is synchronous in the actual implementation
        mock_service.select_focus_concept = Mock(
            side_effect=lambda **kwargs: "oat milk"
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

    @pytest.mark.asyncio
    async def test_uses_focus_from_strategy_selection(self, question_service):
        """Should use focus_node_id from strategy selection when available."""
        from src.domain.models.knowledge_graph import KGNode
        from datetime import datetime, timezone

        # Create context with a focus from strategy selection
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

        # Create recent nodes
        node1 = KGNode(
            id="node-1",
            session_id="test-session",
            label="creamy texture",
            node_type="attribute",
        )
        node2 = KGNode(
            id="node-2",
            session_id="test-session",
            label="satisfying",
            node_type="functional_consequence",
        )

        # Set ContextLoadingOutput (required for turn_number, max_turns, etc.)
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
            recent_nodes=[],  # Not used - recent_nodes from state_computation_output
        )

        # Set StateComputationOutput with recent_nodes (this is what context.recent_nodes reads from)
        from src.domain.models.pipeline_contracts import StateComputationOutput

        ctx.state_computation_output = StateComputationOutput(
            graph_state=graph_state,
            recent_nodes=[node1, node2],
            computed_at=datetime.now(timezone.utc),
        )

        # Set StrategySelectionOutput with focus_node_id
        ctx.strategy_selection_output = StrategySelectionOutput(
            strategy="deepen",
            focus={"focus_node_id": "node-2"},  # Should match node2
        )

        stage = ContinuationStage(question_service)
        result_context = await stage.process(ctx)

        # Should use the node label from the focus
        assert result_context.should_continue is True
        assert result_context.focus_concept == "satisfying"
        # select_focus_concept should NOT be called
        question_service.select_focus_concept.assert_not_called()


# =============================================================================
# Saturation-based continuation tests
# =============================================================================


def _make_question_service():
    """Create a mock question service for saturation tests."""
    svc = AsyncMock()
    svc.select_focus_concept = Mock(side_effect=lambda **kw: "oat milk")
    svc.generate_question = AsyncMock(return_value="Tell me more.")
    return svc


def _make_context(
    session_id: str = "test-session",
    turn_number: int = 6,
    max_turns: int = 20,
    node_count: int = 10,
    edge_count: int = 5,
    max_depth: int = 3,
    strategy: str = "deepen",
    nodes_added_this_turn: int = 0,
    edges_added_this_turn: int = 0,
    node_tracker: NodeStateTracker | None = None,
) -> PipelineContext:
    """Build a PipelineContext with all contracts needed for saturation checks."""
    ctx = PipelineContext(
        session_id=session_id,
        user_input="test input",
        node_tracker=node_tracker,
    )

    graph_state = GraphState(
        node_count=node_count,
        edge_count=edge_count,
        depth_metrics=DepthMetrics(max_depth=max_depth, avg_depth=float(max_depth)),
        coverage_state=CoverageState(),
        current_phase="exploratory",
        turn_count=turn_number,
    )

    ctx.context_loading_output = ContextLoadingOutput(
        methodology="means_end_chain",
        concept_id="test_concept",
        concept_name="Test Concept",
        turn_number=turn_number,
        mode="coverage",
        max_turns=max_turns,
        recent_utterances=[],
        strategy_history=[],
        graph_state=graph_state,
        recent_nodes=[],
    )

    ctx.state_computation_output = StateComputationOutput(
        graph_state=graph_state,
        recent_nodes=[],
        computed_at=datetime.now(timezone.utc),
    )

    ctx.graph_update_output = GraphUpdateOutput(
        nodes_added=[],
        edges_added=[],
        node_count=nodes_added_this_turn,
        edge_count=edges_added_this_turn,
    )

    ctx.strategy_selection_output = StrategySelectionOutput(
        strategy=strategy,
        focus=None,
    )

    return ctx


class TestSaturationContinuation:
    """Tests for saturation-based early termination (bead cgd)."""

    # ── Graph saturation: 5 consecutive zero-yield turns ─────────────

    @pytest.mark.asyncio
    async def test_stops_on_graph_saturation(self):
        """After 5 consecutive turns with 0 new nodes+edges, should stop."""
        svc = _make_question_service()
        stage = ContinuationStage(svc)

        # Simulate 5 consecutive zero-yield turns (all past minimum turn)
        for turn in range(6, 11):
            ctx = _make_context(
                turn_number=turn,
                nodes_added_this_turn=0,
                edges_added_this_turn=0,
            )
            result = await stage.process(ctx)

        # The 5th zero-yield turn (turn 10) should trigger stop
        assert result.should_continue is False
        assert "graph_saturated" in result.continuation_output.reason

    @pytest.mark.asyncio
    async def test_graph_saturation_resets_on_yield(self):
        """A productive turn resets the zero-yield counter."""
        svc = _make_question_service()
        stage = ContinuationStage(svc)

        # 4 zero-yield turns (use increasing max_depth to avoid depth_plateau)
        for i, turn in enumerate(range(6, 10)):
            ctx = _make_context(
                turn_number=turn,
                max_depth=3 + i,
                nodes_added_this_turn=0,
                edges_added_this_turn=0,
            )
            await stage.process(ctx)

        # Turn 10: productive (adds a node)
        ctx = _make_context(
            turn_number=10,
            max_depth=7,
            nodes_added_this_turn=1,
            edges_added_this_turn=0,
        )
        result = await stage.process(ctx)
        assert result.should_continue is True

        # Then 4 more zero-yield turns — still under threshold
        for i, turn in enumerate(range(11, 15)):
            ctx = _make_context(
                turn_number=turn,
                max_depth=8 + i,
                nodes_added_this_turn=0,
                edges_added_this_turn=0,
            )
            result = await stage.process(ctx)

        # Turn 14 is 4th zero-yield since reset — should still continue
        assert result.should_continue is True

    # ── Node exhaustion: all explored nodes exhausted ────────────────

    @pytest.mark.asyncio
    async def test_stops_on_all_nodes_exhausted(self):
        """When all explored nodes are exhausted, should stop."""
        svc = _make_question_service()
        stage = ContinuationStage(svc)

        tracker = NodeStateTracker()
        # Create two nodes that are both exhausted
        tracker.states["n1"] = NodeState(
            node_id="n1",
            label="texture",
            created_at_turn=1,
            depth=0,
            node_type="attribute",
            focus_count=3,
            turns_since_last_yield=5,
        )
        tracker.states["n2"] = NodeState(
            node_id="n2",
            label="taste",
            created_at_turn=1,
            depth=0,
            node_type="attribute",
            focus_count=2,
            turns_since_last_yield=4,
        )

        ctx = _make_context(
            turn_number=8,
            nodes_added_this_turn=0,
            edges_added_this_turn=0,
            node_tracker=tracker,
        )
        result = await stage.process(ctx)

        assert result.should_continue is False
        assert "all_nodes_exhausted" in result.continuation_output.reason

    # ── Quality degradation: 4 consecutive shallow turns ─────────────

    @pytest.mark.asyncio
    async def test_stops_on_quality_degradation(self):
        """After 4 consecutive shallow-only response turns, should stop."""
        svc = _make_question_service()
        stage = ContinuationStage(svc)

        tracker = NodeStateTracker()
        # Single node with all shallow responses
        tracker.states["n1"] = NodeState(
            node_id="n1",
            label="texture",
            created_at_turn=1,
            depth=0,
            node_type="attribute",
            focus_count=5,
            turns_since_last_yield=2,
            all_response_depths=["shallow", "shallow", "shallow", "shallow"],
        )

        # Simulate 4 turns — each turn the tracker shows only shallow responses
        for turn in range(6, 10):
            ctx = _make_context(
                turn_number=turn,
                nodes_added_this_turn=0,
                edges_added_this_turn=0,
                node_tracker=tracker,
            )
            result = await stage.process(ctx)

        assert result.should_continue is False
        assert "quality_degraded" in result.continuation_output.reason

    # ── Depth plateau: 6 turns at same max_depth ─────────────────────

    @pytest.mark.asyncio
    async def test_stops_on_depth_plateau(self):
        """After 6 consecutive turns at same max_depth, should stop."""
        svc = _make_question_service()
        stage = ContinuationStage(svc)

        # 7 turns all at max_depth=3. The 1st turn initializes prev_max_depth,
        # so plateau counting starts from the 2nd turn onward (6 plateaus).
        for turn in range(5, 12):
            ctx = _make_context(
                turn_number=turn,
                max_depth=3,
                nodes_added_this_turn=1,  # not zero-yield, so graph saturation won't fire
                edges_added_this_turn=0,
            )
            result = await stage.process(ctx)

        assert result.should_continue is False
        assert "depth_plateau" in result.continuation_output.reason

    # ── Minimum turn threshold ───────────────────────────────────────

    @pytest.mark.asyncio
    async def test_no_saturation_before_minimum_turn(self):
        """Saturation checks should not fire before minimum turn threshold."""
        svc = _make_question_service()
        stage = ContinuationStage(svc)

        # All exhaustion signals present but at early turns (1-4)
        tracker = NodeStateTracker()
        tracker.states["n1"] = NodeState(
            node_id="n1",
            label="texture",
            created_at_turn=1,
            depth=0,
            node_type="attribute",
            focus_count=3,
            turns_since_last_yield=5,
        )

        for turn in range(1, 5):
            ctx = _make_context(
                turn_number=turn,
                nodes_added_this_turn=0,
                edges_added_this_turn=0,
                node_tracker=tracker,
            )
            result = await stage.process(ctx)

        # Should still continue — too early for saturation
        assert result.should_continue is True

    # ── Session isolation ────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_tracking_isolated_per_session(self):
        """Different session_ids should have independent saturation tracking."""
        svc = _make_question_service()
        stage = ContinuationStage(svc)

        # Session A: 4 zero-yield turns
        for turn in range(6, 10):
            ctx_a = _make_context(
                session_id="session-A",
                turn_number=turn,
                nodes_added_this_turn=0,
                edges_added_this_turn=0,
            )
            await stage.process(ctx_a)

        # Session B: 1 zero-yield turn — should NOT inherit session A's count
        ctx_b = _make_context(
            session_id="session-B",
            turn_number=6,
            nodes_added_this_turn=0,
            edges_added_this_turn=0,
        )
        result_b = await stage.process(ctx_b)

        assert result_b.should_continue is True

        # Session A continues: 5th zero-yield should trigger
        ctx_a5 = _make_context(
            session_id="session-A",
            turn_number=10,
            nodes_added_this_turn=0,
            edges_added_this_turn=0,
        )
        result_a = await stage.process(ctx_a5)
        assert result_a.should_continue is False
