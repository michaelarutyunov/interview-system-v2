"""Domain models for knowledge graph nodes and edges."""

from collections import deque
from pydantic import BaseModel, Field, model_validator, field_validator
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime, timezone
import structlog

logger = structlog.get_logger(__name__)


class KGNode(BaseModel):
    """A node in the knowledge graph.

    Simplified from v1: Single timestamp instead of bi-temporal versioning.
    """

    id: str
    session_id: str
    label: str
    node_type: str  # One of NodeType values
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    properties: Dict[str, Any] = Field(default_factory=dict)
    source_utterance_ids: List[str] = Field(default_factory=list)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    superseded_by: Optional[str] = (
        None  # Node ID that supersedes this one (for REVISES)
    )
    stance: int = Field(
        default=0, ge=-1, le=1
    )  # Stance: -1 (negative), 0 (neutral), +1 (positive)

    model_config = {"from_attributes": True}


class KGEdge(BaseModel):
    """A relationship in the knowledge graph."""

    id: str
    session_id: str
    source_node_id: str
    target_node_id: str
    edge_type: str  # One of EdgeType values
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    properties: Dict[str, Any] = Field(default_factory=dict)
    source_utterance_ids: List[str] = Field(default_factory=list)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"from_attributes": True}


class DepthMetrics(BaseModel):
    """Depth analysis of the knowledge graph (ADR-010).

    Tracks various depth metrics for scoring and analysis.
    """

    max_depth: int = Field(description="Length of longest reasoning chain", ge=0)
    avg_depth: float = Field(description="Average depth across all nodes", ge=0.0)
    depth_by_element: Dict[str, float] = Field(
        description="Average depth per element ID",
        default_factory=dict,
    )
    longest_chain_path: List[str] = Field(
        description="Node IDs in the deepest chain",
        default_factory=list,
    )


class SaturationMetrics(BaseModel):
    """Information saturation indicators (ADR-010).

    Tracks whether the interview is reaching information saturation.
    Computed by StateComputationStage (Stage 5) and consumed by
    ContinuationStage (Stage 7) for termination decisions.
    """

    # === Core saturation metrics ===
    chao1_ratio: float = Field(
        default=0.0,
        description="Chao1 diversity estimator (0-1, placeholder for future)",
        ge=0.0,
        le=1.0,
    )
    new_info_rate: float = Field(
        default=0.0,
        description="Rate of novel concept introduction",
        ge=0.0,
        le=1.0,
    )
    consecutive_low_info: int = Field(
        default=0,
        description="Turns since last novel concept (consecutive zero yield)",
        ge=0,
    )
    is_saturated: bool = Field(
        default=False,
        description="Derived: indicates topic exhaustion",
    )

    # === Quality degradation tracking ===
    consecutive_shallow: int = Field(
        default=0,
        description="Turns with only shallow/surface responses",
        ge=0,
    )

    # === Depth plateau tracking ===
    consecutive_depth_plateau: int = Field(
        default=0,
        description="Turns at same max_depth (no depth progress)",
        ge=0,
    )
    prev_max_depth: int = Field(
        default=-1,
        description="Previous turn's max_depth (for plateau detection)",
    )


class GraphState(BaseModel):
    """Current state of the knowledge graph for a session.

    ADR-010: Strengthened data model with typed fields instead of generic
    properties dict for better type safety and validation.
    """

    # === Basic Counts ===
    node_count: int = Field(ge=0, default=0)
    edge_count: int = Field(ge=0, default=0)
    nodes_by_type: Dict[str, int] = Field(default_factory=dict)
    edges_by_type: Dict[str, int] = Field(default_factory=dict)
    orphan_count: int = Field(ge=0, default=0)

    # === Structured Metrics (ADR-010) ===
    depth_metrics: DepthMetrics = Field(
        description="Depth analysis of the knowledge graph"
    )
    saturation_metrics: Optional[SaturationMetrics] = Field(
        default=None,
        description="Information saturation indicators (expensive to compute)",
    )

    # === Phase Tracking (promoted from properties, ADR-010) ===
    current_phase: Literal["exploratory", "focused", "closing"] = "exploratory"
    turn_count: int = Field(ge=0, default=0)
    strategy_history: Any = Field(
        default_factory=lambda: deque(maxlen=30),
        description="History of recently used strategies (max 30 for diversity tracking)",
    )

    # === Extensibility (ADR-010) ===
    extended_properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Experimental metrics not yet promoted to first-class fields",
    )

    @model_validator(mode="after")
    def validate_consistency(self) -> "GraphState":
        """Validate internal consistency of the graph state."""
        # Count consistency: node_count must match sum of nodes_by_type
        if self.nodes_by_type:
            total_by_type = sum(self.nodes_by_type.values())
            if total_by_type != self.node_count:
                raise ValueError(
                    f"node_count ({self.node_count}) must equal sum of nodes_by_type "
                    f"({total_by_type})"
                )

        # Phase-turn sanity check: closing phase with fewer than 3 turns is unusual
        if self.current_phase == "closing" and self.turn_count < 3:
            logger.warning(
                "Closing phase at turn %d - unusually early",
                self.turn_count,
                extra={
                    "turn_count": self.turn_count,
                    "phase": self.current_phase,
                },
            )

        return self

    @field_validator("strategy_history", mode="before")
    @classmethod
    def _ensure_strategy_history_deque(cls, v: Any) -> Any:
        """Convert list to deque on load from DB (backward compatibility).

        When loading from database, Pydantic deserializes as list.
        This validator converts it to deque for automatic trimming.

        Args:
            v: Value from DB (list or deque)

        Returns:
            deque(maxlen=30) with preserved items
        """
        if isinstance(v, list):
            return deque(v, maxlen=30)
        return v

    def add_strategy_used(self, strategy_id: str) -> None:
        """Record a strategy selection in history for diversity tracking.

        This maintains a list of recently used strategies so the
        StrategyDiversityScorer can penalize repetitive questioning
        patterns and encourage interview variety.

        Args:
            strategy_id: The strategy that was selected
                (e.g., 'broaden', 'deepen', 'cover_element', 'close')
        """
        self.strategy_history.append(strategy_id)
