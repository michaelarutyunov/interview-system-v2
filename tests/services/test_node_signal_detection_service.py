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
        "convgraph.node.exhausted",
        "convgraph.node.exhaustion",
        "convgraph.node.yield_stagnation",
        "convgraph.node.focus.streak",
        "convgraph.node.is_current_focus",
        "convgraph.node.recency",
        "convgraph.node.is_orphan",
        "convgraph.node.edge_count",
        "convgraph.node.has_outgoing",
        "convgraph.node.novelty",
        "convgraph.node.focus.count",
        "canongraph.node.novelty",
        "interview.focus.streak",
        # Chain topology (computed by ChainTopologySignalDetector, flat sentinels register names)
        "convgraph.node.chain.role",
        "convgraph.node.chain.gap.above",
        "convgraph.node.chain.gap.below",
        "convgraph.node.chain.level.skip",
        "convgraph.node.chain.branching_deficit",
        "convgraph.node.chain.fan_in",
        "convgraph.node.chain.level.gap_size",
        "convgraph.node.chain.has_attribute_foundation",
        "convgraph.node.chain.has_terminal_apex",
        # Per-concept LLM quality (Phase C)
        "convgraph.node.llm.elaboration",
        "convgraph.node.llm.charge",
        "convgraph.node.llm.has_quality_data",
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
    monkeypatch.setattr(
        NodeSignalDetector, "get_all_node_signal_classes", classmethod(lambda cls: [])
    )

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
