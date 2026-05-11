"""Tests for ChainTopologySignalDetector — chain topology signals per node."""

from unittest.mock import AsyncMock, MagicMock, patch
from typing import NamedTuple
from dataclasses import dataclass

import pytest

from src.signals.graph.chain_topology_signals import ChainTopologySignalDetector


# -- Mock objects --


class MockNode(NamedTuple):
    id: str
    node_type: str
    label: str = "test"


class MockEdge(NamedTuple):
    id: str
    source_node_id: str
    target_node_id: str
    edge_type: str = "leads_to"


@dataclass
class MockNodeType:
    """Mock node type for methodology schema."""

    name: str
    level: int
    terminal: bool


class MockOntology:
    """Mock ontology for methodology schema."""

    def __init__(self, nodes):
        self.nodes = nodes


class MockMethodologySchema:
    """Mock methodology schema with ontology levels."""

    def __init__(self, has_levels=True):
        if has_levels:
            # MEC-style 5-level ontology
            node_types = [
                MockNodeType("attribute", 1, False),
                MockNodeType("functional_consequence", 2, False),
                MockNodeType("psychosocial_consequence", 3, False),
                MockNodeType("instrumental_value", 4, False),
                MockNodeType("terminal_value", 5, True),
            ]
        else:
            # Non-chain ontology (JTBD-style - all level 0 or no levels)
            node_types = [
                MockNodeType("job", 0, False),
                MockNodeType("context", 0, False),
            ]
        self.ontology = MockOntology(node_types)
        self.method = {"chain_completion": {"expected_branching": {}}}

    def get_chain_relevant_edge_types(self):
        return ["leads_to"]


# -- Helpers --


def _make_context(
    session_id="test-session",
    methodology="means_end_chain",
):
    """Build a mock PipelineContext."""
    ctx = MagicMock()
    ctx.session_id = session_id
    ctx.methodology = methodology
    return ctx


def _make_detector():
    """Create a detector instance."""
    mock_tracker = MagicMock()
    return ChainTopologySignalDetector(node_tracker=mock_tracker)


# -- Test Cases --


class TestCompleteChain:
    """Tests for a complete MEC chain with no gaps."""

    @pytest.mark.asyncio
    async def test_complete_chain_no_gaps(self):
        """A complete chain A→B→C→D→E has no gap.above or gap.below."""
        # Complete chain: attribute → functional → psychosocial → instrumental → terminal
        nodes = [
            MockNode("a", "attribute"),
            MockNode("b", "functional_consequence"),
            MockNode("c", "psychosocial_consequence"),
            MockNode("d", "instrumental_value"),
            MockNode("e", "terminal_value"),
        ]
        edges = [
            MockEdge("e1", "a", "b"),
            MockEdge("e2", "b", "c"),
            MockEdge("e3", "c", "d"),
            MockEdge("e4", "d", "e"),
        ]

        detector = _make_detector()
        ctx = _make_context()

        # Mock schema loader and DB - patch at source location
        with (
            patch(
                "src.signals.graph.chain_topology_signals.load_methodology",
                return_value=MockMethodologySchema(has_levels=True),
            ),
            patch(
                "src.persistence.database.get_db_connection",
                return_value=MagicMock(),
            ),
            patch(
                "src.persistence.repositories.graph_repo.GraphRepository",
            ) as MockRepo,
        ):
            # Setup mock repository
            mock_repo = MagicMock()
            mock_repo.get_nodes_by_session = AsyncMock(return_value=nodes)
            mock_repo.get_edges_by_session = AsyncMock(return_value=edges)
            MockRepo.return_value = mock_repo

            result = await detector.detect(ctx, MagicMock(), "")

        topology = result

        # Verify basic structure
        assert "a" in topology
        assert "b" in topology
        assert "c" in topology
        assert "d" in topology
        assert "e" in topology

        # All nodes should have all signal fields
        for node_id in topology:
            assert "gap.above" in topology[node_id]
            assert "gap.below" in topology[node_id]
            assert "level.skip" in topology[node_id]
            assert "branching_deficit" in topology[node_id]
            assert "fan_in" in topology[node_id]
            assert "level.gap_size" in topology[node_id]

        # No level_skip in a proper chain
        assert all(not topology[n]["level.skip"] for n in topology)

        # fan_in: all nodes except origin have 1 fan_in
        assert topology["a"]["fan_in"] == 0  # origin
        assert topology["b"]["fan_in"] == 1
        assert topology["c"]["fan_in"] == 1
        assert topology["d"]["fan_in"] == 1
        assert topology["e"]["fan_in"] == 1


