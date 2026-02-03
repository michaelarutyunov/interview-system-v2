"""Tests for graph repository."""

import pytest
import tempfile
from pathlib import Path

import aiosqlite

from src.persistence.database import init_database
from src.persistence.repositories.graph_repo import GraphRepository


@pytest.fixture
async def db_connection():
    """Create test database with schema."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        await init_database(db_path)

        async with aiosqlite.connect(db_path) as db:
            yield db


@pytest.fixture
async def repo(db_connection):
    """Create graph repository with test database."""
    return GraphRepository(db_connection)


@pytest.fixture
async def session_id(db_connection):
    """Create a test session and return its ID."""
    session_id = "test-session-1"
    await db_connection.execute(
        """
        INSERT INTO sessions (id, methodology, concept_id, concept_name, status, config)
        VALUES (?, 'means_end_chain', 'test-concept', 'Test', 'active', '{}')
        """,
        (session_id,),
    )
    await db_connection.commit()
    return session_id


class TestNodeOperations:
    """Tests for node CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_node(self, repo, session_id):
        """create_node creates and returns a node."""
        node = await repo.create_node(
            session_id=session_id,
            label="creamy texture",
            node_type="attribute",
            confidence=0.9,
        )

        assert node.id is not None
        assert node.label == "creamy texture"
        assert node.node_type == "attribute"
        assert node.confidence == 0.9

    @pytest.mark.asyncio
    async def test_get_node(self, repo, session_id):
        """get_node retrieves a node by ID."""
        created = await repo.create_node(
            session_id=session_id,
            label="test",
            node_type="attribute",
        )

        retrieved = await repo.get_node(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.label == "test"

    @pytest.mark.asyncio
    async def test_get_node_not_found(self, repo):
        """get_node returns None for unknown ID."""
        result = await repo.get_node("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_nodes_by_session(self, repo, session_id):
        """get_nodes_by_session returns all session nodes."""
        await repo.create_node(session_id, "node1", "attribute")
        await repo.create_node(session_id, "node2", "functional_consequence")

        nodes = await repo.get_nodes_by_session(session_id)

        assert len(nodes) == 2

    @pytest.mark.asyncio
    async def test_find_node_by_label_and_type(self, repo, session_id):
        """find_node_by_label_and_type finds by exact label and type."""
        await repo.create_node(session_id, "Creamy Texture", "attribute")

        # Case-insensitive match with type
        found = await repo.find_node_by_label_and_type(
            session_id, "creamy texture", "attribute"
        )

        assert found is not None
        assert found.label == "Creamy Texture"

    @pytest.mark.asyncio
    async def test_find_node_by_label_and_type_not_found(self, repo, session_id):
        """find_node_by_label_and_type returns None if not found."""
        result = await repo.find_node_by_label_and_type(
            session_id, "nonexistent", "attribute"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_supersede_node(self, repo, session_id):
        """supersede_node marks node as superseded."""
        old = await repo.create_node(session_id, "old belief", "attribute")
        new = await repo.create_node(session_id, "new belief", "attribute")

        updated = await repo.supersede_node(old.id, new.id)

        assert updated.superseded_by == new.id


class TestEdgeOperations:
    """Tests for edge CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_edge(self, repo, session_id):
        """create_edge creates and returns an edge."""
        node1 = await repo.create_node(session_id, "source", "attribute")
        node2 = await repo.create_node(session_id, "target", "functional_consequence")

        edge = await repo.create_edge(
            session_id=session_id,
            source_node_id=node1.id,
            target_node_id=node2.id,
            edge_type="leads_to",
            confidence=0.85,
        )

        assert edge.id is not None
        assert edge.source_node_id == node1.id
        assert edge.target_node_id == node2.id
        assert edge.edge_type == "leads_to"

    @pytest.mark.asyncio
    async def test_find_edge(self, repo, session_id):
        """find_edge finds by source, target, type."""
        node1 = await repo.create_node(session_id, "a", "attribute")
        node2 = await repo.create_node(session_id, "b", "functional_consequence")
        await repo.create_edge(session_id, node1.id, node2.id, "leads_to")

        found = await repo.find_edge(session_id, node1.id, node2.id, "leads_to")

        assert found is not None
        assert found.source_node_id == node1.id

    @pytest.mark.asyncio
    async def test_get_edges_by_session(self, repo, session_id):
        """get_edges_by_session returns all session edges."""
        n1 = await repo.create_node(session_id, "a", "attribute")
        n2 = await repo.create_node(session_id, "b", "functional_consequence")
        n3 = await repo.create_node(session_id, "c", "psychosocial_consequence")

        await repo.create_edge(session_id, n1.id, n2.id, "leads_to")
        await repo.create_edge(session_id, n2.id, n3.id, "leads_to")

        edges = await repo.get_edges_by_session(session_id)

        assert len(edges) == 2


class TestGraphState:
    """Tests for graph state aggregation."""

    @pytest.mark.asyncio
    async def test_get_graph_state_empty(self, repo, session_id):
        """get_graph_state returns zeros for empty graph."""
        state = await repo.get_graph_state(session_id)

        assert state.node_count == 0
        assert state.edge_count == 0

    @pytest.mark.asyncio
    async def test_get_graph_state_with_data(self, repo, session_id):
        """get_graph_state returns correct counts."""
        n1 = await repo.create_node(session_id, "a", "attribute")
        n2 = await repo.create_node(session_id, "b", "functional_consequence")
        await repo.create_edge(session_id, n1.id, n2.id, "leads_to")

        state = await repo.get_graph_state(session_id)

        assert state.node_count == 2
        assert state.edge_count == 1
        assert state.nodes_by_type["attribute"] == 1
        assert state.edges_by_type["leads_to"] == 1

    @pytest.mark.asyncio
    async def test_get_graph_state_orphans(self, repo, session_id):
        """get_graph_state counts orphan nodes."""
        await repo.create_node(session_id, "orphan", "attribute")  # No edges

        state = await repo.get_graph_state(session_id)

        assert state.orphan_count == 1
