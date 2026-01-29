"""Schema loader for methodology YAML files."""

import yaml
from pathlib import Path
from typing import Optional, Dict
import structlog

from src.domain.models.methodology_schema import MethodologySchema

log = structlog.get_logger()

# Module-level cache (singleton pattern - schema doesn't change at runtime)
_cache: Dict[str, MethodologySchema] = {}


def load_methodology(name: str, schema_dir: Optional[Path] = None) -> MethodologySchema:
    """Load methodology schema from YAML. Cached after first load.

    Args:
        name: Methodology name, e.g. "means_end_chain"
        schema_dir: Override config/methodologies/ path (mainly for testing)

    Returns:
        Loaded and validated MethodologySchema instance

    Raises:
        FileNotFoundError: Schema file missing
        ValueError: Invalid YAML structure or validation error
    """
    if name in _cache:
        return _cache[name]

    if schema_dir is None:
        schema_dir = Path(__file__).parent.parent.parent / "config" / "methodologies"

    path = schema_dir / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Methodology schema not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    # Transform new unified structure to legacy format for backward compatibility
    transformed_data = _transform_unified_schema(data)

    schema = MethodologySchema(**transformed_data)
    _cache[name] = schema
    log.info("schema_loaded", methodology=name, node_types=len(schema.node_types))
    return schema


def _transform_unified_schema(data: dict) -> dict:
    """Transform new unified schema format to legacy format.

    New format:
        method:
          name: ...
          version: ...
          description: ...
        ontology:
          nodes: [...]
          edges: [...]
          extraction_guidelines: ...
          relationship_examples: ...
          extractability_criteria: ...
        signals: {...}
        strategies: [...]
        phases: {...}

    Legacy format:
        name: ...
        version: ...
        description: ...
        node_types: [...]
        edge_types: [...]
        valid_connections: {...}
        extraction_guidelines: ...
        relationship_examples: ...
        extractability_criteria: ...

    Args:
        data: Raw YAML data in new format

    Returns:
        Transformed data in legacy format
    """
    # Check if already in legacy format
    if "method" not in data:
        return data

    # Extract method metadata
    method = data.get("method", {})
    ontology = data.get("ontology", {})

    # Build legacy format
    legacy = {
        "name": method.get("name", ""),
        "version": method.get("version", "1.0"),
        "description": method.get("description", ""),
    }

    # Transform nodes to node_types
    nodes = ontology.get("nodes", [])
    legacy["node_types"] = [
        {
            "name": node.get("name"),
            "description": node.get("description"),
            "examples": node.get("examples", []),
            "level": node.get("level"),
            "terminal": node.get("terminal"),
        }
        for node in nodes
    ]

    # Transform edges to edge_types and valid_connections
    edges = ontology.get("edges", [])
    legacy["edge_types"] = [
        {
            "name": edge.get("name"),
            "description": edge.get("description"),
        }
        for edge in edges
    ]

    # Build valid_connections from permitted_connections
    valid_connections = {}
    for edge in edges:
        edge_name = edge.get("name")
        permitted = edge.get("permitted_connections", [])
        if permitted:
            valid_connections[edge_name] = permitted
    legacy["valid_connections"] = valid_connections

    # Copy optional extraction sections
    optional_fields = [
        "extraction_guidelines",
        "relationship_examples",
        "extractability_criteria",
    ]
    for field in optional_fields:
        if field in ontology:
            legacy[field] = ontology[field]

    # Note: signals, strategies, phases are not used by MethodologySchema
    # but are kept for other parts of the system that may load the YAML directly

    return legacy
