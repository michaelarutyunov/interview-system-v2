"""Domain models for knowledge graph nodes and edges."""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from enum import Enum


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


class ElementCoverage(BaseModel):
    """Coverage state for a single element."""

    covered: bool = False  # Any linked node = covered
    linked_node_ids: List[str] = Field(default_factory=list)
    types_found: List[str] = Field(default_factory=list)
    depth_score: float = 0.0  # Chain validation: longest connected path / ladder length


class CoverageState(BaseModel):
    """Coverage state for concept elements."""

    elements: Dict[int, ElementCoverage] = Field(default_factory=dict)
    elements_covered: int = 0  # How many elements have any linked nodes
    elements_total: int = 0  # Total elements in concept
    overall_depth: float = 0.0  # Average depth_score across all elements
    max_depth: float = 0.0  # P0 Fix: Maximum depth_score (monotonically increasing)


class GraphState(BaseModel):
    """Current state of the knowledge graph for a session."""

    node_count: int = 0
    edge_count: int = 0
    nodes_by_type: Dict[str, int] = Field(default_factory=dict)
    edges_by_type: Dict[str, int] = Field(default_factory=dict)
    max_depth: int = 0  # Longest chain from attribute to value
    orphan_count: int = 0  # Nodes with no edges
    properties: Dict[str, Any] = Field(
        default_factory=dict
    )  # Additional state properties
    coverage_state: Optional[CoverageState] = Field(default=None)  # Element coverage

    def get_phase(self) -> str:
        """Get current interview phase."""
        return self.properties.get("phase", "exploratory")

    def set_phase(self, phase: str) -> None:
        """Transition to a new phase.

        Args:
            phase: New phase ('exploratory', 'focused', or 'closing')
        """
        self.properties["phase"] = phase

    def add_strategy_used(self, strategy_id: str) -> None:
        """Record a strategy selection in history for diversity tracking.

        This maintains a list of recently used strategies so the
        StrategyDiversityScorer can penalize repetitive questioning
        patterns and encourage interview variety.

        Args:
            strategy_id: The strategy that was selected
                (e.g., 'broaden', 'deepen', 'cover_element', 'close')
        """
        if "strategy_history" not in self.properties:
            self.properties["strategy_history"] = []
        self.properties["strategy_history"].append(strategy_id)
