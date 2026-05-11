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
        "convgraph.node.chain.has_origin_level_ancestor",
        "convgraph.node.chain.has_max_level_ancestor",
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


class TestKeyspaceGuard:
    """B4: Signal detector keyspace mismatch raises hard ValueError."""

    @pytest.mark.asyncio
    async def test_slot_key_from_detector_raises(self, monkeypatch):
        """Detector emitting a slot key against surface-keyed tracker raises ValueError."""
        import src.signals  # noqa: F401
        from src.signals.graph.node_base import NodeSignalDetector

        # Create a detector that returns a slot key not in the tracker
        class FakeDetector(NodeSignalDetector):
            signal_name = "test.fake_slot_key"
            description = "test"

            async def detect(self, context, graph_state, response_text):  # noqa: ARG002
                return {"slot_unknown_X": 0.5}

        mock_context = MagicMock()
        mock_graph_state = MagicMock()
        mock_node_tracker = MagicMock()
        # Tracker has only surface UUID keys
        mock_node_tracker.get_all_states.return_value = {
            "uuid-abc": MagicMock(),
            "uuid-def": MagicMock(),
        }

        # Patch get_all_node_signal_classes to return only our fake detector
        monkeypatch.setattr(
            NodeSignalDetector,
            "get_all_node_signal_classes",
            classmethod(lambda cls: [FakeDetector]),
        )

        service = NodeSignalDetectionService()
        with pytest.raises(Exception, match="slot_unknown_X"):
            await service.detect(
                context=mock_context,
                graph_state=mock_graph_state,
                response_text="test",
                node_tracker=mock_node_tracker,
            )

    @pytest.mark.asyncio
    async def test_surface_key_from_detector_merges(self, monkeypatch):
        """Detector emitting a surface UUID in tracker keyspace merges successfully."""
        import src.signals  # noqa: F401
        from src.signals.graph.node_base import NodeSignalDetector

        class FakeDetector(NodeSignalDetector):
            signal_name = "test.fake_surface_key"
            description = "test"

            async def detect(self, context, graph_state, response_text):  # noqa: ARG002
                return {"uuid-abc": 0.7}

        mock_context = MagicMock()
        mock_graph_state = MagicMock()
        mock_node_tracker = MagicMock()
        mock_node_tracker.get_all_states.return_value = {
            "uuid-abc": MagicMock(),
        }

        monkeypatch.setattr(
            NodeSignalDetector,
            "get_all_node_signal_classes",
            classmethod(lambda cls: [FakeDetector]),
        )

        service = NodeSignalDetectionService()
        result = await service.detect(
            context=mock_context,
            graph_state=mock_graph_state,
            response_text="test",
            node_tracker=mock_node_tracker,
        )

        assert "uuid-abc" in result
        assert result["uuid-abc"]["test.fake_surface_key"] == 0.7
