"""
API routes for concept configuration management.

GET /concepts - List available concepts
GET /concepts/{id} - Get concept details
"""

from typing import List, Dict, Any

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import structlog

from src.core.config import settings


log = structlog.get_logger(__name__)
router = APIRouter(prefix="/concepts", tags=["concepts"])


# Response Models
class ConceptElement(BaseModel):
    """Single element in a concept configuration."""

    id: str = Field(description="Element identifier")
    label: str = Field(description="Display label")
    type: str = Field(description="Element type (attribute, consequence, etc.)")
    priority: str = Field(description="Priority level (high, medium, low)")


class ConceptCompletion(BaseModel):
    """Completion criteria for a concept."""

    target_coverage: float = Field(description="Target coverage threshold")
    max_turns: int = Field(description="Maximum turns")
    saturation_threshold: float = Field(description="Saturation threshold")


class ConceptConfig(BaseModel):
    """Concept configuration."""

    id: str = Field(description="Concept ID")
    name: str = Field(description="Concept name")
    description: str = Field(default="", description="Description")
    methodology: str = Field(description="Methodology ID")
    elements: List[ConceptElement] = Field(
        default_factory=list, description="Concept elements"
    )
    completion: ConceptCompletion = Field(description="Completion criteria")


class ConceptListItem(BaseModel):
    """Item in concept list."""

    id: str
    name: str
    methodology: str
    element_count: int


def _load_concepts_from_config() -> List[Dict[str, Any]]:
    """Load concepts from configuration directory."""
    concepts_dir = settings.config_dir / "concepts"

    if not concepts_dir.exists():
        log.warning("concepts_directory_not_found", path=str(concepts_dir))
        return []

    concepts = []

    for yaml_file in concepts_dir.glob("*.yaml"):
        try:
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
                if data:
                    concepts.append(data)
        except Exception as e:
            log.warning(
                "concept_load_failed",
                file=str(yaml_file),
                error=str(e),
            )

    log.info("concepts_loaded", count=len(concepts))
    return concepts


# Routes
@router.get(
    "",
    response_model=List[ConceptListItem],
    summary="List available concepts",
    description="Get list of all available concept configurations",
)
async def list_concepts() -> List[ConceptListItem]:
    """List all available concept configurations."""
    concepts = _load_concepts_from_config()

    return [
        ConceptListItem(
            id=c.get("id", ""),
            name=c.get("name", ""),
            methodology=c.get("methodology", ""),
            element_count=len(c.get("elements", [])),
        )
        for c in concepts
    ]


@router.get(
    "/{concept_id}",
    response_model=ConceptConfig,
    summary="Get concept details",
    description="Get full configuration for a specific concept",
)
async def get_concept(concept_id: str) -> ConceptConfig:
    """Get detailed concept configuration."""
    concepts = _load_concepts_from_config()
    concept_data = next((c for c in concepts if c["id"] == concept_id), None)

    if not concept_data:
        log.warning("concept_not_found", concept_id=concept_id)
        raise HTTPException(
            status_code=404,
            detail=f"Concept '{concept_id}' not found",
        )

    log.info("concept_retrieved", concept_id=concept_id)
    return ConceptConfig(**concept_data)


@router.get(
    "/{concept_id}/elements",
    response_model=List[ConceptElement],
    summary="Get concept elements",
    description="Get elements for a specific concept",
)
async def get_concept_elements(concept_id: str) -> List[ConceptElement]:
    """Get elements for a concept configuration."""
    concepts = _load_concepts_from_config()
    concept_data = next((c for c in concepts if c.get("id") == concept_id), None)

    if not concept_data:
        log.warning("concept_not_found", concept_id=concept_id)
        raise HTTPException(
            status_code=404,
            detail=f"Concept '{concept_id}' not found",
        )

    elements = concept_data.get("elements", [])

    log.info("concept_elements_retrieved", concept_id=concept_id, count=len(elements))
    return [
        ConceptElement(
            id=e.get("id", ""),
            label=e.get("label", ""),
            type=e.get("type", ""),
            priority=e.get("priority", "medium"),
        )
        for e in elements
    ]
