"""Persona loader for synthetic respondent generation.

Loads persona definitions from YAML files in config/personas/.
Each persona defines a synthetic respondent's traits, speech patterns,
and response behaviors for testing the interview system.
"""

import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List
import structlog
from pydantic import BaseModel, Field

log = structlog.get_logger(__name__)

# Module-level cache (singleton pattern - personas don't change at runtime)
_cache: Dict[str, Dict[str, Any]] = {}


class PersonaConfig(BaseModel):
    """Validated persona configuration.

    Attributes:
        id: Unique persona identifier
        name: Human-readable persona name
        description: Brief description of the persona
        traits: List of personality traits
        speech_pattern: Description of speech patterns
        response_patterns: Optional dict of response type probabilities
        deflection_patterns: Optional list of deflection phrases
    """

    id: str = Field(..., description="Unique persona identifier")
    name: str = Field(..., description="Human-readable persona name")
    description: str = Field(..., description="Brief description of the persona")
    traits: List[str] = Field(default_factory=list, description="Personality traits")
    speech_pattern: str = Field(..., description="Speech pattern description")
    response_patterns: Optional[Dict[str, float]] = Field(
        default=None,
        description="Response type probabilities (detailed, medium, brief, acknowledgment)",
    )
    deflection_patterns: Optional[List[str]] = Field(
        default=None,
        description="Deflection phrases for authentic respondent behavior",
    )


def list_personas() -> Dict[str, str]:
    """List all available personas.

    Returns:
        Dict mapping persona_id to persona_name
    """
    personas_dir = Path(__file__).parent.parent.parent / "config" / "personas"

    if not personas_dir.exists():
        return {}

    personas = {}
    for persona_file in personas_dir.glob("*.yaml"):
        try:
            with open(persona_file) as f:
                data = yaml.safe_load(f)
                persona_id = data.get("id", persona_file.stem)
                persona_name = data.get("name", persona_file.stem)
                personas[persona_id] = persona_name
        except Exception as e:
            log.warning("failed_to_load_persona", file=str(persona_file), error=str(e))

    return personas


def load_persona(persona_id: str) -> PersonaConfig:
    """Load a persona configuration from YAML.

    Args:
        persona_id: Persona identifier (e.g., "health_conscious")

    Returns:
        Validated PersonaConfig instance

    Raises:
        FileNotFoundError: If persona file not found
        ValueError: If persona validation fails
    """
    # Check cache first
    if persona_id in _cache:
        return PersonaConfig(**_cache[persona_id])

    personas_dir = Path(__file__).parent.parent.parent / "config" / "personas"
    persona_file = personas_dir / f"{persona_id}.yaml"

    if not persona_file.exists():
        raise FileNotFoundError(
            f"Persona file not found: {persona_file}\n"
            f"Available personas: {', '.join(list_personas().keys())}"
        )

    with open(persona_file) as f:
        data = yaml.safe_load(f)

    # Validate with Pydantic
    persona_config = PersonaConfig(**data)

    # Cache for future use
    _cache[persona_id] = data

    log.info("persona_loaded", persona_id=persona_id, name=persona_config.name)
    return persona_config


def load_all_personas() -> Dict[str, PersonaConfig]:
    """Load all available personas.

    Returns:
        Dict mapping persona_id to PersonaConfig
    """
    personas = {}
    for persona_id in list_personas().keys():
        try:
            personas[persona_id] = load_persona(persona_id)
        except Exception as e:
            log.error("persona_load_failed", persona_id=persona_id, error=str(e))

    return personas


def clear_cache() -> None:
    """Clear the persona cache (mainly for testing)."""
    global _cache
    _cache = {}
