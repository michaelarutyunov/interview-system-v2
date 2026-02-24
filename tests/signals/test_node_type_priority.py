"""Tests for NodeTypePrioritySignal detector."""

import pytest
from unittest.mock import MagicMock

from src.domain.models.node_state import NodeState
from src.signals.graph.node_signals import NodeTypePrioritySignal


@pytest.fixture
def node_tracker_with_types():
    """Create a mock node tracker with nodes of different types."""
    tracker = MagicMock()
    tracker.get_all_states.return_value = {
        "node-1": NodeState(
            node_id="node-1",
            label="skepticism about messaging",
            created_at_turn=2,
            depth=0,
            node_type="pain_point",
        ),
        "node-2": NodeState(
            node_id="node-2",
            label="store out of stock",
            created_at_turn=2,
            depth=0,
            node_type="job_trigger",
        ),
        "node-3": NodeState(
            node_id="node-3",
            label="enjoy rich coffee",
            created_at_turn=2,
            depth=0,
            node_type="job_statement",
        ),
        "node-4": NodeState(
            node_id="node-4",
            label="grinding fresh",
            created_at_turn=2,
            depth=0,
            node_type="solution_approach",
        ),
    }
    return tracker


class TestNodeTypePrioritySignal:
    """Tests for graph.node.type_priority signal."""

    @pytest.mark.asyncio
    async def test_returns_priorities_for_all_nodes(self, node_tracker_with_types):
        """Signal returns a priority value for every tracked node."""
        priorities = {"pain_point": 0.8, "job_trigger": 0.7, "job_statement": 0.4}
        detector = NodeTypePrioritySignal(
            node_tracker_with_types, node_type_priorities=priorities
        )
        result = await detector.detect(
            context=MagicMock(), graph_state=MagicMock(), response_text=""
        )

        assert len(result) == 4
        assert result["node-1"] == 0.8  # pain_point
        assert result["node-2"] == 0.7  # job_trigger
        assert result["node-3"] == 0.4  # job_statement

    @pytest.mark.asyncio
    async def test_unknown_type_gets_default(self, node_tracker_with_types):
        """Nodes with types not in priorities map get default 0.5."""
        priorities = {"pain_point": 0.8}  # only pain_point defined
        detector = NodeTypePrioritySignal(
            node_tracker_with_types, node_type_priorities=priorities
        )
        result = await detector.detect(
            context=MagicMock(), graph_state=MagicMock(), response_text=""
        )

        assert result["node-1"] == 0.8  # pain_point: defined
        assert result["node-2"] == 0.5  # job_trigger: default
        assert result["node-3"] == 0.5  # job_statement: default
        assert result["node-4"] == 0.5  # solution_approach: default

    @pytest.mark.asyncio
    async def test_empty_priorities_all_default(self, node_tracker_with_types):
        """With empty priorities map, all nodes get default 0.5."""
        detector = NodeTypePrioritySignal(
            node_tracker_with_types, node_type_priorities={}
        )
        result = await detector.detect(
            context=MagicMock(), graph_state=MagicMock(), response_text=""
        )

        for node_id in result:
            assert result[node_id] == 0.5

    @pytest.mark.asyncio
    async def test_signal_name(self, node_tracker_with_types):
        """Signal has correct signal_name."""
        detector = NodeTypePrioritySignal(
            node_tracker_with_types, node_type_priorities={}
        )
        assert detector.signal_name == "graph.node.type_priority"
