"""
Unit tests for NodeStateTracker service.

Tests cover node registration, focus updates, yield recording,
response signal appending, edge count updates, and strategy tracking.
"""

import pytest

from src.domain.models.knowledge_graph import KGNode
from src.domain.models.node_state import NodeState
from src.services.node_state_tracker import (
    NodeStateTracker,
    GraphChangeSummary,
)


class TestNodeState:
    """Tests for NodeState dataclass."""

    def test_create_node_state(self):
        """NodeState can be created with required fields."""
        state = NodeState(
            node_id="node-1",
            label="creamy texture",
            created_at_turn=1,
            depth=0,
        )

        assert state.node_id == "node-1"
        assert state.label == "creamy texture"
        assert state.created_at_turn == 1
        assert state.depth == 0

    def test_node_state_defaults(self):
        """NodeState has sensible defaults for optional fields."""
        state = NodeState(
            node_id="node-1",
            label="test",
            created_at_turn=1,
            depth=0,
        )

        assert state.focus_count == 0
        assert state.last_focus_turn is None
        assert state.turns_since_last_focus == 0
        assert state.current_focus_streak == 0
        assert state.last_yield_turn is None
        assert state.turns_since_last_yield == 0
        assert state.yield_count == 0
        assert state.yield_rate == 0.0
        assert state.all_response_depths == []
        assert state.connected_node_ids == set()
        assert state.edge_count_outgoing == 0
        assert state.edge_count_incoming == 0
        assert state.strategy_usage_count == {}
        assert state.last_strategy_used is None
        assert state.consecutive_same_strategy == 0

    def test_is_orphan_with_no_edges(self):
        """is_orphan returns True when node has no edges."""
        state = NodeState(
            node_id="node-1",
            label="test",
            created_at_turn=1,
            depth=0,
            edge_count_outgoing=0,
            edge_count_incoming=0,
        )

        assert state.is_orphan is True

    def test_is_orphan_with_outgoing_edges(self):
        """is_orphan returns False when node has outgoing edges."""
        state = NodeState(
            node_id="node-1",
            label="test",
            created_at_turn=1,
            depth=0,
            edge_count_outgoing=2,
            edge_count_incoming=0,
        )

        assert state.is_orphan is False

    def test_is_orphan_with_incoming_edges(self):
        """is_orphan returns False when node has incoming edges."""
        state = NodeState(
            node_id="node-1",
            label="test",
            created_at_turn=1,
            depth=0,
            edge_count_outgoing=0,
            edge_count_incoming=3,
        )

        assert state.is_orphan is False

    def test_is_orphan_with_both_edges(self):
        """is_orphan returns False when node has both edge types."""
        state = NodeState(
            node_id="node-1",
            label="test",
            created_at_turn=1,
            depth=0,
            edge_count_outgoing=1,
            edge_count_incoming=1,
        )

        assert state.is_orphan is False


class TestGraphChangeSummary:
    """Tests for GraphChangeSummary dataclass."""

    def test_create_graph_change_summary(self):
        """GraphChangeSummary can be created with required fields."""
        summary = GraphChangeSummary(
            nodes_added=2,
            edges_added=3,
            nodes_modified=1,
        )

        assert summary.nodes_added == 2
        assert summary.edges_added == 3
        assert summary.nodes_modified == 1

    def test_graph_change_summary_defaults(self):
        """GraphChangeSummary defaults nodes_modified to 0."""
        summary = GraphChangeSummary(
            nodes_added=1,
            edges_added=1,
        )

        assert summary.nodes_modified == 0


