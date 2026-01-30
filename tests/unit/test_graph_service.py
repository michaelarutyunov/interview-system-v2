"""Tests for graph service."""

import pytest
from unittest.mock import AsyncMock

from src.services.graph_service import GraphService
from src.domain.models.extraction import (
    ExtractedConcept,
    ExtractedRelationship,
    ExtractionResult,
)
from src.domain.models.knowledge_graph import (
    KGNode,
    KGEdge,
    GraphState,
    DepthMetrics,
)


@pytest.fixture
def mock_repo():
    """Create mock graph repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def service(mock_repo):
    """Create graph service with mock repo."""
    return GraphService(mock_repo)


@pytest.fixture
def sample_extraction():
    """Create sample extraction result."""
    return ExtractionResult(
        concepts=[
            ExtractedConcept(
                text="creamy texture",
                node_type="attribute",
                confidence=0.9,
                source_utterance_id="u1",
            ),
            ExtractedConcept(
                text="satisfying",
                node_type="functional_consequence",
                confidence=0.8,
                source_utterance_id="u1",
            ),
        ],
        relationships=[
            ExtractedRelationship(
                source_text="creamy texture",
                target_text="satisfying",
                relationship_type="leads_to",
                confidence=0.75,
                source_utterance_id="u1",
            ),
        ],
        is_extractable=True,
    )


class TestAddExtractionToGraph:
    """Tests for add_extraction_to_graph."""

    @pytest.mark.asyncio
    async def test_adds_nodes_and_edges(self, service, mock_repo, sample_extraction):
        """Adds nodes and edges from extraction."""
        # Setup: repo returns created nodes
        mock_repo.find_node_by_label.return_value = None  # No duplicates
        mock_repo.find_edge.return_value = None  # No duplicate edges

        node1 = KGNode(
            id="n1",
            session_id="s1",
            label="creamy texture",
            node_type="attribute",
            source_utterance_ids=["u1"],
        )
        node2 = KGNode(
            id="n2",
            session_id="s1",
            label="satisfying",
            node_type="functional_consequence",
            source_utterance_ids=["u1"],
        )
        edge = KGEdge(
            id="e1",
            session_id="s1",
            source_node_id="n1",
            target_node_id="n2",
            edge_type="leads_to",
            source_utterance_ids=["u1"],
        )

        mock_repo.create_node.side_effect = [node1, node2]
        mock_repo.create_edge.return_value = edge

        nodes, edges = await service.add_extraction_to_graph(
            session_id="s1",
            extraction=sample_extraction,
            utterance_id="u1",
        )

        assert len(nodes) == 2
        assert len(edges) == 1
        assert mock_repo.create_node.call_count == 2
        assert mock_repo.create_edge.call_count == 1

    @pytest.mark.asyncio
    async def test_deduplicates_nodes(self, service, mock_repo, sample_extraction):
        """Deduplicates nodes by label."""
        # Setup: first concept already exists
        existing_node = KGNode(
            id="existing",
            session_id="s1",
            label="creamy texture",
            node_type="attribute",
            source_utterance_ids=["old-u"],
        )
        mock_repo.find_node_by_label.side_effect = [
            existing_node,  # First concept exists
            None,  # Second concept doesn't exist
        ]
        mock_repo.add_source_utterance.return_value = existing_node
        mock_repo.create_node.return_value = KGNode(
            id="new",
            session_id="s1",
            label="satisfying",
            node_type="functional_consequence",
            source_utterance_ids=["u1"],
        )
        mock_repo.find_edge.return_value = None
        mock_repo.create_edge.return_value = KGEdge(
            id="e1",
            session_id="s1",
            source_node_id="existing",
            target_node_id="new",
            edge_type="leads_to",
            source_utterance_ids=["u1"],
        )

        nodes, edges = await service.add_extraction_to_graph(
            session_id="s1",
            extraction=sample_extraction,
            utterance_id="u1",
        )

        # Should have called add_source_utterance for existing node
        mock_repo.add_source_utterance.assert_called_once()
        # Should only create one new node
        assert mock_repo.create_node.call_count == 1

    @pytest.mark.asyncio
    async def test_skips_non_extractable(self, service, mock_repo):
        """Skips non-extractable results."""
        extraction = ExtractionResult(is_extractable=False)

        nodes, edges = await service.add_extraction_to_graph(
            session_id="s1",
            extraction=extraction,
            utterance_id="u1",
        )

        assert nodes == []
        assert edges == []
        mock_repo.create_node.assert_not_called()


class TestGetSessionGraph:
    """Tests for get_session_graph."""

    @pytest.mark.asyncio
    async def test_returns_nodes_and_edges(self, service, mock_repo):
        """Returns all nodes and edges for session."""
        mock_repo.get_nodes_by_session.return_value = [
            KGNode(id="n1", session_id="s1", label="a", node_type="attribute")
        ]
        mock_repo.get_edges_by_session.return_value = []

        nodes, edges = await service.get_session_graph("s1")

        assert len(nodes) == 1
        mock_repo.get_nodes_by_session.assert_called_with("s1")


class TestGetGraphState:
    """Tests for get_graph_state."""

    @pytest.mark.asyncio
    async def test_delegates_to_repo(self, service, mock_repo):
        """Delegates to repository."""
        expected = GraphState(
            node_count=5,
            edge_count=3,
            depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.5, depth_by_element={}),
        )
        mock_repo.get_graph_state.return_value = expected

        result = await service.get_graph_state("s1")

        assert result == expected
        mock_repo.get_graph_state.assert_called_with("s1")


class TestHandleContradiction:
    """Tests for handle_contradiction."""

    @pytest.mark.asyncio
    async def test_creates_revises_edge(self, service, mock_repo):
        """Creates REVISES edge for contradiction."""
        new_node = KGNode(
            id="new",
            session_id="s1",
            label="new belief",
            node_type="attribute",
            source_utterance_ids=["u1"],
        )
        edge = KGEdge(
            id="e1",
            session_id="s1",
            source_node_id="new",
            target_node_id="old",
            edge_type="revises",
            source_utterance_ids=["u1"],
        )

        mock_repo.create_node.return_value = new_node
        mock_repo.supersede_node.return_value = None
        mock_repo.create_edge.return_value = edge

        result_node, result_edge = await service.handle_contradiction(
            session_id="s1",
            old_node_id="old",
            new_concept=ExtractedConcept(
                text="new belief", node_type="attribute", source_utterance_id="u1"
            ),
            utterance_id="u1",
        )

        assert result_node.id == "new"
        assert result_edge.edge_type == "revises"
        mock_repo.supersede_node.assert_called_with("old", "new")
