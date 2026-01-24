"""Tests for methodology schema loading and validation."""

import pytest
import tempfile
from pathlib import Path
import yaml

from src.domain.models.methodology_schema import (
    NodeTypeSpec,
    EdgeTypeSpec,
    MethodologySchema,
)
from src.core.schema_loader import load_methodology, _cache


@pytest.fixture
def sample_schema_data():
    """Sample schema data for testing."""
    return {
        "name": "test_methodology",
        "version": "1.0",
        "description": "Test methodology",
        "node_types": [
            {
                "name": "concept_a",
                "description": "First concept type",
                "examples": ["example1", "example2"],
            },
            {
                "name": "concept_b",
                "description": "Second concept type",
                "examples": ["example3"],
            },
        ],
        "edge_types": [
            {"name": "connects_to", "description": "Connection relationship"},
            {"name": "replaces", "description": "Replacement relationship"},
        ],
        "valid_connections": {
            "connects_to": [["concept_a", "concept_b"], ["concept_b", "concept_b"]],
            "replaces": [["*", "*"]],
        },
    }


@pytest.fixture
def temp_schema_dir(sample_schema_data):
    """Create a temporary directory with a test schema file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        schema_path = Path(tmpdir) / "test_methodology.yaml"
        with open(schema_path, "w") as f:
            yaml.dump(sample_schema_data, f)
        yield Path(tmpdir)


def test_node_type_spec_creation():
    """NodeTypeSpec can be created with valid data."""
    node_type = NodeTypeSpec(
        name="attribute", description="A product feature", examples=["texture", "color"]
    )
    assert node_type.name == "attribute"
    assert node_type.description == "A product feature"
    assert len(node_type.examples) == 2


def test_edge_type_spec_creation():
    """EdgeTypeSpec can be created with valid data."""
    edge_type = EdgeTypeSpec(name="leads_to", description="Causal relationship")
    assert edge_type.name == "leads_to"
    assert edge_type.description == "Causal relationship"


def test_methodology_schema_creation(sample_schema_data):
    """MethodologySchema can be created from dict data."""
    schema = MethodologySchema(**sample_schema_data)

    assert schema.name == "test_methodology"
    assert schema.version == "1.0"
    assert len(schema.node_types) == 2
    assert len(schema.edge_types) == 2


def test_schema_post_init_builds_lookup_sets(sample_schema_data):
    """Schema post_init builds internal lookup sets."""
    schema = MethodologySchema(**sample_schema_data)

    assert "concept_a" in schema._node_names
    assert "concept_b" in schema._node_names
    assert "connects_to" in schema._edge_names
    assert "replaces" in schema._edge_names


def test_is_valid_node_type(sample_schema_data):
    """is_valid_node_type correctly validates node types."""
    schema = MethodologySchema(**sample_schema_data)

    assert schema.is_valid_node_type("concept_a") is True
    assert schema.is_valid_node_type("concept_b") is True
    assert schema.is_valid_node_type("invalid_type") is False
    assert schema.is_valid_node_type("") is False


def test_is_valid_edge_type(sample_schema_data):
    """is_valid_edge_type correctly validates edge types."""
    schema = MethodologySchema(**sample_schema_data)

    assert schema.is_valid_edge_type("connects_to") is True
    assert schema.is_valid_edge_type("replaces") is True
    assert schema.is_valid_edge_type("invalid_edge") is False
    assert schema.is_valid_edge_type("") is False


def test_is_valid_connection_exact_match(sample_schema_data):
    """is_valid_connection validates exact connections."""
    schema = MethodologySchema(**sample_schema_data)

    # Valid connections from schema
    assert schema.is_valid_connection("connects_to", "concept_a", "concept_b") is True
    assert schema.is_valid_connection("connects_to", "concept_b", "concept_b") is True

    # Invalid connections (not in schema)
    assert schema.is_valid_connection("connects_to", "concept_a", "concept_a") is False
    assert schema.is_valid_connection("connects_to", "concept_b", "concept_a") is False


def test_is_valid_connection_wildcard_match(sample_schema_data):
    """is_valid_connection handles wildcard connections."""
    schema = MethodologySchema(**sample_schema_data)

    # Wildcard should match any combination
    assert schema.is_valid_connection("replaces", "concept_a", "concept_a") is True
    assert schema.is_valid_connection("replaces", "concept_a", "concept_b") is True
    assert schema.is_valid_connection("replaces", "concept_b", "concept_a") is True
    assert schema.is_valid_connection("replaces", "concept_b", "concept_b") is True


def test_is_valid_connection_nonexistent_edge(sample_schema_data):
    """is_valid_connection returns False for nonexistent edge types."""
    schema = MethodologySchema(**sample_schema_data)

    assert schema.is_valid_connection("nonexistent", "concept_a", "concept_b") is False


def test_get_node_descriptions(sample_schema_data):
    """get_node_descriptions returns formatted descriptions with examples."""
    schema = MethodologySchema(**sample_schema_data)

    descriptions = schema.get_node_descriptions()

    assert "concept_a" in descriptions
    assert "concept_b" in descriptions
    assert "First concept type" in descriptions["concept_a"]
    assert "'example1'" in descriptions["concept_a"]
    assert "'example2'" in descriptions["concept_a"]
    assert "Second concept type" in descriptions["concept_b"]
    assert "'example3'" in descriptions["concept_b"]


def test_get_node_descriptions_limits_examples():
    """get_node_descriptions limits to first 3 examples."""
    schema_data = {
        "name": "test",
        "version": "1.0",
        "description": "Test",
        "node_types": [
            {
                "name": "many_examples",
                "description": "Node with many examples",
                "examples": ["ex1", "ex2", "ex3", "ex4", "ex5"],
            }
        ],
        "edge_types": [],
        "valid_connections": {},
    }
    schema = MethodologySchema(**schema_data)
    descriptions = schema.get_node_descriptions()

    # Should only include first 3 examples
    assert "'ex1'" in descriptions["many_examples"]
    assert "'ex2'" in descriptions["many_examples"]
    assert "'ex3'" in descriptions["many_examples"]
    assert "'ex4'" not in descriptions["many_examples"]
    assert "'ex5'" not in descriptions["many_examples"]


def test_get_edge_descriptions(sample_schema_data):
    """get_edge_descriptions returns edge type descriptions."""
    schema = MethodologySchema(**sample_schema_data)

    descriptions = schema.get_edge_descriptions()

    assert descriptions["connects_to"] == "Connection relationship"
    assert descriptions["replaces"] == "Replacement relationship"


def test_load_methodology_from_file(temp_schema_dir):
    """load_methodology loads schema from YAML file."""
    # Clear cache before test
    _cache.clear()

    schema = load_methodology("test_methodology", schema_dir=temp_schema_dir)

    assert schema.name == "test_methodology"
    assert schema.version == "1.0"
    assert len(schema.node_types) == 2
    assert len(schema.edge_types) == 2


def test_load_methodology_caching(temp_schema_dir):
    """load_methodology caches schemas after first load."""
    # Clear cache before test
    _cache.clear()

    # First load
    schema1 = load_methodology("test_methodology", schema_dir=temp_schema_dir)

    # Second load should return same instance from cache
    schema2 = load_methodology("test_methodology", schema_dir=temp_schema_dir)

    assert schema1 is schema2


def test_load_methodology_file_not_found():
    """load_methodology raises FileNotFoundError for missing schema."""
    # Clear cache before test
    _cache.clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(FileNotFoundError) as exc_info:
            load_methodology("nonexistent", schema_dir=Path(tmpdir))

        assert "nonexistent.yaml" in str(exc_info.value)


def test_load_means_end_chain_schema():
    """Load the actual means_end_chain.yaml schema."""
    # Clear cache before test
    _cache.clear()

    schema = load_methodology("means_end_chain")

    # Verify basic structure
    assert schema.name == "means_end_chain"
    assert schema.version == "2.0"
    assert "Laddering" in schema.description

    # Verify all 5 node types exist
    node_names = {nt.name for nt in schema.node_types}
    assert node_names == {
        "attribute",
        "functional_consequence",
        "psychosocial_consequence",
        "instrumental_value",
        "terminal_value",
    }

    # Verify edge types
    edge_names = {et.name for et in schema.edge_types}
    assert edge_names == {"leads_to", "revises"}

    # Verify some specific connections
    assert (
        schema.is_valid_connection("leads_to", "attribute", "functional_consequence")
        is True
    )
    assert (
        schema.is_valid_connection("leads_to", "instrumental_value", "terminal_value")
        is True
    )

    # Verify invalid skip-level connection is rejected
    assert (
        schema.is_valid_connection("leads_to", "attribute", "terminal_value") is False
    )

    # Verify wildcard revises connection
    assert schema.is_valid_connection("revises", "attribute", "terminal_value") is True
    assert schema.is_valid_connection("revises", "terminal_value", "attribute") is True


def test_means_end_chain_node_descriptions():
    """Verify means_end_chain node descriptions are properly formatted."""
    # Clear cache before test
    _cache.clear()

    schema = load_methodology("means_end_chain")
    descriptions = schema.get_node_descriptions()

    # Verify all node types have descriptions
    assert len(descriptions) == 5

    # Check that examples are included
    assert "attribute" in descriptions
    assert (
        "creamy texture" in descriptions["attribute"]
        or "plant-based" in descriptions["attribute"]
    )

    # Verify description format includes both description and examples
    assert "Concrete product feature" in descriptions["attribute"]


def test_means_end_chain_valid_connections():
    """Verify means_end_chain connection rules are correct."""
    # Clear cache before test
    _cache.clear()

    schema = load_methodology("means_end_chain")

    # Test same-level connections
    assert schema.is_valid_connection("leads_to", "attribute", "attribute") is True
    assert (
        schema.is_valid_connection(
            "leads_to", "functional_consequence", "functional_consequence"
        )
        is True
    )

    # Test adjacent upward connections
    assert (
        schema.is_valid_connection("leads_to", "attribute", "functional_consequence")
        is True
    )
    assert (
        schema.is_valid_connection(
            "leads_to", "functional_consequence", "psychosocial_consequence"
        )
        is True
    )
    assert (
        schema.is_valid_connection(
            "leads_to", "psychosocial_consequence", "instrumental_value"
        )
        is True
    )
    assert (
        schema.is_valid_connection("leads_to", "instrumental_value", "terminal_value")
        is True
    )

    # Test invalid skip-level connections
    assert (
        schema.is_valid_connection("leads_to", "attribute", "psychosocial_consequence")
        is False
    )
    assert (
        schema.is_valid_connection("leads_to", "attribute", "instrumental_value")
        is False
    )
    assert (
        schema.is_valid_connection("leads_to", "attribute", "terminal_value") is False
    )
    assert (
        schema.is_valid_connection(
            "leads_to", "functional_consequence", "instrumental_value"
        )
        is False
    )

    # Test downward connections are not allowed for leads_to
    assert (
        schema.is_valid_connection("leads_to", "terminal_value", "instrumental_value")
        is False
    )
    assert (
        schema.is_valid_connection(
            "leads_to", "instrumental_value", "psychosocial_consequence"
        )
        is False
    )