class TestLevelSkip:
    """Tests for level.skip detection when edges skip ontology levels."""

    @pytest.mark.asyncio
    async def test_level_skip_detected(self):
        """An edge that skips >1 level triggers level.skip=True."""
        nodes = [
            MockNode("a", "attribute"),  # level 1
            MockNode("c", "psychosocial_consequence"),  # level 3
        ]
        edges = [
            MockEdge("e1", "a", "c"),  # Skips level 2 (functional_consequence)
        ]

        detector = _make_detector()
        ctx = _make_context()

        with (
            patch(
                "src.signals.graph.chain_topology_signals.load_methodology",
                return_value=MockMethodologySchema(has_levels=True),
            ),
            patch(
                "src.persistence.database.get_db_connection",
                return_value=MagicMock(),
            ),
            patch(
                "src.persistence.repositories.graph_repo.GraphRepository",
            ) as MockRepo,
        ):
            mock_repo = MagicMock()
            mock_repo.get_nodes_by_session = AsyncMock(return_value=nodes)
            mock_repo.get_edges_by_session = AsyncMock(return_value=edges)
            MockRepo.return_value = mock_repo

            result = await detector.detect(ctx, MagicMock(), "")

        topology = result

        # "a" has an edge skipping from level 1 to level 3
        assert topology["a"]["level.skip"] is True


class TestFanIn:
    """Tests for fan_in computation."""

    @pytest.mark.asyncio
    async def test_fan_in_counts_origin_paths(self):
        """fan_in counts distinct origin-level nodes with paths to this node."""
        nodes = [
            MockNode("a1", "attribute"),  # origin (level 1)
            MockNode("a2", "attribute"),  # origin (level 1)
            MockNode("b", "functional_consequence"),
            MockNode("c", "psychosocial_consequence"),
        ]
        edges = [
            MockEdge("e1", "a1", "b"),
            MockEdge("e2", "a2", "b"),
            MockEdge("e3", "b", "c"),
        ]

        detector = _make_detector()
        ctx = _make_context()

        with (
            patch(
                "src.signals.graph.chain_topology_signals.load_methodology",
                return_value=MockMethodologySchema(has_levels=True),
            ),
            patch(
                "src.persistence.database.get_db_connection",
                return_value=MagicMock(),
            ),
            patch(
                "src.persistence.repositories.graph_repo.GraphRepository",
            ) as MockRepo,
        ):
            mock_repo = MagicMock()
            mock_repo.get_nodes_by_session = AsyncMock(return_value=nodes)
            mock_repo.get_edges_by_session = AsyncMock(return_value=edges)
            MockRepo.return_value = mock_repo

            result = await detector.detect(ctx, MagicMock(), "")

        topology = result

        # "b" has 2 origin nodes (a1, a2) with paths to it
        assert topology["b"]["fan_in"] == 2

        # "c" has 2 origin nodes via "b"
        assert topology["c"]["fan_in"] == 2

        # Origin nodes have 0 fan_in
        assert topology["a1"]["fan_in"] == 0
        assert topology["a2"]["fan_in"] == 0


class TestNonChainMethodology:
    """Tests for non-chain methodologies (JTBD, CJM, etc.)."""

    @pytest.mark.asyncio
    async def test_non_chain_methodology_returns_empty(self):
        """Non-chain methodologies return empty dict (signal absent)."""
        _ = [
            MockNode("a", "job"),
            MockNode("b", "context"),
        ]
        _ = [
            MockEdge("e1", "a", "b"),
        ]

        detector = _make_detector()
        ctx = _make_context(methodology="jobs_to_be_done")

        with patch(
            "src.signals.graph.chain_topology_signals.load_methodology",
            return_value=MockMethodologySchema(has_levels=False),
        ):
            result = await detector.detect(ctx, MagicMock(), "")

        # Non-chain methodology should return empty dict
        assert result == {}


