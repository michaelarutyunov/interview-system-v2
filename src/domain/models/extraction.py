"""Extraction domain models for concepts and relationships from user input.

This module defines models for LLM-based extraction results that represent
structured knowledge discovered from participant responses.

Core Models:
    - ExtractedConcept: Potential knowledge graph node before deduplication
    - ExtractedRelationship: Causal or associative link between concepts
    - ExtractionResult: Complete extraction with metadata for freshness tracking

Key Concepts:
    - Source utterance provenance: traceability from extraction to original utterance
    - Stance tracking: deprecated (llm.valence covers sentiment); kept for backward compat
    - Methodology-specific typing: node_type, edge_type, linked_elements
    - Freshness validation: timestamp for LLM signal staleness detection
"""

from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class ExtractedConcept(BaseModel):
    """Concept extracted from user response, pre-deduplication.

    Represents a potential knowledge graph node identified by LLM extraction.
    After deduplication, becomes a KGNode in the knowledge graph.

    Key Attributes:
        - node_type: Methodology-specific type (attribute, consequence, value)
        - linked_elements: Element IDs from concept config for coverage tracking
        - stance: Sentiment polarity (-1/0/+1) for attitude modeling
        - source_utterance_id: Traceability to original utterance (ADR-010)

    Lifecycle:
        1. Extracted from user input by ExtractionStage (Stage 3)
        2. Deduplicated against existing nodes
        3. Converted to KGNode and persisted in GraphUpdateStage (Stage 4)
    """

    text: str = Field(description="Normalized concept text")
    node_type: str = Field(description="Methodology-specific type (attribute, consequence, value)")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence score 0-1")
    source_quote: str = Field(default="", description="Verbatim text from user response")
    source_utterance_id: str = Field(description="Source utterance ID for traceability")
    linked_elements: List[int] = Field(
        default_factory=list,
        description="Element IDs from concept config this concept relates to",
    )
    stance: Optional[int] = Field(
        default=None,
        ge=-1,
        le=1,
        description="Deprecated: no longer extracted. llm.valence covers sentiment. "
        "Kept for backward compat. Values: -1 (negative), 0 (neutral), +1 (positive).",
    )
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible metadata for methodology-specific info",
    )
    is_terminal: bool = Field(default=False, description="Whether this is a terminal node type")
    level: int = Field(default=0, description="Hierarchy level in the methodology")


class ExtractedRelationship(BaseModel):
    """Relationship extracted between two concepts from user response.

    Represents a causal, hierarchical, or associative connection identified
    by LLM extraction. After concept deduplication, becomes a KGEdge.

    Relationship Types (methodology-specific):
        - leads_to: Causal or consequential relationship
        - revises: Correction or refinement of earlier concept
        - is_a: Taxonomic or hierarchical classification
        - relates_to: General associative connection

    Key Attributes:
        - reasoning: Explanation of why relationship exists (explicit vs implicit)
        - source_utterance_id: Traceability to original utterance (ADR-010)
    """

    source_text: str = Field(description="Source concept text")
    target_text: str = Field(description="Target concept text")
    relationship_type: str = Field(description="Methodology-specific edge type")
    confidence: float = Field(default=0.7, ge=0.0, le=1.0, description="Confidence score 0-1")
    reasoning: Optional[str] = Field(
        default=None,
        description="Why this edge was created (explicit vs implicit)",
    )
    source_utterance_id: str = Field(description="Source utterance ID for traceability")


class ExtractionResult(BaseModel):
    """Complete LLM extraction result from a single utterance.

    Container for all concepts and relationships extracted from user input,
    produced by ExtractionStage (Stage 3) and consumed by
    GraphUpdateStage (Stage 4).

    Freshness Tracking:
        timestamp field enables staleness detection in StrategySelectionStage
        (Stage 6). Qualitative signals should be from current turn,
        not recycled from extractions on older utterances.

    Non-extractable Cases:
        - is_extractable=False: User input too brief, off-topic, or
          purely conversational (e.g., "I don't know", "sure")
        - extractability_reason: Explanation for why no extraction occurred
    """

    concepts: List[ExtractedConcept] = Field(default_factory=list)
    relationships: List[ExtractedRelationship] = Field(default_factory=list)
    is_extractable: bool = True
    extractability_reason: Optional[str] = None
    latency_ms: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When extraction was performed (for freshness tracking)",
    )
