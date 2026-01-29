"""
NodeState domain model for tracking per-node state across interview sessions.

This module provides the NodeState dataclass which maintains persistent state
for each knowledge graph node throughout an interview session.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set


@dataclass
class NodeState:
    """
    Persistent state tracked for each node across the interview session.

    NodeState tracks engagement patterns, yield history, response quality,
    relationships, and strategy usage for each knowledge graph node.

    Attributes:
        node_id: Unique identifier for the node
        label: Human-readable label for the node
        created_at_turn: Turn number when node was created
        depth: Depth level in the knowledge graph (0 = root)

        # Engagement metrics
        focus_count: Number of times this node has been selected as focus
        last_focus_turn: Most recent turn number when this node was focused
        turns_since_last_focus: Turns elapsed since last focus
        current_focus_streak: Consecutive turns this node has been focus

        # Yield metrics
        last_yield_turn: Most recent turn when node produced graph changes
        turns_since_last_yield: Turns elapsed since last yield
        yield_count: Total number of times node has yielded (produced changes)
        yield_rate: Ratio of yield_count to focus_count (0.0 - 1.0)

        # Response quality
        all_response_depths: List of all response depths (surface/shallow/deep)

        # Relationships
        connected_node_ids: Set of node IDs directly connected to this node
        edge_count_outgoing: Number of edges from this node to others
        edge_count_incoming: Number of edges from others to this node

        # Strategy usage
        strategy_usage_count: Dict mapping strategy name to usage count
        last_strategy_used: Most recently used strategy on this node
        consecutive_same_strategy: Consecutive times same strategy was used
    """

    # Basic info
    node_id: str
    label: str
    created_at_turn: int
    depth: int

    # Engagement metrics
    focus_count: int = 0
    last_focus_turn: Optional[int] = None
    turns_since_last_focus: int = 0
    current_focus_streak: int = 0

    # Yield metrics
    last_yield_turn: Optional[int] = None
    turns_since_last_yield: int = 0
    yield_count: int = 0
    yield_rate: float = 0.0

    # Response quality
    all_response_depths: List[str] = field(default_factory=list)

    # Relationships
    connected_node_ids: Set[str] = field(default_factory=set)
    edge_count_outgoing: int = 0
    edge_count_incoming: int = 0

    # Strategy usage
    strategy_usage_count: Dict[str, int] = field(default_factory=dict)
    last_strategy_used: Optional[str] = None
    consecutive_same_strategy: int = 0

    @property
    def is_orphan(self) -> bool:
        """
        Check if this node is an orphan (no edges).

        A node is considered an orphan if it has no incoming or outgoing edges.

        Returns:
            True if node has no edges, False otherwise
        """
        return (self.edge_count_incoming + self.edge_count_outgoing) == 0
