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
async def test_slot_saturation_returns_categories(node_tracker):
    """Returns categorized saturation levels from saturation_map."""
    saturation_map = {
        "node-1": 1,  # low (0-2)
        "node-2": 3,  # medium (3-5)
        "node-3": 8,  # high (6+)
        # node-4 not mapped
    }

    signal = NodeSlotSaturationSignal(node_tracker, slot_saturation_map=saturation_map)
    result = await signal.detect(context=None, graph_state=None, response_text="")

    assert result == {
        "node-1": "low",
        "node-2": "medium",
        "node-3": "high",
        "node-4": "low",  # unmapped nodes default to "low" (0)
    }


@pytest.mark.asyncio
async def test_slot_saturation_boundary_values(node_tracker):
    """Correctly categorizes boundary values."""
    saturation_map = {
        "node-1": 0,  # low
        "node-2": 2,  # low (boundary)
        "node-3": 3,  # medium (boundary)
        "node-4": 5,  # medium (boundary)
    }

    signal = NodeSlotSaturationSignal(node_tracker, slot_saturation_map=saturation_map)
    result = await signal.detect(context=None, graph_state=None, response_text="")

    assert result == {
        "node-1": "low",
        "node-2": "low",
        "node-3": "medium",
        "node-4": "medium",
    }


@pytest.mark.asyncio
async def test_slot_saturation_empty_map(node_tracker):
    """Returns 'low' for all nodes when saturation_map is empty."""
    signal = NodeSlotSaturationSignal(node_tracker, slot_saturation_map={})
    result = await signal.detect(context=None, graph_state=None, response_text="")

    assert result == {
        "node-1": "low",
        "node-2": "low",
        "node-3": "low",
        "node-4": "low",
    }


@pytest.mark.asyncio
async def test_slot_saturation_none_map(node_tracker):
    """Returns 'low' for all nodes when saturation_map is None."""
    signal = NodeSlotSaturationSignal(node_tracker, slot_saturation_map=None)
    result = await signal.detect(context=None, graph_state=None, response_text="")

    assert result == {
        "node-1": "low",
        "node-2": "low",
        "node-3": "low",
        "node-4": "low",
    }


def test_slot_saturation_signal_name(node_tracker):
    """Signal has correct namespaced name."""
    signal = NodeSlotSaturationSignal(node_tracker)
    assert signal.signal_name == "graph.node.slot_saturation"
