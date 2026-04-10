"""Tests for global chain topology signals."""

from typing import NamedTuple
from unittest.mock import MagicMock, patch

import pytest

from src.signals.graph.global_chain_signals import GlobalChainTopologySignal


class MockNode(NamedTuple):
    id: str
    node_type: str


class MockEdge(NamedTuple):
    source_node_id: str
    target_node_id: str
    edge_type: str = "leads_to"


@pytest.fixture
def mock_methodology_schema():
    """Mock methodology schema with MEC-like ontology."""
    attr = MagicMock()
    attr.name = "attribute"
    attr.level = 1
    attr.terminal = False

    func = MagicMock()
    func.name = "functional_consequence"
    func.level = 2
    func.terminal = False

    term = MagicMock()
    term.name = "terminal_value"
    term.level = 3
    term.terminal = True

    ontology = MagicMock(nodes=[attr, func, term])
    schema = MagicMock(ontology=ontology)
    schema.get_terminal_node_types.return_value = ["terminal_value"]
    return schema


def _make_context(methodology="means_end_chain", session_id="test-session"):
    ctx = MagicMock()
    ctx.methodology = methodology
    ctx.session_id = session_id
    return ctx


class TestGlobalChainTopology:
    @pytest.mark.asyncio
    async def test_incomplete_chain_counts_frontiers(self, mock_methodology_schema):
        """A→B with no B→terminal: frontier=1 (B), ungrounded=1 (T has no incoming)."""
        nodes = [
            MockNode("a", "attribute"),
            MockNode("b", "functional_consequence"),
            MockNode("t", "terminal_value"),
        ]
        edges = [MockEdge("a", "b")]  # B has no outgoing edge to terminal

        detector = GlobalChainTopologySignal()
        with (
            patch(
                "src.signals.graph.global_chain_signals.load_methodology",
                return_value=mock_methodology_schema,
            ),
            patch.object(detector, "_get_session_nodes", return_value=nodes),
            patch.object(detector, "_get_session_edges", return_value=edges),
        ):
            result = await detector.detect(_make_context(), None, "")
            assert result["graph.global.frontier_count"] == 1  # B is frontier
            assert result["graph.global.ungrounded_count"] == 1  # T has no incoming

    @pytest.mark.asyncio
    async def test_ungrounded_spontaneous_node(self, mock_methodology_schema):
        """A high-level node with no incoming edges = ungrounded."""
        nodes = [
            MockNode("a", "attribute"),
            MockNode("t", "terminal_value"),  # spontaneous terminal, no incoming
        ]
        edges = []  # No edges at all

        detector = GlobalChainTopologySignal()
        with (
            patch(
                "src.signals.graph.global_chain_signals.load_methodology",
                return_value=mock_methodology_schema,
            ),
            patch.object(detector, "_get_session_nodes", return_value=nodes),
            patch.object(detector, "_get_session_edges", return_value=edges),
        ):
            result = await detector.detect(_make_context(), None, "")
            assert result["graph.global.frontier_count"] == 1  # a has no outgoing
            assert result["graph.global.ungrounded_count"] == 1  # t has no incoming

    @pytest.mark.asyncio
    async def test_complete_chain_no_counts(self, mock_methodology_schema):
        """A→B→T: complete chain = no frontiers, no ungrounded."""
        nodes = [
            MockNode("a", "attribute"),
            MockNode("b", "functional_consequence"),
            MockNode("t", "terminal_value"),
        ]
        edges = [MockEdge("a", "b"), MockEdge("b", "t")]

        detector = GlobalChainTopologySignal()
        with (
            patch(
                "src.signals.graph.global_chain_signals.load_methodology",
                return_value=mock_methodology_schema,
            ),
            patch.object(detector, "_get_session_nodes", return_value=nodes),
            patch.object(detector, "_get_session_edges", return_value=edges),
        ):
            result = await detector.detect(_make_context(), None, "")
            assert result["graph.global.frontier_count"] == 0
            assert result["graph.global.ungrounded_count"] == 0

    @pytest.mark.asyncio
    async def test_non_chain_methodology_returns_empty(self):
        """JTBD with all level-0 nodes → non-chain → empty dict."""
        job = MagicMock()
        job.name = "job_statement"
        job.level = 0
        job.terminal = False

        emotional = MagicMock()
        emotional.name = "emotional_job"
        emotional.level = 0
        emotional.terminal = True

        ontology = MagicMock(nodes=[job, emotional])
        schema = MagicMock(ontology=ontology)
        schema.get_terminal_node_types.return_value = ["emotional_job"]

        detector = GlobalChainTopologySignal()
        with patch(
            "src.signals.graph.global_chain_signals.load_methodology",
            return_value=schema,
        ):
            result = await detector.detect(_make_context("jobs_to_be_done"), None, "")
            assert result == {}

    @pytest.mark.asyncio
    async def test_empty_graph(self, mock_methodology_schema):
        """No nodes → zero counts."""
        detector = GlobalChainTopologySignal()
        with (
            patch(
                "src.signals.graph.global_chain_signals.load_methodology",
                return_value=mock_methodology_schema,
            ),
            patch.object(detector, "_get_session_nodes", return_value=[]),
            patch.object(detector, "_get_session_edges", return_value=[]),
        ):
            result = await detector.detect(_make_context(), None, "")
            assert result["graph.global.frontier_count"] == 0
            assert result["graph.global.ungrounded_count"] == 0
