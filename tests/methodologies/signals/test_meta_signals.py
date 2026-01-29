"""Unit tests for meta signals.

Tests for meta signals that combine multiple signal sources:
- InterviewPhaseSignal: Detects interview phase (early/mid/late)
- NodeOpportunitySignal: Determines node opportunity (exhausted/probe_deeper/fresh)
"""

import pytest
from unittest.mock import Mock, AsyncMock

from src.methodologies.signals.meta.interview_phase import InterviewPhaseSignal
from src.methodologies.signals.meta.node_opportunity import NodeOpportunitySignal
from src.domain.models.node_state import NodeState


class TestInterviewPhaseSignal:
    """Test interview phase detection signal."""

    @pytest.mark.asyncio
    async def test_early_phase_small_graph(self):
        """Test early phase detection with small graph (< 5 nodes)."""
        signal = InterviewPhaseSignal()

        # Create mock graph state
        graph_state = Mock()
        graph_state.node_count = 3
        graph_state.max_depth = 2
        graph_state.orphan_count = 1
        graph_state.extended_properties = {"orphan_count": 1}

        context = Mock()
        response_text = "Test response"

        result = await signal.detect(context, graph_state, response_text)

        assert result["meta.interview.phase"] == "early"

    @pytest.mark.asyncio
    async def test_mid_phase_medium_graph(self):
        """Test mid phase detection with medium graph (5-14 nodes)."""
        signal = InterviewPhaseSignal()

        # Create mock graph state
        graph_state = Mock()
        graph_state.node_count = 10
        graph_state.max_depth = 3
        graph_state.orphan_count = 2
        graph_state.extended_properties = {"orphan_count": 2}

        context = Mock()
        response_text = "Test response"

        result = await signal.detect(context, graph_state, response_text)

        assert result["meta.interview.phase"] == "mid"

    @pytest.mark.asyncio
    async def test_mid_phase_many_orphans(self):
        """Test mid phase detection with many orphan nodes (> 3)."""
        signal = InterviewPhaseSignal()

        # Create mock graph state with many orphans
        graph_state = Mock()
        graph_state.node_count = 20
        graph_state.max_depth = 4
        graph_state.orphan_count = 5
        graph_state.extended_properties = {"orphan_count": 5}

        context = Mock()
        response_text = "Test response"

        result = await signal.detect(context, graph_state, response_text)

        # Should be mid due to high orphan count
        assert result["meta.interview.phase"] == "mid"

    @pytest.mark.asyncio
    async def test_late_phase_large_graph(self):
        """Test late phase detection with large graph (15+ nodes)."""
        signal = InterviewPhaseSignal()

        # Create mock graph state
        graph_state = Mock()
        graph_state.node_count = 20
        graph_state.max_depth = 5
        graph_state.orphan_count = 2
        graph_state.extended_properties = {"orphan_count": 2}

        context = Mock()
        response_text = "Test response"

        result = await signal.detect(context, graph_state, response_text)

        assert result["meta.interview.phase"] == "late"

    @pytest.mark.asyncio
    async def test_orphan_count_from_extended_properties(self):
        """Test orphan count is read from extended_properties."""
        signal = InterviewPhaseSignal()

        # Create mock graph state
        graph_state = Mock()
        graph_state.node_count = 8
        graph_state.max_depth = 3
        graph_state.extended_properties = {"orphan_count": 4}

        context = Mock()
        response_text = "Test response"

        result = await signal.detect(context, graph_state, response_text)

        # Should be mid due to orphan count > 3
        assert result["meta.interview.phase"] == "mid"

    @pytest.mark.asyncio
    async def test_orphan_count_fallback_to_attribute(self):
        """Test orphan count fallback to attribute when not in extended_properties."""
        signal = InterviewPhaseSignal()

        # Create mock graph state without extended_properties
        graph_state = Mock()
        graph_state.node_count = 10
        graph_state.max_depth = 3
        graph_state.orphan_count = 1
        graph_state.extended_properties = {}

        # Mock hasattr to return False for extended_properties check
        graph_state.extended_properties = {}

        context = Mock()
        response_text = "Test response"

        result = await signal.detect(context, graph_state, response_text)

        assert result["meta.interview.phase"] == "mid"


