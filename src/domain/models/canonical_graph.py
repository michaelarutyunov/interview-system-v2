"""
Domain models for canonical graph (dual-graph architecture).

The canonical graph abstracts surface-level nodes into stable "slots" representing
latent concepts. Multiple surface nodes map to a single canonical slot via similarity
matching, enabling robust concept tracking despite respondent language variation.

Architecture Reference: Phase 2 (Dual-Graph Construction)
Bead: 46hu
"""

from typing import List, Optional
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger(__name__)


class CanonicalSlot(BaseModel):
    """A canonical slot in the canonical graph.

    A slot represents a latent concept abstracted from multiple surface nodes.
    Surface nodes are mapped to slots via embedding similarity (spaCy en_core_web_md).

    Lifecycle:
    - Created as 'candidate' when first surface node suggests a new concept
    - Promoted to 'active' after meeting support_count and turn thresholds
    - Status changes on promotion, so model is NOT frozen

    Node Type Preservation:
        node_type preserves methodology hierarchy (attribute, consequence, value)
        to enable type-aware canonical slot discovery and edge aggregation.
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
        default=None, description="Serialized numpy embedding (float32, 300-dim for en_core_web_md)"
    )

    model_config = {"from_attributes": True}


class SlotMapping(BaseModel):
    """Maps a surface node to its canonical slot.

    Represents the many-to-one relationship where multiple surface nodes
    (KGNode instances) map to a single CanonicalSlot via similarity scoring.
    """

    surface_node_id: str = Field(description="ID of the surface node (from kg_nodes table)")
    canonical_slot_id: str = Field(description="ID of the canonical slot (from canonical_slots table)")
    similarity_score: float = Field(
        ge=0.0, le=1.0, description="Cosine similarity score (0.0-1.0)"
    )
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
    """Current state of the canonical graph for a session.

    Parallel to GraphState but operates on canonical slots instead of surface nodes.
    Computed during StateComputationStage (Stage 5) alongside surface graph state.

    Orphan Definition (AMBIGUITY RESOLUTION 2026-02-07):
        Only ACTIVE slots (status='active') with zero canonical edges are orphans.
        Candidate slots are excluded from orphan counting entirely.
    """

    concept_count: int = Field(
        ge=0, description="Active slots only (candidates excluded)"
    )
    edge_count: int = Field(ge=0, description="Canonical edges")
    orphan_count: int = Field(
        ge=0,
        description="Active slots with no canonical edges (candidates excluded)",
    )
    max_depth: int = Field(ge=0, description="Longest canonical chain")
    avg_support: float = Field(
        ge=0.0, description="Average support_count per active slot"
    )

    model_config = {"from_attributes": True}


# Export all models for easy importing
__all__ = [
    "CanonicalSlot",
    "SlotMapping",
    "CanonicalEdge",
    "CanonicalGraphState",
]
