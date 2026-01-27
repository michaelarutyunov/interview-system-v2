"""Pipeline stage contracts (ADR-010 Part 1).

Formalized Pydantic models for stage inputs and outputs to provide
type safety and runtime validation for the turn processing pipeline.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, model_validator

from src.domain.models.knowledge_graph import GraphState, KGNode


class ContextLoadingOutput(BaseModel):
    """Contract: ContextLoadingStage output (Stage 1).

    Stage 1 loads session metadata, conversation history, and graph state.
    """

    # Session metadata
    methodology: str = Field(
        description="Methodology identifier (e.g., 'means_end_chain')"
    )
    concept_id: str = Field(description="Concept identifier")
    concept_name: str = Field(description="Human-readable concept name")
    turn_number: int = Field(ge=0, description="Current turn number (0-indexed)")
    mode: str = Field(description="Interview mode (e.g., 'coverage', 'depth')")
    max_turns: int = Field(ge=1, description="Maximum number of turns")

    # Conversation history
    recent_utterances: List[Dict[str, str]] = Field(
        default_factory=list, description="Recent conversation turns"
    )
    strategy_history: List[str] = Field(
        default_factory=list, description="History of strategies used"
    )

    # Graph state
    graph_state: GraphState = Field(description="Current knowledge graph state")
    recent_nodes: List[KGNode] = Field(
        default_factory=list, description="Recently added graph nodes"
    )


class UtteranceSavingOutput(BaseModel):
    """Contract: UtteranceSavingStage output (Stage 2).

    Stage 2 persists user input to database.
    """

    turn_number: int = Field(ge=0, description="Turn number for this utterance")
    user_utterance_id: str = Field(description="Database ID of saved utterance")


class StateComputationOutput(BaseModel):
    """Contract: StateComputationStage output (Stage 5).

    Stage 5 refreshes graph state metrics after updates.

    ADR-010: Added computed_at for freshness tracking to prevent
    stale state bug where coverage_state from Stage 1 was used in Stage 6.
    """

    graph_state: GraphState = Field(description="Refreshed knowledge graph state")
    recent_nodes: List[KGNode] = Field(
        default_factory=list, description="Refreshed list of recent nodes"
    )
    computed_at: datetime = Field(
        description="When state was computed (for freshness validation)"
    )

    @model_validator(mode="after")
    def set_computed_at_if_missing(self) -> "StateComputationOutput":
        """Set computed_at to current time if not provided."""
        if self.computed_at is None:  # type: ignore
            self.computed_at = datetime.now(timezone.utc)
        return self


class StrategySelectionInput(BaseModel):
    """Contract: StrategySelectionStage input (Stage 6).

    Stage 6 selects questioning strategy using two-tier scoring.

    ADR-010: Added freshness validation to prevent stale state bug.
    """

    # Graph state (must be fresh!)
    graph_state: GraphState = Field(description="Current knowledge graph state")
    recent_nodes: List[KGNode] = Field(default_factory=list, description="Recent nodes")

    # Extraction results
    extraction: Any = Field(
        description="ExtractionResult with timestamp for freshness check"
    )

    # Context
    conversation_history: List[Dict[str, str]] = Field(
        default_factory=list, description="Conversation history"
    )
    turn_number: int = Field(ge=0, description="Current turn number")
    mode: str = Field(description="Interview mode")

    # Freshness tracking
    computed_at: datetime = Field(
        description="When graph_state was computed (for freshness validation)"
    )

    @model_validator(mode="after")
    def verify_state_freshness(self) -> "StrategySelectionInput":
        """Ensure state isn't stale relative to extraction.

        ADR-010: This validation prevents the stale coverage_state bug where
        StateComputation output from before extraction was used, causing wrong
        strategy selection.
        """
        if hasattr(self.extraction, "timestamp"):
            extraction_time = self.extraction.timestamp
            if self.computed_at < extraction_time:
                time_diff = extraction_time - self.computed_at
                raise ValueError(
                    f"State is stale! Computed {time_diff.total_seconds():.1f}s "
                    "before extraction. StrategySelection requires fresh state "
                    "from StateComputation that was computed AFTER extraction."
                )
        return self


class StrategySelectionOutput(BaseModel):
    """Contract: StrategySelectionStage output (Stage 6).

    Stage 6 produces selected strategy and focus for question generation.
    """

    strategy: str = Field(
        description="Selected strategy ID (e.g., 'deepen', 'broaden')"
    )
    focus: Optional[Dict[str, Any]] = Field(
        default=None, description="Focus target (node_id, element_id, or description)"
    )
    selected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When strategy was selected (for debugging)",
    )


# =============================================================================
# ADR-010 Phase 2: Strategy Selection Result Schema
# =============================================================================

"""
Enhanced type-safe models for strategy selection results.

