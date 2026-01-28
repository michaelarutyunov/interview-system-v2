"""
Graph-derived signals (O(1), cached on graph update).

These signals are derived from the knowledge graph snapshot and are
refreshed after each graph update (PER_TURN). They are free or low cost.

Example signals:
- GraphNodeCountSignal: Number of nodes in the graph
- GraphMaxDepthSignal: Maximum chain depth in the graph
- CoverageBreadthSignal: How well different attribute types are covered
"""

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
from src.methodologies.signals.graph.coverage import (
    CoverageBreadthSignal,
    MissingTerminalValueSignal,
)

__all__ = [
    # Structure
    "GraphNodeCountSignal",
    "GraphEdgeCountSignal",
    "OrphanCountSignal",
    # Depth
    "GraphMaxDepthSignal",
    "GraphAvgDepthSignal",
    "DepthByElementSignal",
    # Coverage
    "CoverageBreadthSignal",
    "MissingTerminalValueSignal",
]
