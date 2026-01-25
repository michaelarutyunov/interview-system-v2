"""Tests for graph repository."""

import pytest
import tempfile
from pathlib import Path

import aiosqlite
import yaml

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
    async def test_find_node_by_label(self, repo, session_id):
        """find_node_by_label finds by exact label."""
        await repo.create_node(session_id, "Creamy Texture", "attribute")

        # Case-insensitive match
        found = await repo.find_node_by_label(session_id, "creamy texture")

        assert found is not None
        assert found.label == "Creamy Texture"

    @pytest.mark.asyncio
    async def test_find_node_by_label_not_found(self, repo, session_id):
        """find_node_by_label returns None if not found."""
        result = await repo.find_node_by_label(session_id, "nonexistent")
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


class TestConceptElementMatching:
    """Tests for concept element loading and fuzzy matching."""

    @pytest.mark.asyncio
    async def test_match_labels_to_elements_exact_match(self, repo):
        """_match_labels_to_elements matches exact label."""
        elements_data = {
            "element_ids": [1, 2, 3],
            "elements_by_id": {
                1: {"label": "Creamy texture", "aliases": ["silky", "smooth"]},
                2: {"label": "Plant-based", "aliases": ["vegan"]},
                3: {"label": "Sustainability", "aliases": ["eco-friendly"]},
            },
        }

        node_labels = ["Creamy texture", "vegan options"]
        matched = repo._match_labels_to_elements(node_labels, elements_data)

        # Should match element 1 (exact label) and element 2 (alias)
        assert 1 in matched
        assert 2 in matched
        assert 3 not in matched

    @pytest.mark.asyncio
    async def test_match_labels_to_elements_substring_match(self, repo):
        """_match_labels_to_elements matches substrings in aliases."""
        elements_data = {
            "element_ids": [1, 2],
            "elements_by_id": {
                1: {"label": "Creamy texture", "aliases": ["silky", "smooth", "foam"]},
                2: {"label": "Plant-based", "aliases": ["dairy-free", "vegan"]},
            },
        }

        node_labels = ["I love the silky foam", "It's dairy-free"]
        matched = repo._match_labels_to_elements(node_labels, elements_data)

        # "silky foam" should match element 1 (contains "silky" and "foam")
        # "dairy-free" should match element 2 (contains "dairy-free")
        assert 1 in matched
        assert 2 in matched

    @pytest.mark.asyncio
    async def test_match_labels_to_elements_case_insensitive(self, repo):
        """_match_labels_to_elements is case-insensitive."""
        elements_data = {
            "element_ids": [1],
            "elements_by_id": {
                1: {"label": "Creamy Texture", "aliases": ["Silky", "SMOOTH"]},
            },
        }

        node_labels = ["creamy texture", "SILKY foam"]
        matched = repo._match_labels_to_elements(node_labels, elements_data)

        assert 1 in matched

    @pytest.mark.asyncio
    async def test_match_labels_to_elements_no_match(self, repo):
        """_match_labels_to_elements returns empty list when no matches."""
        elements_data = {
            "element_ids": [1, 2],
            "elements_by_id": {
                1: {"label": "Creamy texture", "aliases": ["silky", "smooth"]},
                2: {"label": "Plant-based", "aliases": ["vegan"]},
            },
        }

        node_labels = ["bitter taste", "expensive price"]
        matched = repo._match_labels_to_elements(node_labels, elements_data)

        assert len(matched) == 0

    @pytest.mark.asyncio
    async def test_match_labels_to_elements_word_boundaries(self, repo):
        """_match_labels_to_elements handles word boundaries correctly."""
        elements_data = {
            "element_ids": [1, 2],
            "elements_by_id": {
                1: {"label": "Foam", "aliases": ["foam"]},
                2: {"label": "Milk", "aliases": ["milk"]},
            },
        }

        # "foam" should match element 1
        # "soy milk" should match element 2 (contains "milk")
        node_labels = ["love the foam", "soy milk alternative"]
        matched = repo._match_labels_to_elements(node_labels, elements_data)

        assert 1 in matched
        assert 2 in matched

    @pytest.mark.asyncio
    async def test_match_labels_to_elements_empty_aliases(self, repo):
        """_match_labels_to_elements works with empty alias list."""
        elements_data = {
            "element_ids": [1],
            "elements_by_id": {
                1: {"label": "Creamy texture", "aliases": []},
            },
        }

        node_labels = ["The creamy texture is great"]
        matched = repo._match_labels_to_elements(node_labels, elements_data)

        # Should still match via label
        assert 1 in matched


