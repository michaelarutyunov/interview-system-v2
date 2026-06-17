"""Edge extraction domain models for cross-turn edge identification and typing.

This module defines models for Stage 4.5B edge extraction, which separates
edge identification from node extraction (Stage 3) for improved quality.

Core Models:
    - ConfirmedEdge: Evidenced edge with confidence level and supporting span
    - RejectedEdgeCandidate: Edge rejected with structured rejection reason
    - EdgeExtractionOutput: Complete extraction result with audit trail

Key Concepts:
    - Confidence calibration: high (explicit) / medium (implied) / low (inferred across turns)
    - Supporting span: character offsets grounding edge to source utterance
    - Rejection taxonomy: standardised codes for auditability per D7
    - Audit trail: rejected candidates retained for observability, not silently discarded

Rejection Reason Taxonomy (5 codes per D7):
    type_constraint_violation     — Edge type not permitted for this source/target pair
    insufficient_evidence         — No transcript span supports the relationship
    duplicate_edge                — Same (source, target, type) edge already exists
    semantic_irrelevance          — Source and target nodes are topically unrelated
    question_frame_contamination  — Causal frame supplied by interviewer, not respondent

See docs/edge-extraction-decisions.md for architecture decisions.
"""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

ConfidenceLevel = Literal["high", "medium", "low"]

VALID_REJECTION_REASONS: frozenset[str] = frozenset(
    {
        "type_constraint_violation",
        "insufficient_evidence",
        "duplicate_edge",
        "semantic_irrelevance",
        "question_frame_contamination",
    }
)


def is_valid_rejection_reason(code: str) -> bool:
    """Check whether a rejection reason code is in the standard taxonomy."""
    return code in VALID_REJECTION_REASONS


class ConfirmedEdge(BaseModel):
    """An edge confirmed by the LLM with evidence and confidence level.

    Represents a single directed relationship between two graph nodes,
    grounded in transcript evidence via supporting_span.

    Reasoning is captured as structured axes (assertion, direction, frame)
    rather than free-form prose, reducing output token consumption by ~75%.
    Confidence is derivable from these three axes per the prompt specification.
    """

    source_node_id: str = Field(description="Source graph node ID (post-dedup)")
    target_node_id: str = Field(description="Target graph node ID (post-dedup)")
    edge_type: str = Field(
        description="Methodology-specific edge type (e.g., triggers, implies)"
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description="Confidence level: high (explicitly stated), medium (implied), low (inferred across turns)"
    )
    supporting_span: tuple[int, int] = Field(
        description="Character offsets [start, end] in source utterance that support this edge"
    )
    utterance_id: str = Field(
        description="ID of the utterance containing the supporting evidence"
    )
    reasoning_summary: str = Field(
        default="",
        description="Human-readable summary derived from structured reasoning axes",
    )
    assertion: Literal["explicit", "implicit", "inferred"] | None = Field(
        default=None,
        description="How the respondent asserted the relationship: explicit (directly stated), implicit (strongly implied), inferred (across turns or weakly)",
    )
    direction: Literal["clear", "uncertain"] | None = Field(
        default=None, description="Whether the causal direction is unambiguous"
    )
    frame: Literal["respondent", "minor_influence", "contaminated"] | None = Field(
        default=None,
        description="Frame contamination: respondent (self-asserted), minor_influence (slight interviewer framing), contaminated (interviewer supplied the causal frame)",
    )


class RejectedEdgeCandidate(BaseModel):
    """An edge candidate the LLM considered but rejected.

    Retained for audit logging and observability. Rejected candidates are not
    written to the knowledge graph but are surfaced via structured logging.

    Reasoning is omitted for rejected candidates — the rejection_reason taxonomy
    code (one of 5 standard codes) captures the rationale. This reduces output
    tokens by ~50% since ~80% of candidate pairs are typically rejected.
    """

    source_node_id: str = Field(description="Source graph node ID (post-dedup)")
    target_node_id: str = Field(description="Target graph node ID (post-dedup)")
    rejection_reason: str = Field(
        description=(
            "Standardised rejection code. One of the 5 D7 taxonomy codes: "
            "type_constraint_violation, insufficient_evidence, duplicate_edge, "
            "semantic_irrelevance, question_frame_contamination"
        )
    )
    reasoning_summary: str = Field(
        default="",
        description="Optional reasoning from the LLM (empty for structured-format responses)",
    )


class EdgeExtractionOutput(BaseModel):
    """Complete output from the edge extraction stage (Stage 4.5B).

    Contains confirmed edges for graph persistence, rejected candidates for
    audit logging, and metadata for latency tracking.
    """

    confirmed_edges: list[ConfirmedEdge] = Field(
        default_factory=list,
        description="Edges that passed evidence and confidence review",
    )
    rejected_candidates: list[RejectedEdgeCandidate] = Field(
        default_factory=list,
        description="Edge candidates that were considered but rejected with reasons",
    )
    low_confidence_count: int = Field(
        default=0,
        description="Count of confirmed edges with confidence='low' (for downstream audit)",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When edge extraction was performed",
    )
    latency_ms: int = Field(
        default=0,
        description="LLM call latency in milliseconds",
    )