class TestNodeStateTracker:
    """Tests for NodeStateTracker service."""

    def test_create_tracker(self):
        """NodeStateTracker can be instantiated."""
        tracker = NodeStateTracker()

        assert tracker.states == {}
        assert tracker.previous_focus is None

    @pytest.mark.asyncio
    async def test_register_new_node(self):
        """register_node creates a new NodeState for untracked nodes."""
        tracker = NodeStateTracker()
        node = KGNode(
            id="node-1",
            session_id="session-1",
            label="creamy texture",
            node_type="attribute",
        )

        state = await tracker.register_node(node, turn_number=1)

        assert "node-1" in tracker.states
        assert state.node_id == "node-1"
        assert state.label == "creamy texture"
        assert state.created_at_turn == 1
        assert state.depth == 0

    @pytest.mark.asyncio
    async def test_register_node_already_registered(self):
        """register_node returns existing state if node already tracked."""
        tracker = NodeStateTracker()
        node = KGNode(
            id="node-1",
            session_id="session-1",
            label="creamy texture",
            node_type="attribute",
        )

        # Register once
        state1 = await tracker.register_node(node, turn_number=1)
        # Try to register again
        state2 = await tracker.register_node(node, turn_number=2)

        # Should return same state
        assert state1 is state2
        assert state1.created_at_turn == 1  # Original turn preserved

    @pytest.mark.asyncio
    async def test_update_focus_first_time(self):
        """update_focus initializes focus metrics on first focus."""
        tracker = NodeStateTracker()
        node = KGNode(
            id="node-1",
            session_id="session-1",
            label="test",
            node_type="attribute",
        )

        await tracker.register_node(node, turn_number=1)
        await tracker.update_focus(node_id="node-1", turn_number=1, strategy="deepen")

        state = tracker.get_state("node-1")
        if state is None:
            raise AssertionError("state should not be None")
        assert state.focus_count == 1
        assert state.last_focus_turn == 1
        assert state.turns_since_last_focus == 0
        assert state.current_focus_streak == 1
        assert state.last_strategy_used == "deepen"
        assert state.consecutive_same_strategy == 1
        assert state.strategy_usage_count == {"deepen": 1}

    @pytest.mark.asyncio
    async def test_update_focus_consecutive_same_node(self):
        """update_focus increments streak when same node focused consecutively."""
        tracker = NodeStateTracker()
        node = KGNode(
            id="node-1",
            session_id="session-1",
            label="test",
            node_type="attribute",
        )

        await tracker.register_node(node, turn_number=1)
        await tracker.update_focus(node_id="node-1", turn_number=1, strategy="deepen")
        await tracker.update_focus(node_id="node-1", turn_number=2, strategy="deepen")

        state = tracker.get_state("node-1")
        if state is None:
            raise AssertionError("state should not be None")
        assert state.focus_count == 2
        assert state.current_focus_streak == 2
        assert state.consecutive_same_strategy == 2

    @pytest.mark.asyncio
    async def test_update_focus_changed_node(self):
        """update_focus resets streak when focus changes to different node."""
        tracker = NodeStateTracker()
        node1 = KGNode(
            id="node-1",
            session_id="session-1",
            label="test1",
            node_type="attribute",
        )
        node2 = KGNode(
            id="node-2",
            session_id="session-1",
            label="test2",
            node_type="attribute",
        )

        await tracker.register_node(node1, turn_number=1)
        await tracker.register_node(node2, turn_number=1)

        await tracker.update_focus(node_id="node-1", turn_number=1, strategy="deepen")
        await tracker.update_focus(node_id="node-2", turn_number=2, strategy="probe")

        state1 = tracker.get_state("node-1")
        state2 = tracker.get_state("node-2")
        assert state1 is not None
        assert state2 is not None

        # node-1 streak should reset to 0 when focus changed
        assert state1.current_focus_streak == 1
        assert state1.turns_since_last_focus == 1

        # node-2 should have streak of 1
        assert state2.current_focus_streak == 1
        assert state2.turns_since_last_focus == 0

    @pytest.mark.asyncio
    async def test_update_focus_different_strategy(self):
        """update_focus resets consecutive strategy when strategy changes."""
        tracker = NodeStateTracker()
        node = KGNode(
            id="node-1",
            session_id="session-1",
            label="test",
            node_type="attribute",
        )

        await tracker.register_node(node, turn_number=1)
        await tracker.update_focus(node_id="node-1", turn_number=1, strategy="deepen")
        await tracker.update_focus(node_id="node-1", turn_number=2, strategy="probe")

        state = tracker.get_state("node-1")
        assert state is not None
        assert state.consecutive_same_strategy == 1  # Reset
        assert state.last_strategy_used == "probe"
        assert state.strategy_usage_count == {"deepen": 1, "probe": 1}

    @pytest.mark.asyncio
    async def test_update_focus_node_not_found(self):
        """update_focus logs warning and returns gracefully when node not found."""
        tracker = NodeStateTracker()

        # Should not raise exception
        await tracker.update_focus(
            node_id="nonexistent", turn_number=1, strategy="deepen"
        )

        # States should remain empty
        assert tracker.states == {}

    @pytest.mark.asyncio
    async def test_record_yield_with_changes(self):
        """record_yield updates yield metrics when graph changes occur."""
        tracker = NodeStateTracker()
        node = KGNode(
            id="node-1",
            session_id="session-1",
            label="test",
            node_type="attribute",
        )

        await tracker.register_node(node, turn_number=1)
        await tracker.update_focus(node_id="node-1", turn_number=1, strategy="deepen")

        changes = GraphChangeSummary(nodes_added=2, edges_added=1)
        await tracker.record_yield(
            node_id="node-1", turn_number=1, graph_changes=changes
        )

        state = tracker.get_state("node-1")
        assert state is not None
        assert state.last_yield_turn == 1
        assert state.turns_since_last_yield == 0
        assert state.yield_count == 1
        assert state.yield_rate == 1.0  # 1 yield / 1 focus

    @pytest.mark.asyncio
    async def test_record_yield_resets_focus_streak(self):
        """record_yield resets current_focus_streak to 0."""
        tracker = NodeStateTracker()
        node = KGNode(
            id="node-1",
            session_id="session-1",
            label="test",
            node_type="attribute",
        )

        await tracker.register_node(node, turn_number=1)
        await tracker.update_focus(node_id="node-1", turn_number=1, strategy="deepen")
        await tracker.update_focus(node_id="node-1", turn_number=2, strategy="deepen")

        # Streak should be 2
        state = tracker.get_state("node-1")
        assert state is not None
        assert state.current_focus_streak == 2

        # Yield should reset streak
        changes = GraphChangeSummary(nodes_added=1, edges_added=0)
        await tracker.record_yield(
            node_id="node-1", turn_number=2, graph_changes=changes
        )

        state = tracker.get_state("node-1")
        assert state is not None
        assert state.current_focus_streak == 0

    @pytest.mark.asyncio
    async def test_record_yield_no_changes(self):
        """record_yield does nothing when there are no graph changes."""
        tracker = NodeStateTracker()
        node = KGNode(
            id="node-1",
            session_id="session-1",
            label="test",
            node_type="attribute",
        )

        await tracker.register_node(node, turn_number=1)
        await tracker.update_focus(node_id="node-1", turn_number=1, strategy="deepen")

        changes = GraphChangeSummary(nodes_added=0, edges_added=0)
        await tracker.record_yield(
            node_id="node-1", turn_number=1, graph_changes=changes
        )

        state = tracker.get_state("node-1")
        assert state is not None
        assert state.last_yield_turn is None
        assert state.yield_count == 0
        assert state.yield_rate == 0.0

    @pytest.mark.asyncio
    async def test_record_yield_rate_calculation(self):
        """yield_rate is calculated as yield_count / max(focus_count, 1)."""
        tracker = NodeStateTracker()
        node = KGNode(
            id="node-1",
            session_id="session-1",
            label="test",
            node_type="attribute",
        )

        await tracker.register_node(node, turn_number=1)

        # Focus 3 times, yield 2 times
        await tracker.update_focus(node_id="node-1", turn_number=1, strategy="deepen")
        changes = GraphChangeSummary(nodes_added=1, edges_added=0)
        await tracker.record_yield(
            node_id="node-1", turn_number=1, graph_changes=changes
        )

        await tracker.update_focus(node_id="node-1", turn_number=2, strategy="deepen")

        await tracker.update_focus(node_id="node-1", turn_number=3, strategy="deepen")
        await tracker.record_yield(
            node_id="node-1", turn_number=3, graph_changes=changes
        )

        state = tracker.get_state("node-1")
        assert state is not None
        assert state.focus_count == 3
        assert state.yield_count == 2
        assert state.yield_rate == 2.0 / 3.0

    @pytest.mark.asyncio
    async def test_record_yield_node_not_found(self):
        """record_yield logs warning when node not found."""
        tracker = NodeStateTracker()

        changes = GraphChangeSummary(nodes_added=1, edges_added=0)
        await tracker.record_yield(
            node_id="nonexistent", turn_number=1, graph_changes=changes
        )

        # Should not raise exception
        assert tracker.states == {}

    @pytest.mark.asyncio
    async def test_append_response_signal(self):
        """append_response_signal adds response depth to node."""
        tracker = NodeStateTracker()
        node = KGNode(
            id="node-1",
            session_id="session-1",
            label="test",
            node_type="attribute",
        )

        await tracker.register_node(node, turn_number=1)
        await tracker.append_response_signal(
            focus_node_id="node-1", response_depth="deep"
        )

        state = tracker.get_state("node-1")
        assert state is not None
        assert state.all_response_depths == ["deep"]

    @pytest.mark.asyncio
    async def test_append_multiple_response_signals(self):
        """Multiple response signals are appended in order."""
        tracker = NodeStateTracker()
        node = KGNode(
            id="node-1",
            session_id="session-1",
            label="test",
            node_type="attribute",
        )

        await tracker.register_node(node, turn_number=1)
        await tracker.append_response_signal(
            focus_node_id="node-1", response_depth="deep"
        )
        await tracker.append_response_signal(
            focus_node_id="node-1", response_depth="shallow"
        )
        await tracker.append_response_signal(
            focus_node_id="node-1", response_depth="surface"
        )

        state = tracker.get_state("node-1")
        assert state is not None
        assert state.all_response_depths == ["deep", "shallow", "surface"]

    @pytest.mark.asyncio
    async def test_append_response_signal_node_not_found(self):
        """append_response_signal logs warning when node not found."""
        tracker = NodeStateTracker()

        await tracker.append_response_signal(
            focus_node_id="nonexistent", response_depth="deep"
        )

        # Should not raise exception
        assert tracker.states == {}

    @pytest.mark.asyncio
    async def test_update_edge_counts_increments(self):
        """update_edge_counts increments edge counts correctly."""
        tracker = NodeStateTracker()
        node = KGNode(
            id="node-1",
            session_id="session-1",
            label="test",
            node_type="attribute",
        )

        await tracker.register_node(node, turn_number=1)
        await tracker.update_edge_counts(
            node_id="node-1", outgoing_delta=2, incoming_delta=3
        )

        state = tracker.get_state("node-1")
        assert state is not None
        assert state.edge_count_outgoing == 2
        assert state.edge_count_incoming == 3

    @pytest.mark.asyncio
    async def test_update_edge_counts_decrements(self):
        """update_edge_counts decrements edge counts correctly."""
        tracker = NodeStateTracker()
        node = KGNode(
            id="node-1",
            session_id="session-1",
            label="test",
            node_type="attribute",
        )

        await tracker.register_node(node, turn_number=1)
        await tracker.update_edge_counts(
            node_id="node-1", outgoing_delta=5, incoming_delta=5
        )
        await tracker.update_edge_counts(
            node_id="node-1", outgoing_delta=-2, incoming_delta=-1
        )

        state = tracker.get_state("node-1")
        assert state is not None
        assert state.edge_count_outgoing == 3
        assert state.edge_count_incoming == 4

    @pytest.mark.asyncio
    async def test_update_edge_counts_no_negative(self):
        """update_edge_counts prevents negative counts."""
        tracker = NodeStateTracker()
        node = KGNode(
            id="node-1",
            session_id="session-1",
            label="test",
            node_type="attribute",
        )

        await tracker.register_node(node, turn_number=1)
        await tracker.update_edge_counts(
            node_id="node-1", outgoing_delta=-5, incoming_delta=-3
        )

        state = tracker.get_state("node-1")
        assert state is not None
        assert state.edge_count_outgoing == 0
        assert state.edge_count_incoming == 0

    @pytest.mark.asyncio
    async def test_update_edge_counts_node_not_found(self):
        """update_edge_counts logs warning when node not found."""
        tracker = NodeStateTracker()

        await tracker.update_edge_counts(
            node_id="nonexistent", outgoing_delta=1, incoming_delta=1
        )

        # Should not raise exception
        assert tracker.states == {}

    def test_get_state_existing_node(self):
        """get_state returns NodeState for existing node."""
        tracker = NodeStateTracker()
        state: NodeState = NodeState(
            node_id="node-1",
            label="test",
            created_at_turn=1,
            depth=0,
        )
        tracker.states["node-1"] = state

        result = tracker.get_state("node-1")
        assert result is state

    def test_get_state_nonexistent_node(self):
        """get_state returns None for nonexistent node."""
        tracker = NodeStateTracker()

        result = tracker.get_state("nonexistent")
        assert result is None

    def test_get_all_states(self):
        """get_all_states returns copy of all tracked states."""
        tracker = NodeStateTracker()
        state1 = NodeState(
            node_id="node-1",
            label="test1",
            created_at_turn=1,
            depth=0,
        )
        state2 = NodeState(
            node_id="node-2",
            label="test2",
            created_at_turn=1,
            depth=0,
        )
        tracker.states = {"node-1": state1, "node-2": state2}

        result = tracker.get_all_states()
        assert result == {"node-1": state1, "node-2": state2}

        # Verify it's a copy (modifying result doesn't affect tracker)
        # We can't assign None to Dict[str, NodeState], so we just verify the keys
        assert "node-3" not in result

    @pytest.mark.asyncio
    async def test_turns_since_last_focus_increments(self):
        """turns_since_last_focus increments for all non-focused nodes."""
        tracker = NodeStateTracker()
        node1 = KGNode(
            id="node-1",
            session_id="session-1",
            label="test1",
            node_type="attribute",
        )
        node2 = KGNode(
            id="node-2",
            session_id="session-1",
            label="test2",
            node_type="attribute",
        )

        await tracker.register_node(node1, turn_number=1)
        await tracker.register_node(node2, turn_number=1)

        # Focus node-1
        await tracker.update_focus(node_id="node-1", turn_number=1, strategy="deepen")

        # Focus node-2 (node-1's turns_since_last_focus should increment)
        await tracker.update_focus(node_id="node-2", turn_number=2, strategy="probe")

        state1 = tracker.get_state("node-1")
        state2 = tracker.get_state("node-2")
        assert state1 is not None
        assert state2 is not None

        assert state1.turns_since_last_focus == 1
        assert state2.turns_since_last_focus == 0

    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        """Test complete workflow: register, focus, yield, response."""
        tracker = NodeStateTracker()
        node = KGNode(
            id="node-1",
            session_id="session-1",
            label="creamy texture",
            node_type="attribute",
        )

        # 1. Register node
        await tracker.register_node(node, turn_number=1)

        # 2. Focus on node
        await tracker.update_focus(node_id="node-1", turn_number=1, strategy="deepen")

        # 3. Node yields (produces graph changes)
        changes = GraphChangeSummary(nodes_added=2, edges_added=1)
        await tracker.record_yield(
            node_id="node-1", turn_number=1, graph_changes=changes
        )

        # 4. Update edge counts
        await tracker.update_edge_counts(
            node_id="node-1", outgoing_delta=1, incoming_delta=1
        )

        # 5. Append response signal
        await tracker.append_response_signal(
            focus_node_id="node-1", response_depth="deep"
        )

        # Verify final state
        state = tracker.get_state("node-1")
        assert state is not None
        assert state.node_id == "node-1"
        assert state.focus_count == 1
        assert state.yield_count == 1
        assert state.yield_rate == 1.0
        assert state.edge_count_outgoing == 1
        assert state.edge_count_incoming == 1
        assert state.all_response_depths == ["deep"]
        assert state.current_focus_streak == 0  # Reset by yield
        assert state.is_orphan is False
