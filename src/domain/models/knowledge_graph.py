"""Domain models for knowledge graph nodes and edges."""

from pydantic import BaseModel, Field, model_validator, computed_field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime, timezone
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class NodeType(str, Enum):
    """Valid node types for Means-End Chain methodology.

    DEPRECATED: This enum is kept for IDE autocomplete only.
    The authoritative source of truth is config/methodologies/means_end_chain.yaml.
    Use src.core.schema_loader.load_methodology() to get valid types at runtime.
    """

    ATTRIBUTE = "attribute"
    FUNCTIONAL_CONSEQUENCE = "functional_consequence"
    PSYCHOSOCIAL_CONSEQUENCE = "psychosocial_consequence"
    INSTRUMENTAL_VALUE = "instrumental_value"
    TERMINAL_VALUE = "terminal_value"


class EdgeType(str, Enum):
    """Valid edge types.

    DEPRECATED: This enum is kept for IDE autocomplete only.
    The authoritative source of truth is config/methodologies/means_end_chain.yaml.
    Use src.core.schema_loader.load_methodology() to get valid types at runtime.
    """

    LEADS_TO = "leads_to"
    REVISES = "revises"


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
    """

    chao1_ratio: float = Field(
        description="Chao1 diversity estimator (0-1)", ge=0.0, le=1.0
    )
    new_info_rate: float = Field(
        description="Rate of novel concept introduction", ge=0.0, le=1.0
    )
    consecutive_low_info: int = Field(
        description="Turns since last novel concept", ge=0
    )
    is_saturated: bool = Field(description="Derived: indicates topic exhaustion")


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
    strategy_history: List[str] = Field(
        default_factory=list,
        description="History of recently used strategies for diversity tracking",
    )

    # === Extensibility (ADR-010) ===
    extended_properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Experimental metrics not yet promoted to first-class fields",
    )

    # === Backwards Compatibility (migration period) ===
    # Deprecated: Use current_phase instead
    @computed_field
    @property
    def phase(self) -> str:
        """Current interview phase (deprecated: use current_phase)."""
        return self.current_phase

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

    # === Backwards Compatibility Methods ===

    def get_phase(self) -> str:
        """Get current interview phase (deprecated: use current_phase directly)."""
        return self.current_phase

    def set_phase(self, phase: str) -> None:
        """Transition to a new phase.

        Args:
            phase: New phase ('exploratory', 'focused', or 'closing')
        """
        # This will validate via Pydantic on assignment
        self.current_phase = phase  # type: ignore

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
