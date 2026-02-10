"""
Graph-derived signals (O(1), cached on graph update).

These signals are derived from the knowledge graph snapshot and are
refreshed after each graph update (PER_TURN). They are free or low cost.

Example signals:
- GraphNodeCountSignal: Number of nodes in the graph
- GraphMaxDepthSignal: Maximum chain depth in the graph
- ChainCompletionSignal: Checks if chains have terminal values
- NodeExhaustedSignal: Per-node exhaustion detection

Also includes canonical_structure module for canonical graph signals
that operate on deduplicated graph for stable metrics.
"""

from src.methodologies.signals.graph.canonical_structure import (
    CanonicalConceptCountSignal,
    CanonicalEdgeDensitySignal,
    CanonicalExhaustionScoreSignal,
)
from src.methodologies.signals.graph.structure import (
    GraphNodeCountSignal,
    GraphEdgeCountSignal,
    OrphanCountSignal,
)
from src.methodologies.signals.graph.depth import (
    GraphMaxDepthSignal,
    GraphAvgDepthSignal,
    DepthByElementSignal,
)
from src.methodologies.signals.graph.node_exhaustion import (
    NodeExhaustedSignal,
    NodeExhaustionScoreSignal,
    NodeYieldStagnationSignal,
)
from src.methodologies.signals.graph.node_engagement import (
    NodeFocusStreakSignal,
    NodeIsCurrentFocusSignal,
    NodeRecencyScoreSignal,
)
from src.methodologies.signals.graph.node_relationships import (
    NodeIsOrphanSignal,
    NodeEdgeCountSignal,
    NodeHasOutgoingSignal,
)
from src.methodologies.signals.graph.chain_completion import (
    ChainCompletionSignal,
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
]
