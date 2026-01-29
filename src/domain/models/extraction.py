"""Domain models for extraction results."""

from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class ExtractedConcept(BaseModel):
    """A concept extracted from user text.

    Represents a potential knowledge graph node before deduplication.

    ADR-010 Phase 2: Added source_utterance_id for traceability and
    made stance optional to handle cases where it's not applicable.
    """

    text: str = Field(description="Normalized concept text")
    node_type: str = Field(
        description="Methodology-specific type (attribute, consequence, value)"
    )
    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Confidence score 0-1"
    )
    source_quote: str = Field(
        default="", description="Verbatim text from user response"
    )
    source_utterance_id: str = Field(
        description="Source utterance ID for traceability (ADR-010 Phase 2)"
    )
    linked_elements: List[int] = Field(
        default_factory=list,
        description="Element IDs from concept config this concept relates to",
    )
    stance: Optional[int] = Field(
        default=None,
        ge=-1,
        le=1,
        description="Stance: -1 (negative), 0 (neutral), +1 (positive), or null if N/A",
    )
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible metadata for methodology-specific info",
    )
    is_terminal: bool = Field(
        default=False, description="Whether this is a terminal node type"
    )
    level: int = Field(default=0, description="Hierarchy level in the methodology")


class ExtractedRelationship(BaseModel):
    """A relationship extracted from user text.

    Links two extracted concepts.

    ADR-010 Phase 2: Added reasoning and source_utterance_id for
    traceability and understanding of why edges were created.
    """

    source_text: str = Field(description="Source concept text")
    target_text: str = Field(description="Target concept text")
    relationship_type: str = Field(description="Methodology-specific edge type")
    confidence: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Confidence score 0-1"
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Why this edge was created (explicit vs implicit)",
    )
    source_utterance_id: str = Field(
        description="Source utterance ID for traceability (ADR-010 Phase 2)"
    )


class ExtractionResult(BaseModel):
    """Complete extraction result from a single utterance.

    Contains all concepts and relationships extracted from user input.

    ADR-010: Added timestamp field for freshness validation in StrategySelectionStage.
    """

    concepts: List[ExtractedConcept] = Field(default_factory=list)
    relationships: List[ExtractedRelationship] = Field(default_factory=list)
    discourse_markers: List[str] = Field(default_factory=list)  # "because", "so", etc.
    is_extractable: bool = True
    extractability_reason: Optional[str] = None
    latency_ms: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When extraction was performed (ADR-010 freshness tracking)",
    )
