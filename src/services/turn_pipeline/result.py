"""
Result object for turn processing pipeline.

ADR-008 Phase 3: TurnResult is returned by the pipeline.
Phase 3 (Dual-Graph Integration), bead 0nl3: Added canonical_graph and graph_comparison fields.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List


@dataclass
class TurnResult:
    """
    Result of processing a single turn.

    Matches PRD Section 8.6 response structure.

    Note: strategy_selected is Optional to support partial pipeline execution
    (e.g., tests that only run early stages). In full pipeline execution,
    it will always be set after StrategySelectionStage (Stage 6).

    Phase 3 (Dual-Graph Integration): Added canonical_graph and graph_comparison
    for dual-graph architecture observability.
    """

    turn_number: int
    extracted: dict  # concepts, relationships
    graph_state: dict  # node_count, edge_count, depth_achieved
    scoring: dict  # strategy_id, score, reasoning (Phase 3)
    strategy_selected: Optional[str]
    next_question: str
    should_continue: bool
    latency_ms: int = 0
    # Phase 6: Methodology-based signal detection observability
    signals: Optional[Dict[str, Any]] = None  # Raw methodology signals from signal pools
    strategy_alternatives: Optional[List[Dict[str, Any]]] = None  # Alternative strategies with scores
    # Termination reason (populated by ContinuationStage when should_continue=False)
    termination_reason: Optional[str] = None  # e.g., "max_turns_reached", "graph_saturated", "close_strategy"
    # Phase 3 (Dual-Graph Integration), bead 0nl3: Dual-graph output fields
    canonical_graph: Optional[Dict[str, Any]] = None  # {slots, edges, metrics}
    graph_comparison: Optional[Dict[str, Any]] = None  # {node_reduction_pct, edge_aggregation_ratio, orphan_improvement_pct}