class TestStringElementIDs:
    """Tests for string element IDs (legacy format)."""

    @pytest.fixture
    async def session_with_string_ids(self, db_connection, tmp_path):
        """Create a test session with string element IDs."""
        session_id = "test-session-string-ids"
        concept_id = "test_concept_strings"

        await db_connection.execute(
            """
            INSERT INTO sessions (id, methodology, concept_id, concept_name, status, config)
            VALUES (?, 'means_end_chain', ?, 'Test String IDs', 'active', '{}')
            """,
            (session_id, concept_id),
        )
        await db_connection.commit()

        config_dir = tmp_path / "config" / "concepts"
        config_dir.mkdir(parents=True, exist_ok=True)
        concept_path = config_dir / f"{concept_id}.yaml"

        concept_data = {
            "id": concept_id,
            "name": "Test String IDs",
            "methodology": "means_end_chain",
            "elements": [
                {
                    "id": "creamy_texture",
                    "label": "Creamy texture",
                    "aliases": ["silky", "smooth", "foam"],
                },
                {
                    "id": "plant_based",
                    "label": "Plant-based",
                    "aliases": ["vegan", "dairy-free"],
                },
            ],
        }

        with open(concept_path, "w") as f:
            yaml.dump(concept_data, f)

        return session_id

    @pytest.mark.asyncio
    async def test_match_labels_to_elements_string_ids(self, repo):
        """_match_labels_to_elements preserves string element IDs."""
        elements_data = {
            "element_ids": ["creamy_texture", "plant_based"],
            "elements_by_id": {
                "creamy_texture": {
                    "label": "Creamy texture",
                    "aliases": ["silky", "foam"],
                },
                "plant_based": {"label": "Plant-based", "aliases": ["vegan"]},
            },
        }

        node_labels = ["silky foam", "vegan options"]
        matched = repo._match_labels_to_elements(node_labels, elements_data)

        # Should return string IDs
        assert "creamy_texture" in matched
        assert "plant_based" in matched

    @pytest.mark.asyncio
    async def test_coverage_state_with_oat_milk_concept(self, repo, db_connection):
        """get_graph_state works with actual oat_milk_v2 concept."""
        session_id = "test-session-oatmilk"

        # Use the actual oat_milk_v2 concept
        await db_connection.execute(
            """
            INSERT INTO sessions (id, methodology, concept_id, concept_name, status, config)
            VALUES (?, 'means_end_chain', ?, 'Oat Milk v2', 'active', '{}')
            """,
            (session_id, "oat_milk_v2"),
        )
        await db_connection.commit()

        # Create nodes that should match to elements via fuzzy matching
        await repo.create_node(session_id, "I love the silky foam", "attribute")
        await repo.create_node(session_id, "It's dairy-free and vegan", "attribute")
        await repo.create_node(session_id, "Good for the planet", "attribute")

        state = await repo.get_graph_state(session_id)
        coverage_state = state.coverage_state

        # Check that coverage state was built
        assert coverage_state is not None
        assert coverage_state.elements_total == 6

        # Check that elements are properly matched
        # Element 1 (Creamy texture) should be matched via "silky" or "foam"
        # Element 2 (Plant-based / dairy-free) should be matched via "dairy-free" or "vegan"
        # Element 3 (Environmentally sustainable) should be matched via "planet"
        assert coverage_state.elements[1].covered is True
        assert coverage_state.elements[2].covered is True
        assert coverage_state.elements[3].covered is True

        # Check coverage count
        assert coverage_state.elements_covered >= 3  # At least 3 elements covered

    @pytest.mark.asyncio
    async def test_coverage_state_partial_with_oat_milk(self, repo, db_connection):
        """get_graph_state correctly tracks partial coverage with oat_milk."""
        session_id = "test-session-oatmilk-partial"

        await db_connection.execute(
            """
            INSERT INTO sessions (id, methodology, concept_id, concept_name, status, config)
            VALUES (?, 'means_end_chain', ?, 'Oat Milk v2', 'active', '{}')
            """,
            (session_id, "oat_milk_v2"),
        )
        await db_connection.commit()

        # Create node that only matches element 1
        await repo.create_node(session_id, "Very silky texture", "attribute")

        state = await repo.get_graph_state(session_id)
        coverage_state = state.coverage_state

        # Check that coverage state was built
        assert coverage_state is not None
        assert coverage_state.elements_total == 6

        # Only element 1 should be matched (contains "silky")
        assert coverage_state.elements[1].covered is True
        assert coverage_state.elements[2].covered is False
        assert coverage_state.elements[3].covered is False
        assert coverage_state.elements[4].covered is False
        assert coverage_state.elements[5].covered is False
        assert coverage_state.elements[6].covered is False

        # Only 1 element covered
        assert coverage_state.elements_covered == 1
