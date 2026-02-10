"""
Shared signal pools for methodology modules.

Signals are grouped by data source:
- graph: Derived from knowledge graph snapshot (O(1), cached on graph update)
- llm: Derived from LLM analysis of response (high cost, computed fresh each response)
- temporal: Derived from conversation history (O(1), cached on turn start)
- meta: Composite signals that depend on multiple signal sources

Example usage:
    from methodologies.signals.graph import GraphNodeCountSignal
    detector = GraphNodeCountSignal()
    signals = await detector.detect(context, graph_state, response_text)
    # Returns: {"graph.node_count": 5}
"""

# Base classes
from src.methodologies.signals.common import SignalDetector

# Graph signals
from src.methodologies.signals.graph import (
    GraphNodeCountSignal,
    GraphEdgeCountSignal,
    OrphanCountSignal,
    GraphMaxDepthSignal,
    GraphAvgDepthSignal,
    DepthByElementSignal,
    ChainCompletionSignal,
)

# LLM signals (fresh every response)
from src.methodologies.signals.llm import (
    ResponseDepthSignal,
    SentimentSignal,
    UncertaintySignal,
    AmbiguitySignal,
)

# Temporal signals (conversation history)
from src.methodologies.signals.temporal import (
    StrategyRepetitionCountSignal,
    TurnsSinceChangeSignal,
)

# Meta signals (composite)
from src.methodologies.signals.meta import InterviewProgressSignal

__all__ = [
    # Base
    "SignalDetector",
    # Graph
    "GraphNodeCountSignal",
    "GraphEdgeCountSignal",
    "OrphanCountSignal",
    "GraphMaxDepthSignal",
    "GraphAvgDepthSignal",
    "DepthByElementSignal",
    "ChainCompletionSignal",
    # LLM
    "ResponseDepthSignal",
    "SentimentSignal",
    "UncertaintySignal",
    "AmbiguitySignal",
    # Temporal
    "StrategyRepetitionCountSignal",
    "TurnsSinceChangeSignal",
    # Meta
    "InterviewProgressSignal",
]
