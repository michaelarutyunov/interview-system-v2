"""
Graph-derived signals (O(1), cached on graph update).

These signals are derived from the knowledge graph snapshot and are
refreshed after each graph update (PER_TURN). They are free or low cost.

Consolidated module: exports from graph_signals.py and node_signals.py
"""

# Graph signals (consolidated)
from src.signals.graph.graph_signals import (
    GraphNodeCountSignal,
    GraphEdgeCountSignal,
    OrphanCountSignal,
    GraphMaxDepthSignal,
    GraphAvgDepthSignal,
    DepthByElementSignal,
    ChainCompletionSignal,
    CanonicalConceptCountSignal,
    CanonicalEdgeDensitySignal,
    CanonicalExhaustionScoreSignal,
)

# Node-level signals (consolidated)
from src.signals.graph.node_signals import (
    NodeExhaustedSignal,
    NodeExhaustionScoreSignal,
    NodeYieldStagnationSignal,
    NodeFocusStreakSignal,
    NodeIsCurrentFocusSignal,
    NodeRecencyScoreSignal,
    NodeIsOrphanSignal,
    NodeEdgeCountSignal,
    NodeHasOutgoingSignal,
    NodeTypePrioritySignal,
)

__all__ = [
    # Canonical structure
    "CanonicalConceptCountSignal",
    "CanonicalEdgeDensitySignal",
    "CanonicalExhaustionScoreSignal",
    # Structure
    "GraphNodeCountSignal",
    "GraphEdgeCountSignal",
    "OrphanCountSignal",
    # Depth
    "GraphMaxDepthSignal",
    "GraphAvgDepthSignal",
    "DepthByElementSignal",
    # Chain completion
    "ChainCompletionSignal",
    # Node-level: Exhaustion
    "NodeExhaustedSignal",
    "NodeExhaustionScoreSignal",
    "NodeYieldStagnationSignal",
    # Node-level: Engagement
    "NodeFocusStreakSignal",
    "NodeIsCurrentFocusSignal",
    "NodeRecencyScoreSignal",
    # Node-level: Relationships
    "NodeIsOrphanSignal",
    "NodeEdgeCountSignal",
    "NodeHasOutgoingSignal",
    # Node-level: Differentiation
    "NodeTypePrioritySignal",
]
