"""
Result object for turn processing pipeline.

Returned by the pipeline after all stages complete, containing extraction
results, graph state, scoring data, and the generated response.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class TurnResult:
    """Result of processing a single turn.

    Contains extraction results, graph state, scoring data, next question,
    and continuation status.

    Matches PRD Section 8.6 response structure.
    """

    turn_number: int
    extracted: dict  # concepts, relationships
    graph_state: dict  # node_count, edge_count, depth_achieved
    scoring: dict  # strategy_id, score, reasoning
    strategy_selected: str
    next_question: str
    should_continue: bool
    latency_ms: int = 0
    # Methodology-based signal detection observability
    signals: Optional[Dict[str, Any]] = (
        None  # Raw methodology signals from signal pools
    )
    strategy_alternatives: Optional[List[Dict[str, Any]]] = (
        None  # Alternative strategies with scores
    )
    # Termination reason (populated by ContinuationStage when should_continue=False)
    termination_reason: Optional[str] = (
        None  # e.g., "max_turns_reached", "graph_saturated", "close_strategy"
    )
    # Dual-graph output fields
    canonical_graph: Optional[Dict[str, Any]] = None  # {slots, edges, metrics}
    graph_comparison: Optional[Dict[str, Any]] = (
        None  # {node_reduction_pct, edge_aggregation_ratio}
    )
    # Per-turn graph changes for simulation observability
    nodes_added: List[Dict[str, Any]] = field(
        default_factory=list
    )  # [{"id": ..., "label": ..., "node_type": ...}]
    edges_added: List[Dict[str, Any]] = field(
        default_factory=list
    )  # [{"source_node_id": ..., "target_node_id": ..., "edge_type": ...}]
    # Saturation tracking metrics from StateComputationStage (Stage 5)
    saturation_metrics: Optional[Dict[str, Any]] = None
    # Per-node signals from StrategySelectionStage (Stage 6)
    node_signals: Optional[Dict[str, Dict[str, Any]]] = None
