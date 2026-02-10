"""Schema loader for methodology YAML configuration files.

Loads methodology schemas that define signals, strategies, and node/edge types
for interview questioning approaches. Schemas are cached after first load.
"""

import yaml
from pathlib import Path
from typing import Optional, Dict
import structlog

from src.domain.models.methodology_schema import MethodologySchema

log = structlog.get_logger()

# Module-level cache (singleton pattern - schema doesn't change at runtime)
_cache: Dict[str, MethodologySchema] = {}


def load_methodology(name: str, schema_dir: Optional[Path] = None) -> MethodologySchema:
    """Load methodology schema from YAML configuration file.

    Reads methodology definition from config/methodologies/{name}.yaml which
    defines signals, strategies, node types, and edge types for the questioning
    approach. Results are cached after first load for performance.

    Args:
        name: Methodology identifier (e.g., 'means_end_chain', 'laddering')
        schema_dir: Override config/methodologies/ path (for testing)

    Returns:
        Loaded and validated MethodologySchema with signals and strategy definitions

    Raises:
        FileNotFoundError: Methodology YAML file not found
        ValueError: Invalid YAML structure or missing required fields
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

    # YAML files now use the new method + ontology format directly
    schema = MethodologySchema(**data)
    _cache[name] = schema

    node_count = len(schema.ontology.nodes) if schema.ontology else 0
    log.info("schema_loaded", methodology=name, node_count=node_count)
    return schema
