"""Shared signal pools for methodology modules.

Signals are grouped by data source:
- graph: Derived from knowledge graph snapshot (O(1)), cached on graph update
- llm: Derived from LLM analysis of response (high cost, computed fresh each response)
- session: Session-level patterns derived from conversation history (O(1)), cached on turn start
- meta: Composite signals that depend on multiple signal sources

All signals are auto-registered via __init_subclass__ in SignalDetector base class.
Importing from this module triggers registration of all signals.
"""

# Graph signals - imports all graph-level signals via graph/__init__.py
from src.signals.graph import (
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
    # Node-level graph signals
    NodeExhaustedSignal,
    NodeExhaustionScoreSignal,
    NodeYieldStagnationSignal,
    NodeFocusStreakSignal,
    NodeIsCurrentFocusSignal,
)

# LLM signals - imports all LLM signals via llm/__init__.py
from src.signals.llm import (
    ResponseDepthSignal,
    SpecificitySignal,
    CertaintySignal,
    ValenceSignal,
    EngagementSignal,
)

# LLM batch detector
from src.signals.llm.batch_detector import LLMBatchDetector

# Base classes
from src.signals.signal_base import SignalDetector
from src.signals.graph.node_base import NodeSignalDetector
from src.signals.llm.llm_signal_base import BaseLLMSignal

# Session signals - imports all session signals via session/__init__.py
from src.signals.session import (
    StrategyRepetitionCountSignal,
    TurnsSinceChangeSignal,
    NodeStrategyRepetitionSignal,
    GlobalResponseTrendSignal,
)

# Meta signals - imports all meta signals via meta/__init__.py
from src.signals.meta import (
    InterviewProgressSignal,
    InterviewPhaseSignal,
    NodeOpportunitySignal,
)

__all__ = [
    # Base classes
    "SignalDetector",
    "NodeSignalDetector",
    "BaseLLMSignal",
    # Graph signals
    "GraphNodeCountSignal",
    "GraphEdgeCountSignal",
    "OrphanCountSignal",
    "GraphMaxDepthSignal",
    "GraphAvgDepthSignal",
    "DepthByElementSignal",
    "ChainCompletionSignal",
    "CanonicalConceptCountSignal",
    "CanonicalEdgeDensitySignal",
    "CanonicalExhaustionScoreSignal",
    # Node-level graph signals
    "NodeExhaustedSignal",
    "NodeExhaustionScoreSignal",
    "NodeYieldStagnationSignal",
    "NodeFocusStreakSignal",
    "NodeIsCurrentFocusSignal",
    # LLM signals
    "ResponseDepthSignal",
    "SpecificitySignal",
    "CertaintySignal",
    "ValenceSignal",
    "EngagementSignal",
    # LLM batch detector
    "LLMBatchDetector",
    # Session signals
    "StrategyRepetitionCountSignal",
    "TurnsSinceChangeSignal",
    "NodeStrategyRepetitionSignal",
    "GlobalResponseTrendSignal",
    # Meta signals
    "InterviewProgressSignal",
    "InterviewPhaseSignal",
    "NodeOpportunitySignal",
]