class TestNodeOpportunitySignal:
    """Test node opportunity meta signal."""

    @pytest.fixture
    def node_tracker(self):
        """Create a mock NodeStateTracker."""
        tracker = Mock()

        # Create mock node states
        node1 = NodeState(
            node_id="node1",
            label="Node 1",
            created_at_turn=1,
            depth=1,
            focus_count=3,
            last_focus_turn=3,
            turns_since_last_focus=2,
            current_focus_streak=2,
            yield_count=0,
            turns_since_last_yield=3,
            yield_rate=0.0,
            all_response_depths=["shallow", "shallow", "shallow"],
            connected_node_ids=set(),
            edge_count_outgoing=0,
            edge_count_incoming=0,
        )

        node2 = NodeState(
            node_id="node2",
            label="Node 2",
            created_at_turn=1,
            depth=2,
            focus_count=4,
            last_focus_turn=4,
            turns_since_last_focus=1,
            current_focus_streak=4,
            yield_count=0,
            turns_since_last_yield=4,
            yield_rate=0.0,
            all_response_depths=["deep", "deep", "deep"],
            connected_node_ids=set(),
            edge_count_outgoing=0,
            edge_count_incoming=0,
        )

        node3 = NodeState(
            node_id="node3",
            label="Node 3",
            created_at_turn=2,
            depth=1,
            focus_count=1,
            last_focus_turn=2,
            turns_since_last_focus=3,
            current_focus_streak=0,
            yield_count=1,
            turns_since_last_yield=1,
            yield_rate=1.0,
            all_response_depths=["moderate"],
            connected_node_ids=set(),
            edge_count_outgoing=1,
            edge_count_incoming=1,
        )

        tracker.get_all_states = Mock(
            return_value={"node1": node1, "node2": node2, "node3": node3}
        )
        tracker.get_state = Mock(
            side_effect=lambda nid: {
                "node1": node1,
                "node2": node2,
                "node3": node3,
            }.get(nid)
        )

        return tracker

    @pytest.mark.asyncio
    async def test_exhausted_node(self, node_tracker):
        """Test node marked as exhausted."""
        signal = NodeOpportunitySignal(node_tracker)

        # Mock dependency signals
        signal.exhausted_signal.detect = AsyncMock(
            return_value={"node1": "true", "node2": "false", "node3": "false"}
        )
        signal.streak_signal.detect = AsyncMock(
            return_value={"node1": "high", "node2": "high", "node3": "none"}
        )

        context = Mock()
        context.signals = {"llm.response_depth": "deep"}
        graph_state = Mock()
        response_text = "Test response"

        result = await signal.detect(context, graph_state, response_text)

        # node1 should be exhausted (is_exhausted=True)
        assert result["node1"] == "exhausted"

    @pytest.mark.asyncio
    async def test_probe_deeper_node(self, node_tracker):
        """Test node marked as probe_deeper (deep responses, high streak, not exhausted)."""
        signal = NodeOpportunitySignal(node_tracker)

        # Mock dependency signals
        signal.exhausted_signal.detect = AsyncMock(
            return_value={"node1": "false", "node2": "false", "node3": "false"}
        )
        signal.streak_signal.detect = AsyncMock(
            return_value={"node1": "high", "node2": "high", "node3": "none"}
        )

        context = Mock()
        context.signals = {"llm.response_depth": "deep"}
        graph_state = Mock()
        response_text = "Test response"

        result = await signal.detect(context, graph_state, response_text)

        # node2 should be probe_deeper (high streak + deep response + not exhausted)
        assert result["node2"] == "probe_deeper"

    @pytest.mark.asyncio
    async def test_fresh_node(self, node_tracker):
        """Test node marked as fresh (default)."""
        signal = NodeOpportunitySignal(node_tracker)

        # Mock dependency signals
        signal.exhausted_signal.detect = AsyncMock(
            return_value={"node1": "false", "node2": "false", "node3": "false"}
        )
        signal.streak_signal.detect = AsyncMock(
            return_value={"node1": "none", "node2": "low", "node3": "none"}
        )

        context = Mock()
        context.signals = {"llm.response_depth": "moderate"}
        graph_state = Mock()
        response_text = "Test response"

        result = await signal.detect(context, graph_state, response_text)

        # All nodes should be fresh (not exhausted, not high streak + deep)
        assert result["node1"] == "fresh"
        assert result["node2"] == "fresh"
        assert result["node3"] == "fresh"

    @pytest.mark.asyncio
    async def test_no_response_depth_in_context(self, node_tracker):
        """Test behavior when response depth not available in context."""
        signal = NodeOpportunitySignal(node_tracker)

        # Mock dependency signals
        signal.exhausted_signal.detect = AsyncMock(
            return_value={"node1": "false", "node2": "false", "node3": "false"}
        )
        signal.streak_signal.detect = AsyncMock(
            return_value={"node1": "high", "node2": "low", "node3": "none"}
        )

        context = Mock()
        context.signals = {}  # No response depth
        graph_state = Mock()
        response_text = "Test response"

        result = await signal.detect(context, graph_state, response_text)

        # Without deep response, should not be probe_deeper
        # node1 has high streak but no deep response -> fresh
        assert result["node1"] == "fresh"

    @pytest.mark.asyncio
    async def test_shallow_response_with_high_streak(self, node_tracker):
        """Test that shallow response with high streak doesn't trigger probe_deeper."""
        signal = NodeOpportunitySignal(node_tracker)

        # Mock dependency signals
        signal.exhausted_signal.detect = AsyncMock(
            return_value={"node1": "false", "node2": "false", "node3": "false"}
        )
        signal.streak_signal.detect = AsyncMock(
            return_value={"node1": "high", "node2": "medium", "node3": "none"}
        )

        context = Mock()
        context.signals = {"llm.response_depth": "shallow"}
        graph_state = Mock()
        response_text = "Test response"

        result = await signal.detect(context, graph_state, response_text)

        # node1 should be fresh (high streak but shallow response)
        assert result["node1"] == "fresh"
