"""Concept loader for concept YAML files.

Loads concept definitions from YAML configuration files. Each concept defines
an interview topic with methodology, objective, and optional elements for targeting.
Concepts are cached after first load for performance.
"""

import yaml
from pathlib import Path
from typing import Optional, Dict
import structlog

from src.domain.models.concept import Concept, ConceptElement, ConceptContext

log = structlog.get_logger(__name__)

# Module-level cache (singleton pattern - concept doesn't change at runtime)
_cache: Dict[str, Concept] = {}


def load_concept(name: str, concepts_dir: Optional[Path] = None) -> Concept:
    """Load concept configuration from YAML file.

    Reads concept definition from config/concepts/{name}.yaml, validates the
    structure, and returns a Concept instance. Results are cached after first load
    for performance, so subsequent calls with the same name return instantly.

    Args:
        name: Concept identifier (e.g., 'oat_milk_v2', 'smartphone_v3')
        concepts_dir: Override config/concepts/ path (for testing)

    Returns:
        Loaded and validated Concept instance with methodology, objective, and elements

    Raises:
        FileNotFoundError: Concept YAML file not found
        ValueError: Invalid YAML structure or missing required fields
    """
    if name in _cache:
        return _cache[name]

    if concepts_dir is None:
        concepts_dir = Path(__file__).parent.parent.parent / "config" / "concepts"

    path = concepts_dir / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Concept not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    # Parse context (objective is at root level or nested in context)
    context_data = data.get("context", {})
    objective = data.get("objective") or context_data.get("objective")

    context = ConceptContext(objective=objective)

    # Parse elements
    elements_data = data.get("elements", [])
    elements = [
        ConceptElement(
            id=e["id"],
            label=e["label"],
            aliases=e.get("aliases", []),
        )
        for e in elements_data
    ]

    concept = Concept(
        id=data["id"],
        name=data["name"],
        methodology=data["methodology"],
        context=context,
        elements=elements,
    )
    _cache[name] = concept
    log.info("concept_loaded", concept=name, element_count=len(elements))
    return concept


def get_element_alias_map(concept: Concept) -> Dict[str, int]:
    """Build a map from aliases to element IDs for fast lookup.

    Args:
        concept: Concept with elements

    Returns:
        Dict mapping lowercased aliases/labels to element IDs
    """
    alias_map = {}
    for element in concept.elements:
        # Add label as alias
        alias_map[element.label.lower()] = element.id
        # Add all aliases
        for alias in element.aliases:
            alias_map[alias.lower()] = element.id

    return alias_map