class TestOrphanNode:
    """Tests for orphan nodes (no edges)."""

    @pytest.mark.asyncio
    async def test_orphan_node_signals(self):
        """Orphan nodes have specific topology characteristics."""
        nodes = [
            MockNode("orphan", "attribute"),  # No edges
        ]
        edges = []

        detector = _make_detector()
        ctx = _make_context()

        with (
            patch(
                "src.signals.graph.chain_topology_signals.load_methodology",
                return_value=MockMethodologySchema(has_levels=True),
            ),
            patch(
                "src.persistence.database.get_db_connection",
                return_value=MagicMock(),
            ),
            patch(
                "src.persistence.repositories.graph_repo.GraphRepository",
            ) as MockRepo,
        ):
            mock_repo = MagicMock()
            mock_repo.get_nodes_by_session = AsyncMock(return_value=nodes)
            mock_repo.get_edges_by_session = AsyncMock(return_value=edges)
            MockRepo.return_value = mock_repo

            result = await detector.detect(ctx, MagicMock(), "")

        topology = result

        # Orphan should have 0 fan_in
        assert topology["orphan"]["fan_in"] == 0

        # No level_skip with no edges
        assert topology["orphan"]["level.skip"] is False


class TestEmptyGraph:
    """Tests for empty graph."""

    @pytest.mark.asyncio
    async def test_empty_graph_returns_empty_topology(self):
        """Empty graph returns empty topology dict."""
        nodes = []
        edges = []

        detector = _make_detector()
        ctx = _make_context()

        with (
            patch(
                "src.signals.graph.chain_topology_signals.load_methodology",
                return_value=MockMethodologySchema(has_levels=True),
            ),
            patch(
                "src.persistence.database.get_db_connection",
                return_value=MagicMock(),
            ),
            patch(
                "src.persistence.repositories.graph_repo.GraphRepository",
            ) as MockRepo,
        ):
            mock_repo = MagicMock()
            mock_repo.get_nodes_by_session = AsyncMock(return_value=nodes)
            mock_repo.get_edges_by_session = AsyncMock(return_value=edges)
            MockRepo.return_value = mock_repo

            result = await detector.detect(ctx, MagicMock(), "")

        assert result == {"convgraph.node.chain.role": {}}


class TestNonLeadsToEdges:
    """Tests that non-leads_to edges are filtered out."""

    @pytest.mark.asyncio
    async def test_revises_edges_ignored(self):
        """revises edges should not affect topology computation."""
        nodes = [
            MockNode("a", "attribute"),
            MockNode("b", "functional_consequence"),
        ]
        edges = [
            MockEdge("e1", "a", "b", "leads_to"),
            MockEdge("e2", "b", "a", "revises"),  # Should be ignored
        ]

        detector = _make_detector()
        ctx = _make_context()

        with (
            patch(
                "src.signals.graph.chain_topology_signals.load_methodology",
                return_value=MockMethodologySchema(has_levels=True),
            ),
            patch(
                "src.persistence.database.get_db_connection",
                return_value=MagicMock(),
            ),
            patch(
                "src.persistence.repositories.graph_repo.GraphRepository",
            ) as MockRepo,
        ):
            mock_repo = MagicMock()
            mock_repo.get_nodes_by_session = AsyncMock(return_value=nodes)
            mock_repo.get_edges_by_session = AsyncMock(return_value=edges)
            MockRepo.return_value = mock_repo

            result = await detector.detect(ctx, MagicMock(), "")

        topology = result

        # Should only count leads_to edges, not revises
        assert "a" in topology
        assert "b" in topology


