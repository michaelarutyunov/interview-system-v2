"""
Tests for NodeSignalDetectionService.

Note: The signal detectors require properly structured NodeState objects.
Full integration testing happens in the main test suite where real
NodeStateTracker instances are used.
"""

from unittest.mock import MagicMock

import pytest

from src.services.node_signal_detection_service import NodeSignalDetectionService


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