Replaces dataclass-based SelectionResult with Pydantic models that provide:
- Full type safety (no more Dict[str, Any])
- Runtime validation
- Better serialization for debugging/analysis
- Proper element_id support for cover_element strategy
- Aggregate statistics for observability
"""


class Focus(BaseModel):
    """A focus target for strategy execution.

    ADR-010 Phase 2: Enhanced focus model with element_id support.
    The element_id field is CRITICAL for cover_element strategy to work correctly.
    """

    focus_type: str = Field(
        description="Type of focus: breadth_exploration, depth_exploration, element_coverage, etc."
    )
    focus_description: str = Field(
        description="Human-readable description of what to focus on"
    )
    node_id: Optional[str] = Field(
        default=None, description="Graph node ID if focus is on a specific node"
    )
    element_id: Optional[int] = Field(
        default=None,
        description="CRITICAL: Coverage element ID for cover_element strategy",
    )


class VetoResult(BaseModel):
    """Result from a Tier 1 scorer (hard constraint).

    Tier 1 scorers return boolean veto decisions with reasoning.
    """

    scorer_id: str = Field(
        description="Identifier of the scorer (e.g., 'KnowledgeCeilingScorer')"
    )
    is_veto: bool = Field(description="Whether this scorer vetoed the candidate")
    reasoning: str = Field(
        description="Human-readable explanation of the veto decision"
    )
    signals: Dict[str, Any] = Field(
        default_factory=dict, description="Raw signals used for veto decision"
    )


class WeightedResult(BaseModel):
    """Result from a Tier 2 scorer (weighted additive).

    Tier 2 scorers return numeric scores with weights and contributions.
    """

    scorer_id: str = Field(
        description="Identifier of the scorer (e.g., 'CoverageGapScorer')"
    )
    raw_score: float = Field(
        ge=0.0, description="Raw score from scorer (typically 0-2 range, 1.0 = neutral)"
    )
    weight: float = Field(ge=0.0, description="Weight of this scorer in the total sum")
    contribution: float = Field(
        ge=0.0, description="Contribution to final score (weight × raw_score)"
    )
    reasoning: str = Field(description="Human-readable explanation of the score")
    signals: Dict[str, Any] = Field(
        default_factory=dict, description="Raw signals used for scoring"
    )


class ScoredStrategy(BaseModel):
    """A strategy+focus combination with full scoring breakdown.

    Represents one candidate in the strategy selection process.
    """

    # Strategy identification
    strategy_id: str = Field(
        description="Strategy identifier (e.g., 'deepen', 'broaden')"
    )
    strategy_name: str = Field(description="Human-readable strategy name")

    # Focus
    focus: Focus = Field(description="Focus target for this strategy")

    # Tier 1 results (hard constraints)
    tier1_results: List[VetoResult] = Field(
        default_factory=list, description="Results from Tier 1 veto scorers"
    )

    # Tier 2 results (weighted scoring)
    tier2_results: List[WeightedResult] = Field(
        default_factory=list, description="Results from Tier 2 weighted scorers"
    )

    # Scores
    tier2_score: float = Field(
        ge=0.0, description="Sum of weighted Tier 2 scores (BEFORE phase multiplier)"
    )
    final_score: float = Field(
        ge=0.0, description="Final score AFTER applying phase multiplier"
    )

    # Selection status
    is_selected: bool = Field(description="Whether this strategy was selected")
    vetoed_by: Optional[str] = Field(
        default=None, description="Scorer ID that vetoed this candidate, if any"
    )

    # Reasoning
    reasoning: str = Field(description="Human-readable explanation of why this score")


class StrategySelectionResult(BaseModel):
    """Complete result from strategy selection process.

    ADR-010 Phase 2: Type-safe replacement for dataclass SelectionResult.

    This model provides:
    - Session context (session_id, turn_number, phase)
    - Selected strategy with full scoring breakdown
    - Alternative strategies with their scores
    - Aggregate statistics (total_candidates, vetoed_count)
    - Phase multiplier information for debugging
    """

    # Session context
    session_id: str = Field(description="Session identifier")
    turn_number: int = Field(ge=0, description="Turn number when selection was made")

    # Phase information
    phase: str = Field(description="Interview phase: exploratory, focused, or closing")
    phase_multiplier: float = Field(
        ge=0.0, description="Phase multiplier applied to scores"
    )

    # Selected strategy
    selected_strategy: ScoredStrategy = Field(
        description="The winning strategy with full scoring breakdown"
    )

    # Alternatives
    alternatives: List[ScoredStrategy] = Field(
        default_factory=list,
        description="All other evaluated strategies (runner-ups)",
    )

    # Aggregate statistics
    total_candidates: int = Field(
        ge=0, description="Total number of (strategy, focus) candidates evaluated"
    )
    vetoed_count: int = Field(
        ge=0, description="How many candidates were vetoed by Tier 1 scorers"
    )