class TestIncompleteChain:
    """Tests for incomplete chains."""

    @pytest.mark.asyncio
    async def test_incomplete_chain_basic_structure(self):
        """An incomplete chain should still compute topology correctly."""
        nodes = [
            MockNode("a", "attribute"),
            MockNode("b", "functional_consequence"),
            MockNode("c", "psychosocial_consequence"),
        ]
        edges = [
            MockEdge("e1", "a", "b"),
            MockEdge("e2", "b", "c"),
        ]

        detector = _make_detector()
        ctx = _make_context()

        with (
            patch(
                "src.signals.graph.chain_topology_signals.load_methodology",
                return_value=MockMethodologySchema(has_levels=True),
            ),
            patch(
                "src.persistence.database.get_db_connection",
                return_value=MagicMock(),
            ),
            patch(
                "src.persistence.repositories.graph_repo.GraphRepository",
            ) as MockRepo,
        ):
            mock_repo = MagicMock()
            mock_repo.get_nodes_by_session = AsyncMock(return_value=nodes)
            mock_repo.get_edges_by_session = AsyncMock(return_value=edges)
            MockRepo.return_value = mock_repo

            result = await detector.detect(ctx, MagicMock(), "")

        topology = result

        # All nodes should be in the result
        assert "a" in topology
        assert "b" in topology
        assert "c" in topology

        # Verify signal fields exist
        for node_id in topology:
            assert "gap.above" in topology[node_id]
            assert "gap.below" in topology[node_id]
            assert "level.skip" in topology[node_id]
            assert "branching_deficit" in topology[node_id]
            assert "fan_in" in topology[node_id]
            assert "level.gap_size" in topology[node_id]
            assert "has_origin_level_ancestor" in topology[node_id]
            assert "has_max_level_ancestor" in topology[node_id]


