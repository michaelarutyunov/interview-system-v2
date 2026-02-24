"""Tests for NodeSlotSaturationSignal."""

import pytest
from unittest.mock import MagicMock

from src.domain.models.node_state import NodeState
from src.signals.graph.node_signals import NodeSlotSaturationSignal


@pytest.fixture
def node_tracker():
    """Create a mock node tracker with tracked nodes."""
    tracker = MagicMock()
    tracker.get_all_states.return_value = {
        "node-1": NodeState(
            node_id="node-1",
            label="Flavor",
            created_at_turn=1,
            depth=0,
            node_type="attribute",
        ),
        "node-2": NodeState(
            node_id="node-2",
            label="Cost",
            created_at_turn=1,
            depth=0,
            node_type="attribute",
        ),
        "node-3": NodeState(
            node_id="node-3",
            label="Convenience",
            created_at_turn=1,
            depth=0,
            node_type="consequence",
        ),
        "node-4": NodeState(
            node_id="node-4",
            label="Fresh",
            created_at_turn=1,
            depth=0,
            node_type="attribute",
        ),
    }
    return tracker


@pytest.mark.asyncio
async def test_slot_saturation_returns_float_scores(node_tracker):
    """Returns continuous freshness scores (0.0-1.0) from saturation_map."""
    saturation_map = {
        "node-1": 1,  # 1 - (1/8) = 0.875
        "node-2": 3,  # 1 - (3/8) = 0.625
        "node-3": 8,  # 1 - (8/8) = 0.0 (max saturated)
        # node-4 not mapped → 1 - (0/8) = 1.0
    }

    signal = NodeSlotSaturationSignal(node_tracker, slot_saturation_map=saturation_map)
    result = await signal.detect(context=None, graph_state=None, response_text="")

    assert result == {
        "node-1": 0.875,
        "node-2": 0.625,
        "node-3": 0.0,
        "node-4": 1.0,
    }


@pytest.mark.asyncio
async def test_slot_saturation_linear_distribution(node_tracker):
    """Scores distribute linearly relative to max support count."""
    saturation_map = {
        "node-1": 1,  # 1 - (1/5) = 0.8
        "node-2": 3,  # 1 - (3/5) = 0.4
        "node-3": 5,  # 1 - (5/5) = 0.0 (max)
        # node-4 not mapped → 1.0
    }

    signal = NodeSlotSaturationSignal(node_tracker, slot_saturation_map=saturation_map)
    result = await signal.detect(context=None, graph_state=None, response_text="")

    assert result["node-1"] == pytest.approx(0.8)
    assert result["node-2"] == pytest.approx(0.4)
    assert result["node-3"] == pytest.approx(0.0)
    assert result["node-4"] == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_slot_saturation_empty_map(node_tracker):
    """Returns 1.0 (fully fresh) for all nodes when saturation_map is empty."""
    signal = NodeSlotSaturationSignal(node_tracker, slot_saturation_map={})
    result = await signal.detect(context=None, graph_state=None, response_text="")

    assert result == {
        "node-1": 1.0,
        "node-2": 1.0,
        "node-3": 1.0,
        "node-4": 1.0,
    }


@pytest.mark.asyncio
async def test_slot_saturation_none_map(node_tracker):
    """Returns 1.0 (fully fresh) for all nodes when saturation_map is None."""
    signal = NodeSlotSaturationSignal(node_tracker, slot_saturation_map=None)
    result = await signal.detect(context=None, graph_state=None, response_text="")

    assert result == {
        "node-1": 1.0,
        "node-2": 1.0,
        "node-3": 1.0,
        "node-4": 1.0,
    }


def test_slot_saturation_signal_name(node_tracker):
    """Signal has correct namespaced name."""
    signal = NodeSlotSaturationSignal(node_tracker)
    assert signal.signal_name == "graph.node.slot_saturation"


class TestComputeSaturationScore:
    """Unit tests for _compute_saturation_score formula."""

    def test_standard_distribution(self, node_tracker):
        """Scores distribute linearly: unmapped=1.0, max=0.0, mid proportional."""
        signal = NodeSlotSaturationSignal(
            node_tracker,
            slot_saturation_map={"node-a": 1, "node-b": 3, "node-c": 5},
        )
        assert signal._compute_saturation_score(0) == 1.0   # unmapped
        assert signal._compute_saturation_score(5) == 0.0   # max saturated
        assert signal._compute_saturation_score(1) == pytest.approx(0.8)   # 1-(1/5)
        assert signal._compute_saturation_score(3) == pytest.approx(0.4)   # 1-(3/5)

    def test_empty_map_returns_fresh(self, node_tracker):
        """Empty saturation map means all nodes are fresh."""
        signal = NodeSlotSaturationSignal(
            node_tracker, slot_saturation_map={}
        )
        assert signal._compute_saturation_score(0) == 1.0

    def test_single_node_in_map(self, node_tracker):
        """Single-node map: that node is max saturated, unmapped is fresh."""
        signal = NodeSlotSaturationSignal(
            node_tracker, slot_saturation_map={"node-a": 3}
        )
        assert signal._compute_saturation_score(3) == 0.0   # only node = max
        assert signal._compute_saturation_score(0) == 1.0   # unmapped = fresh

    def test_all_zero_support(self, node_tracker):
        """All nodes with zero support → fresh (avoids division by zero)."""
        signal = NodeSlotSaturationSignal(
            node_tracker, slot_saturation_map={"node-a": 0, "node-b": 0}
        )
        assert signal._compute_saturation_score(0) == 1.0
