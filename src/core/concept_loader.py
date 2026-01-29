"""Concept loader for concept YAML files.

Loads concept definitions including elements with labels and aliases.
Used during extraction to link extracted concepts to predefined elements.
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
    """Load concept from YAML. Cached after first load.

    Args:
        name: Concept name (e.g., 'oat_milk_v2')
        concepts_dir: Override config/concepts/ path (mainly for testing)

    Returns:
        Loaded and validated Concept instance

    Raises:
        FileNotFoundError: Concept file missing
        ValueError: Invalid YAML structure or validation error
    """
    if name in _cache:
        return _cache[name]

    if concepts_dir is None:
        concepts_dir = Path(__file__).parent.parent.parent / "config" / "concepts"

    path = concepts_dir / f"{name}.yaml"
    if not path.exists():
        # Try without _v2 suffix for backwards compatibility
        path_without_suffix = concepts_dir / f"{name.replace('_v2', '')}.yaml"
        if path_without_suffix.exists():
            path = path_without_suffix
        else:
            raise FileNotFoundError(f"Concept not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    # Parse context
    context_data = data.get("context", {})
    context = ConceptContext(
        topic=context_data.get("topic", ""),
        insight=context_data.get("insight", ""),
        objective=context_data.get("objective"),  # New field for exploratory interviews
        promise=context_data.get("promise"),
        rtb=context_data.get("rtb"),
    )

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
