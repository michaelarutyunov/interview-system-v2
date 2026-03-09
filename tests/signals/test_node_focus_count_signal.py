"""Tests for NodeFocusCountSignal — cumulative focus count across the interview."""

import pytest
from unittest.mock import MagicMock

from src.signals.graph.node_signals import NodeFocusCountSignal
from src.domain.models.node_state import NodeState


def _make_node_state(node_id: str, focus_count: int) -> NodeState:
    """Create a minimal NodeState with a given focus_count."""
    return NodeState(
        node_id=node_id,
        label=f"node_{node_id}",
        created_at_turn=1,
        depth=1,
        node_type="concept",
        focus_count=focus_count,
    )


def _make_signal(states: dict[str, NodeState]) -> NodeFocusCountSignal:
    """Instantiate NodeFocusCountSignal with a mocked NodeStateTracker."""
    tracker = MagicMock()
    tracker.get_all_states.return_value = states
    signal = NodeFocusCountSignal(node_tracker=tracker)
    return signal


class TestNodeFocusCountCategorization:
    """Unit tests for _categorize_count helper."""

    def test_focus_count_zero_returns_none(self):
        signal = _make_signal({})
        assert signal._categorize_count(0) == "none"

    def test_focus_count_one_returns_low(self):
        signal = _make_signal({})
        assert signal._categorize_count(1) == "low"

    def test_focus_count_two_returns_low(self):
        signal = _make_signal({})
        assert signal._categorize_count(2) == "low"

    def test_focus_count_three_returns_medium(self):
        signal = _make_signal({})
        assert signal._categorize_count(3) == "medium"

    def test_focus_count_four_returns_medium(self):
        signal = _make_signal({})
        assert signal._categorize_count(4) == "medium"

    def test_focus_count_five_returns_high(self):
        signal = _make_signal({})
        assert signal._categorize_count(5) == "high"

    def test_focus_count_large_returns_high(self):
        signal = _make_signal({})
        assert signal._categorize_count(20) == "high"


class TestNodeFocusCountDetect:
    """Integration tests for the detect() method."""

    @pytest.mark.asyncio
    async def test_never_focused_node_returns_none(self):
        states = {"node-a": _make_node_state("node-a", focus_count=0)}
        signal = _make_signal(states)
        result = await signal.detect(context=None, graph_state=None, response_text=None)
        assert result == {"node-a": "none"}

    @pytest.mark.asyncio
    async def test_low_focus_count_returns_low(self):
        states = {"node-a": _make_node_state("node-a", focus_count=2)}
        signal = _make_signal(states)
        result = await signal.detect(context=None, graph_state=None, response_text=None)
        assert result == {"node-a": "low"}

    @pytest.mark.asyncio
    async def test_medium_focus_count_returns_medium(self):
        states = {"node-a": _make_node_state("node-a", focus_count=4)}
        signal = _make_signal(states)
        result = await signal.detect(context=None, graph_state=None, response_text=None)
        assert result == {"node-a": "medium"}

    @pytest.mark.asyncio
    async def test_high_focus_count_returns_high(self):
        states = {"node-a": _make_node_state("node-a", focus_count=6)}
        signal = _make_signal(states)
        result = await signal.detect(context=None, graph_state=None, response_text=None)
        assert result == {"node-a": "high"}

    @pytest.mark.asyncio
    async def test_all_nodes_are_included_in_result(self):
        """Verify signal fires for all tracked nodes, not just the focused one."""
        states = {
            "node-a": _make_node_state("node-a", focus_count=0),
            "node-b": _make_node_state("node-b", focus_count=2),
            "node-c": _make_node_state("node-c", focus_count=4),
            "node-d": _make_node_state("node-d", focus_count=7),
        }
        signal = _make_signal(states)
        result = await signal.detect(context=None, graph_state=None, response_text=None)

        assert result == {
            "node-a": "none",
            "node-b": "low",
            "node-c": "medium",
            "node-d": "high",
        }

    @pytest.mark.asyncio
    async def test_empty_tracker_returns_empty_dict(self):
        signal = _make_signal({})
        result = await signal.detect(context=None, graph_state=None, response_text=None)
        assert result == {}


class TestNodeFocusCountSignalMetadata:
    """Verify signal name and class attributes."""

    def test_signal_name(self):
        assert NodeFocusCountSignal.signal_name == "graph.node.focus_count"

    def test_requires_node_tracker(self):
        assert NodeFocusCountSignal.requires_node_tracker is True
