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

    schema = MethodologySchema(**data)
    _cache[name] = schema
    log.info("schema_loaded", methodology=name, node_types=len(schema.node_types))
    return schema
