"""NodeState domain model for per-node engagement tracking across interviews.

This module provides NodeState dataclass that tracks individual node behavior
patterns throughout an interview session. Used by NodeStateTracker service
to maintain yield history, focus streaks, and strategy effectiveness.

Core Metrics:
    - Engagement: focus_count, current_focus_streak, turns_since_last_focus
    - Yield: yield_count, yield_rate, turns_since_last_yield
    - Quality: all_response_depths for shallow/deep classification
    - Connectivity: edge counts and connected_node_ids for orphan detection
    - Strategy: strategy_usage_count for repetition detection

Consumers:
    - NodeExhaustedSignal (graph.node.exhausted)
    - StrategyDiversityScorer (temporal.strategy_repetition_count)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set


@dataclass
class NodeState:
    """Per-node persistent state tracking for exhaustion and yield scoring.

    Tracks engagement patterns, yield history, and response quality for each
    knowledge graph node throughout an interview session. Updated by
    NodeStateTracker after each graph mutation.

    Key Metrics for Signal Detection:
        - focus_count + current_focus_streak: Detects over-focus patterns
        - turns_since_last_yield: Primary exhaustion signal (threshold-based)
        - yield_rate: Quality ratio (0.0 = exhausted, 1.0 = high yield)
        - is_orphan property: Identifies unconnected nodes for coverage signals

    State Update Cycle:
        1. Node selected as focus: increment focus_count, update last_focus_turn
        2. Graph mutation from node: increment yield_count, update last_yield_turn
        3. Strategy used: update strategy_usage_count, track consecutive_same_strategy
    """

    # Basic info
    node_id: str
    label: str
    created_at_turn: int
    depth: int
    node_type: str
    is_terminal: bool = False
    level: int = 0

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
        """Detect orphan nodes with no incoming or outgoing edges.

        Orphan nodes indicate incomplete coverage - concepts mentioned but
        not yet explored or connected to interview structure.

        Returns:
            True if node has zero edges (incoming + outgoing), False otherwise

        Used by:
            - OrphanCountSignal (graph.orphan_count)
            - Coverage scoring for breadth strategies
        """
        return (self.edge_count_incoming + self.edge_count_outgoing) == 0
