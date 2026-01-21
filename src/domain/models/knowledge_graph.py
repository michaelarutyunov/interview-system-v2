"""Domain models for knowledge graph nodes and edges."""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class NodeType(str, Enum):
    """Valid node types for Means-End Chain methodology."""
    ATTRIBUTE = "attribute"
    FUNCTIONAL_CONSEQUENCE = "functional_consequence"
    PSYCHOSOCIAL_CONSEQUENCE = "psychosocial_consequence"
    INSTRUMENTAL_VALUE = "instrumental_value"
    TERMINAL_VALUE = "terminal_value"


class EdgeType(str, Enum):
    """Valid edge types."""
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
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
    superseded_by: Optional[str] = None  # Node ID that supersedes this one (for REVISES)

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
    recorded_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"from_attributes": True}


class GraphState(BaseModel):
    """Current state of the knowledge graph for a session."""
    node_count: int = 0
    edge_count: int = 0
    nodes_by_type: Dict[str, int] = Field(default_factory=dict)
    edges_by_type: Dict[str, int] = Field(default_factory=dict)
    max_depth: int = 0  # Longest chain from attribute to value
    orphan_count: int = 0  # Nodes with no edges
    properties: Dict[str, Any] = Field(default_factory=dict)  # Additional state properties
