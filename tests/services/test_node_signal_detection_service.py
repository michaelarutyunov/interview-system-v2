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


def test_all_node_signals_auto_registered():
    """Verify all NodeSignalDetector subclasses are auto-registered via __init_subclass__."""
    import src.signals  # noqa: F401 — ensure all modules are imported
    from src.signals.graph.node_base import NodeSignalDetector

    node_classes = NodeSignalDetector.get_all_node_signal_classes()
    signal_names = {cls.signal_name for cls in node_classes}

    expected = {
        "graph.node.exhausted",
        "graph.node.exhaustion_score",
        "graph.node.yield_stagnation",
        "graph.node.focus_streak",
        "graph.node.is_current_focus",
        "graph.node.recency_score",
        "graph.node.is_orphan",
        "graph.node.edge_count",
        "graph.node.has_outgoing",
        "graph.node.novelty",
        "graph.node.focus_count",
        "graph.node.canonical_novelty",
        "technique.node.strategy_repetition",
        "meta.node.opportunity",
    }
    assert signal_names == expected, (
        f"Missing: {expected - signal_names}, Extra: {signal_names - expected}"
    )


@pytest.mark.asyncio
async def test_detect_raises_on_empty_registry(monkeypatch):
    """Verify detect() raises RuntimeError if no node signal detectors are registered."""
    import src.signals  # noqa: F401
    from src.signals.graph.node_base import NodeSignalDetector
    from src.signals.signal_base import SignalDetector

    # Temporarily empty the registry and the node signal class list
    monkeypatch.setattr(SignalDetector, "_registry", {})
    monkeypatch.setattr(NodeSignalDetector, "get_all_node_signal_classes", classmethod(lambda cls: []))

    service = NodeSignalDetectionService()
    mock_context = MagicMock()
    mock_graph_state = MagicMock()
    mock_node_tracker = MagicMock()
    mock_node_tracker.get_all_states.return_value = {"node-1": MagicMock()}

    with pytest.raises(RuntimeError, match="No NodeSignalDetector subclasses"):
        await service.detect(
            context=mock_context,
            graph_state=mock_graph_state,
            response_text="test",
            node_tracker=mock_node_tracker,
        )
