"""Canonical graph domain models for dual-graph architecture.

This module defines the canonical graph that abstracts surface-level nodes
into stable "slots" representing latent concepts. Dual-graph architecture
enables robust concept tracking despite respondent language variation.

Core Concepts:
    - Canonical Slots: Stable latent concepts abstracted from surface nodes
    - Slot Mappings: Many-to-one relationship from surface nodes to slots
    - Canonical Edges: Aggregate relationships with support counts
    - CanonicalGraphState: Session-level canonical metrics (parallel to GraphState)

Architecture Rationale:
    Surface nodes are language-dependent ("fast car", "quick vehicle")
    while canonical slots represent stable latent concepts ("speed_performance").
    Similarity matching (spaCy embeddings) maps surface to canonical.

Orphan Definition (AMBIGUITY RESOLUTION 2026-02-07):
    Only ACTIVE slots (status='active') with zero canonical edges count
    as orphans. Candidate slots are excluded entirely from orphan counting.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger(__name__)


class CanonicalSlot(BaseModel):
    """Stable latent concept abstracted from multiple surface nodes.

    A canonical slot represents a single concept that may have been mentioned
    using various surface phrases. Surface nodes map to slots via embedding
    similarity (spaCy en_core_web_md, 300-dim vectors).

    Lifecycle:
        1. Created as 'candidate' when first surface node suggests new concept
        2. Additional surface nodes increase support_count
        3. Promoted to 'active' after meeting thresholds
        4. Status field changes (model is NOT frozen)

    Node Type Preservation:
        node_type preserves methodology hierarchy (attribute, consequence, value)
        for type-aware canonical slot discovery and edge aggregation.

    Fields:
        - slot_name: LLM-generated canonical name (e.g., 'energy_stability')
        - description: LLM-generated concept explanation
        - support_count: Number of surface nodes mapped to this slot
        - first_seen_turn/promoted_turn: Lifecycle tracking
        - embedding: Serialized numpy float32 vector for similarity matching
    """

    id: str
    session_id: str
    slot_name: str = Field(description="LLM-generated canonical name (e.g., 'energy_stability')")
    description: str = Field(description="LLM-generated description of the concept")
    node_type: str = Field(
        description="Preserves methodology hierarchy - same types as KGNode.node_type"
    )
    status: str = Field(description="'candidate' or 'active'")
    support_count: int = Field(
        default=0, ge=0, description="Number of surface nodes mapped to this slot"
    )
    first_seen_turn: int = Field(ge=1, description="Turn when slot was first created")
    promoted_turn: Optional[int] = Field(
        default=None,
        description="Turn when slot was promoted to active (None if still candidate)",
    )
    embedding: Optional[bytes] = Field(
        default=None,
        description="Serialized numpy embedding (float32, 300-dim for en_core_web_md)",
    )

    model_config = {"from_attributes": True}


class SlotMapping(BaseModel):
    """Maps a surface node to its canonical slot.

    Represents the many-to-one relationship where multiple surface nodes
    (KGNode instances) map to a single CanonicalSlot via similarity scoring.
    """

    surface_node_id: str = Field(description="ID of the surface node (from kg_nodes table)")
    canonical_slot_id: str = Field(
        description="ID of the canonical slot (from canonical_slots table)"
    )
    similarity_score: float = Field(ge=0.0, le=1.0, description="Cosine similarity score (0.0-1.0)")
    assigned_turn: int = Field(ge=1, description="Turn when this mapping was created")

    model_config = {"from_attributes": True}


class CanonicalEdge(BaseModel):
    """A relationship in the canonical graph.

    Canonical edges aggregate multiple surface edges that connect the same
    conceptual relationship. The support_count represents the weight of
    evidence for this canonical relationship.

    Provenance Tracking:
        surface_edge_ids maintains provenance by listing all supporting
        surface edge IDs, enabling traceability back to original utterances.
    """

    id: str
    session_id: str
    source_slot_id: str = Field(description="Source canonical slot ID")
    target_slot_id: str = Field(description="Target canonical slot ID")
    edge_type: str = Field(description="Edge type (leads_to, revises, etc.)")
    support_count: int = Field(
        default=1, ge=1, description="Weight = number of supporting surface edges"
    )
    surface_edge_ids: List[str] = Field(
        default_factory=list,
        description="Provenance - IDs of surface edges supporting this canonical edge",
    )

    model_config = {"from_attributes": True}


class CanonicalGraphState(BaseModel):
    """Session-level canonical graph state metrics.

    Parallel to GraphState but operates on canonical slots instead of
    surface nodes. Computed during StateComputationStage (Stage 5)
    alongside surface graph state metrics.

    Metrics:
        - concept_count: Active slots only (candidates excluded)
        - edge_count: Total canonical edges
        - orphan_count: Active slots with no edges (candidates excluded)
        - max_depth: Longest canonical chain for depth analysis
        - avg_support: Average surface nodes per slot (richness measure)

    Orphan Definition (2026-02-07 RESOLUTION):
        Only slots with status='active' AND zero canonical edges
        are counted as orphans. Candidate slots are excluded entirely.

    Used by:
        - CanonicalOrphanCountSignal (canonical_graph.orphan_count)
        - Coverage and depth scoring for canonical-level decisions
    """

    concept_count: int = Field(ge=0, description="Active slots only (candidates excluded)")
    edge_count: int = Field(ge=0, description="Canonical edges")
    orphan_count: int = Field(
        ge=0,
        description="Active slots with no canonical edges (candidates excluded)",
    )
    max_depth: int = Field(ge=0, description="Longest canonical chain")
    avg_support: float = Field(ge=0.0, description="Average support_count per active slot")

    model_config = {"from_attributes": True}


# Export all models for easy importing
__all__ = [
    "CanonicalSlot",
    "SlotMapping",
    "CanonicalEdge",
    "CanonicalGraphState",
]
