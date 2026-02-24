"""
Tests for NodeSignalDetectionService.

Note: The signal detectors require properly structured NodeState objects.
Full integration testing happens in the main test suite where real
NodeStateTracker instances are used.
"""

from unittest.mock import MagicMock

import pytest

from src.services.node_signal_detection_service import NodeSignalDetectionService
from src.domain.models.node_state import NodeState


@pytest.fixture
def node_signal_service():
    """Create a NodeSignalDetectionService instance."""
    return NodeSignalDetectionService()


@pytest.mark.asyncio
async def test_node_signal_service_instantiation(node_signal_service):
    """Test that NodeSignalDetectionService can be instantiated."""
    assert node_signal_service is not None


@pytest.mark.asyncio
async def test_detect_handles_empty_node_tracker(node_signal_service):
    """Test that detect() returns empty dict when node_tracker has no states."""
    mock_context = MagicMock()
    mock_graph_state = MagicMock()
    mock_node_tracker = MagicMock()
    mock_node_tracker.get_all_states.return_value = {}

    result = await node_signal_service.detect(
        context=mock_context,
        graph_state=mock_graph_state,
        response_text="test response",
        node_tracker=mock_node_tracker,
    )

    assert result == {}


@pytest.mark.asyncio
async def test_detect_includes_type_priority_signal(node_signal_service):
    """Test that detect() includes graph.node.type_priority when priorities provided."""
    mock_context = MagicMock()
    mock_graph_state = MagicMock()
    mock_node_tracker = MagicMock()

    mock_node_tracker.get_all_states.return_value = {
        "node-1": NodeState(
            node_id="node-1",
            label="test node",
            created_at_turn=1,
            depth=0,
            node_type="pain_point",
        ),
    }

    result = await node_signal_service.detect(
        context=mock_context,
        graph_state=mock_graph_state,
        response_text="test",
        node_tracker=mock_node_tracker,
        node_type_priorities={"pain_point": 0.9},
    )

    assert "node-1" in result
    assert "graph.node.type_priority" in result["node-1"]
    assert result["node-1"]["graph.node.type_priority"] == 0.9
