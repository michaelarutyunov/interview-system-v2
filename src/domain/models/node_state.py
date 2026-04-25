"""NodeState domain model for per-node engagement tracking across interviews.

Frozen Pydantic models — all mutation returns a new instance via model_copy().
Consumed by NodeStateTracker (immutable) and node signal detectors (read-only).

Core Metrics:
    - Engagement: focus_count, current_focus_streak, turns_since_last_focus
    - Yield: yield_count, yield_rate, turns_since_last_yield
    - Quality: all_response_depths for shallow/deep classification
    - Connectivity: edge counts and connected_node_ids for orphan detection
    - Strategy: strategy_usage_count for repetition detection

Consumers:
    - NodeExhaustionScoreSignal (convgraph.node.exhaustion)
    - StrategyDiversityScorer (temporal.strategy_repetition_count)
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# Per-concept elaboration score → categorical response_depth bins (spec §C.5.1)
_ELAB_CUT_SURFACE = 0.125
_ELAB_CUT_SHALLOW = 0.375
_ELAB_CUT_MODERATE = 0.625


def _elaboration_to_depth(elaboration: float) -> str:
    """Bin normalized per-concept elaboration score to categorical response_depth."""
    if elaboration < _ELAB_CUT_SURFACE:
        return "surface"
    if elaboration < _ELAB_CUT_SHALLOW:
        return "shallow"
    if elaboration < _ELAB_CUT_MODERATE:
        return "moderate"
    return "deep"


class NodeQualityHistory(BaseModel):
    """Per-node LLM quality signal history (per-concept ratings from batch detector).

    Populated via NodeStateTracker.append_quality() when a concept extracted from
    the user's response is mapped back to a graph node via concept_to_node_id.
    Consumed by NodeElaborationSignal / NodeChargeSignal / NodeHasQualityDataSignal.
    """

    model_config = ConfigDict(frozen=True)

    elaboration_scores: tuple[float, ...] = ()
    charge_scores: tuple[float, ...] = ()

    def with_scores(self, elaboration: float, charge: float) -> NodeQualityHistory:
        """Return new history with scores appended."""
        return self.model_copy(update={
            "elaboration_scores": self.elaboration_scores + (elaboration,),
            "charge_scores": self.charge_scores + (charge,),
        })

    def merged_with(self, other: NodeQualityHistory) -> NodeQualityHistory:
        """Return merged history when two surface nodes collapse to one canonical slot."""
        return NodeQualityHistory(
            elaboration_scores=self.elaboration_scores + other.elaboration_scores,
            charge_scores=self.charge_scores + other.charge_scores,
        )


class NodeState(BaseModel):
    """Per-node persistent state tracking for exhaustion and yield scoring.

    Tracks engagement patterns, yield history, and response quality for each
    knowledge graph node throughout an interview session. Updated by
    NodeStateTracker after each graph mutation.

    All fields are immutable. Use with_* methods to produce updated copies.

    Key Metrics for Signal Detection:
        - focus_count + current_focus_streak: Detects over-focus patterns
        - turns_since_last_yield: Primary exhaustion signal (threshold-based)
        - yield_rate: Quality ratio (0.0 = exhausted, 1.0 = high yield)
        - is_orphan property: Identifies unconnected nodes for coverage signals

    State Update Cycle:
        1. Node selected as focus: tracker calls with_focus() on focused node,
           tick_no_focus() on all others
        2. Graph mutation from node: tracker calls with_yield()
        3. LLM bridge: tracker calls with_quality() per concept
    """

    model_config = ConfigDict(frozen=True)

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
    all_response_depths: tuple[str, ...] = ()
    quality_history: NodeQualityHistory = Field(default_factory=NodeQualityHistory)

    # Relationships
    connected_node_ids: frozenset[str] = Field(default_factory=frozenset)
    edge_count_outgoing: int = 0
    edge_count_incoming: int = 0

    # Strategy usage
    strategy_usage_count: dict[str, int] = Field(default_factory=dict)
    last_strategy_used: Optional[str] = None
    consecutive_same_strategy: int = 0

    @property
    def is_orphan(self) -> bool:
        """True if node has zero edges — unconnected concept needing exploration."""
        return (self.edge_count_incoming + self.edge_count_outgoing) == 0

    # ------------------------------------------------------------------
    # Functional update methods — each returns a new NodeState instance
    # ------------------------------------------------------------------

    def with_focus(self, *, turn_number: int, strategy: str, is_same_as_previous: bool) -> NodeState:
        """Return new NodeState with focus metrics updated (the node that was focused)."""
        new_streak = (self.current_focus_streak + 1) if is_same_as_previous else 1
        new_consecutive = (self.consecutive_same_strategy + 1) if self.last_strategy_used == strategy else 1
        new_strategy_count = {**self.strategy_usage_count, strategy: self.strategy_usage_count.get(strategy, 0) + 1}
        return self.model_copy(update={
            "focus_count": self.focus_count + 1,
            "last_focus_turn": turn_number,
            "turns_since_last_focus": 0,
            "current_focus_streak": new_streak,
            "turns_since_last_yield": self.turns_since_last_yield + 1,
            "strategy_usage_count": new_strategy_count,
            "last_strategy_used": strategy,
            "consecutive_same_strategy": new_consecutive,
        })

    def tick_no_focus(self) -> NodeState:
        """Return new NodeState with time-ticks applied (all nodes that were NOT focused)."""
        return self.model_copy(update={
            "turns_since_last_focus": self.turns_since_last_focus + 1,
            "current_focus_streak": 0,
            "turns_since_last_yield": self.turns_since_last_yield + 1,
        })

    def with_yield(self, *, turn_number: int) -> NodeState:
        """Return new NodeState with yield recorded."""
        new_yield_count = self.yield_count + 1
        return self.model_copy(update={
            "last_yield_turn": turn_number,
            "turns_since_last_yield": 0,
            "yield_count": new_yield_count,
            "yield_rate": new_yield_count / max(self.focus_count, 1),
        })

    def with_quality(self, *, elaboration: float, charge: float) -> NodeState:
        """Return new NodeState with LLM quality scores appended."""
        depth = _elaboration_to_depth(elaboration)
        return self.model_copy(update={
            "quality_history": self.quality_history.with_scores(elaboration, charge),
            "all_response_depths": self.all_response_depths + (depth,),
        })

    def with_edge_delta(self, *, outgoing_delta: int, incoming_delta: int) -> NodeState:
        """Return new NodeState with edge counts updated (clamped to zero)."""
        return self.model_copy(update={
            "edge_count_outgoing": max(0, self.edge_count_outgoing + outgoing_delta),
            "edge_count_incoming": max(0, self.edge_count_incoming + incoming_delta),
        })

    def merged_with(self, other: NodeState) -> NodeState:
        """Return merged NodeState when two surface nodes collapse to the same canonical slot."""
        merged_strategy_count = {**self.strategy_usage_count}
        for strat, count in other.strategy_usage_count.items():
            merged_strategy_count[strat] = merged_strategy_count.get(strat, 0) + count

        # Take most-recent focus timing
        if other.last_focus_turn is not None and (
            self.last_focus_turn is None or other.last_focus_turn > self.last_focus_turn
        ):
            focus_turn = other.last_focus_turn
            focus_streak = other.current_focus_streak
            turns_since_focus = other.turns_since_last_focus
        else:
            focus_turn = self.last_focus_turn
            focus_streak = self.current_focus_streak
            turns_since_focus = self.turns_since_last_focus

        # Take most-recent yield timing
        if other.last_yield_turn is not None and (
            self.last_yield_turn is None or other.last_yield_turn > self.last_yield_turn
        ):
            yield_turn = other.last_yield_turn
            turns_since_yield = other.turns_since_last_yield
        else:
            yield_turn = self.last_yield_turn
            turns_since_yield = self.turns_since_last_yield

        new_focus_count = self.focus_count + other.focus_count
        new_yield_count = self.yield_count + other.yield_count

        return self.model_copy(update={
            "focus_count": new_focus_count,
            "last_focus_turn": focus_turn,
            "turns_since_last_focus": turns_since_focus,
            "current_focus_streak": focus_streak,
            "yield_count": new_yield_count,
            "yield_rate": new_yield_count / max(new_focus_count, 1),
            "last_yield_turn": yield_turn,
            "turns_since_last_yield": turns_since_yield,
            "all_response_depths": self.all_response_depths + other.all_response_depths,
            "quality_history": self.quality_history.merged_with(other.quality_history),
            "connected_node_ids": self.connected_node_ids | other.connected_node_ids,
            "edge_count_outgoing": self.edge_count_outgoing + other.edge_count_outgoing,
            "edge_count_incoming": self.edge_count_incoming + other.edge_count_incoming,
            "strategy_usage_count": merged_strategy_count,
        })
