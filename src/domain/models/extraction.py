"""Domain models for extraction results."""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class ExtractedConcept(BaseModel):
    """A concept extracted from user text.

    Represents a potential knowledge graph node before deduplication.
    """

    text: str  # Original text from user
    node_type: str  # Suggested type (attribute, consequence, value)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    source_quote: str = ""  # Verbatim quote from utterance
    properties: Dict[str, Any] = Field(default_factory=dict)
    stance: int = Field(
        default=0, ge=-1, le=1
    )  # Stance: -1 (negative), 0 (neutral), +1 (positive)


class ExtractedRelationship(BaseModel):
    """A relationship extracted from user text.

    Links two extracted concepts.
    """

    source_text: str  # Source concept text
    target_text: str  # Target concept text
    relationship_type: str  # "leads_to" or "revises"
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    source_quote: str = ""


class ExtractionResult(BaseModel):
    """Complete extraction result from a single utterance.

    Contains all concepts and relationships extracted from user input.
    """

    concepts: List[ExtractedConcept] = Field(default_factory=list)
    relationships: List[ExtractedRelationship] = Field(default_factory=list)
    discourse_markers: List[str] = Field(default_factory=list)  # "because", "so", etc.
    is_extractable: bool = True
    extractability_reason: Optional[str] = None
    latency_ms: int = 0