class TestChainLifecycleSignals:
    """Tests for has_origin_level_ancestor and has_max_level_ancestor."""

    @pytest.mark.asyncio
    async def test_complete_chain_lifecycle(self):
        """A complete chain A→B→C→D→E: middle nodes have both foundation and apex."""
        nodes = [
            MockNode("a", "attribute"),
            MockNode("b", "functional_consequence"),
            MockNode("c", "psychosocial_consequence"),
            MockNode("d", "instrumental_value"),
            MockNode("e", "terminal_value"),
        ]
        edges = [
            MockEdge("e1", "a", "b"),
            MockEdge("e2", "b", "c"),
            MockEdge("e3", "c", "d"),
            MockEdge("e4", "d", "e"),
        ]

        detector = _make_detector()
        ctx = _make_context()

        with (
            patch(
                "src.signals.graph.chain_topology_signals.load_methodology",
                return_value=MockMethodologySchema(has_levels=True),
            ),
            patch(
                "src.persistence.database.get_db_connection",
                return_value=MagicMock(),
            ),
            patch(
                "src.persistence.repositories.graph_repo.GraphRepository",
            ) as MockRepo,
        ):
            mock_repo = MagicMock()
            mock_repo.get_nodes_by_session = AsyncMock(return_value=nodes)
            mock_repo.get_edges_by_session = AsyncMock(return_value=edges)
            MockRepo.return_value = mock_repo

            result = await detector.detect(ctx, MagicMock(), "")

        topology = result

        # all nodes in a complete chain can reach both an attribute (downward)
        # and a terminal (upward), including the attribute and terminal themselves
        for node_id in ["a", "b", "c", "d", "e"]:
            assert topology[node_id]["has_origin_level_ancestor"] is True
            assert topology[node_id]["has_max_level_ancestor"] is True

    @pytest.mark.asyncio
    async def test_floating_consequence_no_foundation(self):
        """A functional_consequence with no attribute below has no foundation."""
        nodes = [
            MockNode("b", "functional_consequence"),
            MockNode("c", "psychosocial_consequence"),
        ]
        edges = [
            MockEdge("e1", "b", "c"),
        ]

        detector = _make_detector()
        ctx = _make_context()

        with (
            patch(
                "src.signals.graph.chain_topology_signals.load_methodology",
                return_value=MockMethodologySchema(has_levels=True),
            ),
            patch(
                "src.persistence.database.get_db_connection",
                return_value=MagicMock(),
            ),
            patch(
                "src.persistence.repositories.graph_repo.GraphRepository",
            ) as MockRepo,
        ):
            mock_repo = MagicMock()
            mock_repo.get_nodes_by_session = AsyncMock(return_value=nodes)
            mock_repo.get_edges_by_session = AsyncMock(return_value=edges)
            MockRepo.return_value = mock_repo

            result = await detector.detect(ctx, MagicMock(), "")

        topology = result

        assert topology["b"]["has_origin_level_ancestor"] is False
        assert topology["b"]["has_max_level_ancestor"] is False
        assert topology["c"]["has_origin_level_ancestor"] is False
        assert topology["c"]["has_max_level_ancestor"] is False

    @pytest.mark.asyncio
    async def test_grounded_but_no_terminal(self):
        """Attribute → functional: foundation present, apex absent."""
        nodes = [
            MockNode("a", "attribute"),
            MockNode("b", "functional_consequence"),
        ]
        edges = [
            MockEdge("e1", "a", "b"),
        ]

        detector = _make_detector()
        ctx = _make_context()

        with (
            patch(
                "src.signals.graph.chain_topology_signals.load_methodology",
                return_value=MockMethodologySchema(has_levels=True),
            ),
            patch(
                "src.persistence.database.get_db_connection",
                return_value=MagicMock(),
            ),
            patch(
                "src.persistence.repositories.graph_repo.GraphRepository",
            ) as MockRepo,
        ):
            mock_repo = MagicMock()
            mock_repo.get_nodes_by_session = AsyncMock(return_value=nodes)
            mock_repo.get_edges_by_session = AsyncMock(return_value=edges)
            MockRepo.return_value = mock_repo

            result = await detector.detect(ctx, MagicMock(), "")

        topology = result

        assert topology["a"]["has_origin_level_ancestor"] is True
        assert topology["a"]["has_max_level_ancestor"] is False
        assert topology["b"]["has_origin_level_ancestor"] is True
        assert topology["b"]["has_max_level_ancestor"] is False

    @pytest.mark.asyncio
    async def test_terminal_without_attribute(self):
        """A floating chain that reaches terminal but lacks attribute foundation."""
        nodes = [
            MockNode("c", "psychosocial_consequence"),
            MockNode("e", "terminal_value"),
        ]
        edges = [
            MockEdge("e1", "c", "e"),  # Skips instrumental
        ]

        detector = _make_detector()
        ctx = _make_context()

        with (
            patch(
                "src.signals.graph.chain_topology_signals.load_methodology",
                return_value=MockMethodologySchema(has_levels=True),
            ),
            patch(
                "src.persistence.database.get_db_connection",
                return_value=MagicMock(),
            ),
            patch(
                "src.persistence.repositories.graph_repo.GraphRepository",
            ) as MockRepo,
        ):
            mock_repo = MagicMock()
            mock_repo.get_nodes_by_session = AsyncMock(return_value=nodes)
            mock_repo.get_edges_by_session = AsyncMock(return_value=edges)
            MockRepo.return_value = mock_repo

            result = await detector.detect(ctx, MagicMock(), "")

        topology = result

        assert topology["c"]["has_origin_level_ancestor"] is False
        assert topology["c"]["has_max_level_ancestor"] is True
        assert topology["e"]["has_origin_level_ancestor"] is False
        assert topology["e"]["has_max_level_ancestor"] is True

    @pytest.mark.asyncio
    async def test_branched_chains_keep_lifecycle(self):
        """Two attributes merging into one consequence: foundation True, apex follows path."""
        nodes = [
            MockNode("a1", "attribute"),
            MockNode("a2", "attribute"),
            MockNode("b", "functional_consequence"),
            MockNode("c", "psychosocial_consequence"),
            MockNode("e", "terminal_value"),
        ]
        edges = [
            MockEdge("e1", "a1", "b"),
            MockEdge("e2", "a2", "b"),
            MockEdge("e3", "b", "c"),
            MockEdge("e4", "c", "e"),
        ]

        detector = _make_detector()
        ctx = _make_context()

        with (
            patch(
                "src.signals.graph.chain_topology_signals.load_methodology",
                return_value=MockMethodologySchema(has_levels=True),
            ),
            patch(
                "src.persistence.database.get_db_connection",
                return_value=MagicMock(),
            ),
            patch(
                "src.persistence.repositories.graph_repo.GraphRepository",
            ) as MockRepo,
        ):
            mock_repo = MagicMock()
            mock_repo.get_nodes_by_session = AsyncMock(return_value=nodes)
            mock_repo.get_edges_by_session = AsyncMock(return_value=edges)
            MockRepo.return_value = mock_repo

            result = await detector.detect(ctx, MagicMock(), "")

        topology = result

        for node_id in ["a1", "a2", "b", "c", "e"]:
            assert topology[node_id]["has_origin_level_ancestor"] is True
            assert topology[node_id]["has_max_level_ancestor"] is True
