"""Pipeline stage contracts (ADR-010 Part 1).

Formalized Pydantic models for stage inputs and outputs to provide
type safety and runtime validation for the turn processing pipeline.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, model_validator

from src.domain.models.knowledge_graph import GraphState, KGNode, SaturationMetrics
from src.domain.models.utterance import Utterance
from src.domain.models.extraction import ExtractionResult


class ContextLoadingOutput(BaseModel):
    """Contract: ContextLoadingStage output (Stage 1).

    Stage 1 loads session metadata and conversation history.

    Note: graph_state and recent_nodes are NOT loaded here - they come from
    StateComputationStage (Stage 5) after graph updates. Stages 2-4 should
    not access these properties via context.graph_state or context.recent_nodes.
    """

    # Session metadata
    methodology: str = Field(
        description="Methodology identifier (e.g., 'means_end_chain')"
    )
    concept_id: str = Field(description="Concept identifier")
    concept_name: str = Field(description="Human-readable concept name")
    turn_number: int = Field(ge=0, description="Current turn number (0-indexed)")
    mode: str = Field(description="Interview mode (e.g., 'exploratory')")
    max_turns: int = Field(ge=1, description="Maximum number of turns")

    # Conversation history
    recent_utterances: List[Dict[str, Any]] = Field(
        default_factory=list, description="Recent conversation turns"
    )
    strategy_history: List[str] = Field(
        default_factory=list, description="History of strategies used"
    )


class UtteranceSavingOutput(BaseModel):
    """Contract: UtteranceSavingStage output (Stage 2).

    Stage 2 persists user input to database.
    """

    turn_number: int = Field(ge=0, description="Turn number for this utterance")
    user_utterance_id: str = Field(description="Database ID of saved utterance")
    user_utterance: Utterance = Field(description="Full saved utterance record")


class StateComputationOutput(BaseModel):
    """Contract: StateComputationStage output (Stage 5).

    Stage 5 refreshes graph state metrics after updates.

    ADR-010: Added computed_at for freshness tracking to prevent
    stale state bug where graph_state from Stage 1 was used in Stage 6.

    Domain Encapsulation: Added saturation_metrics computed from graph
    yield and quality signals. ContinuationStage reads this instead of
    maintaining its own tracking state.
    """

    graph_state: GraphState = Field(description="Refreshed knowledge graph state")
    recent_nodes: List[KGNode] = Field(
        default_factory=list, description="Refreshed list of recent nodes"
    )
    computed_at: datetime = Field(
        description="When state was computed (for freshness validation)"
    )
    saturation_metrics: Optional[SaturationMetrics] = Field(
        default=None,
        description="Saturation indicators computed from graph state and yield tracking",
    )

    @model_validator(mode="after")
    def set_computed_at_if_missing(self) -> "StateComputationOutput":
        """Set computed_at to current time if not provided."""
        if self.computed_at is None:  # type: ignore
            self.computed_at = datetime.now(timezone.utc)
        return self


class StrategySelectionInput(BaseModel):
    """Contract: StrategySelectionStage input (Stage 6).

    Stage 6 selects questioning strategy using methodology-based signal detection
    (Phase 4: methodology-specific signals with direct signal->strategy scoring).

    The two-tier scoring system has been removed and replaced by methodology-specific
    signal detection in each methodology module (MEC, JTBD).

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
    conversation_history: List[Dict[str, Any]] = Field(
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

        ADR-010: This validation prevents the stale graph_state bug where
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

    Phase 4: Added signals and alternatives for methodology-based selection.
    """

    strategy: str = Field(
        description="Selected strategy ID (e.g., 'deepen', 'broaden', 'ladder_deeper')"
    )
    focus: Optional[Dict[str, Any]] = Field(
        default=None, description="Focus target (node_id, element_id, or description)"
    )
    selected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When strategy was selected (for debugging)",
    )

    # Phase 4: Methodology-based selection fields
    signals: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Detected signals from methodology-specific signal detector (Phase 4)",
    )
    # Phase 6: Joint strategy-node scoring produces tuples with node_id
    strategy_alternatives: List[Union[tuple[str, float], tuple[str, str, float]]] = (
        Field(
            default_factory=list,
            description=(
                "Alternative strategies with scores for observability (Phase 4, Phase 6). "
                "Format: [(strategy, score)] or [(strategy, node_id, score)] for joint scoring"
            ),
        )
    )


class ExtractionOutput(BaseModel):
    """Contract: ExtractionStage output (Stage 3).

    Stage 3 extracts concepts and relationships from user input using
    methodology-specific extraction service.
    """

    extraction: ExtractionResult = Field(
        description="Extracted concepts and relationships"
    )
    methodology: str = Field(description="Methodology used for extraction")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When extraction was performed",
    )
    concept_count: int = Field(
        default=0, ge=0, description="Number of concepts extracted"
    )
    relationship_count: int = Field(
        default=0, ge=0, description="Number of relationships extracted"
    )

    @model_validator(mode="after")
    def set_counts_if_missing(self) -> "ExtractionOutput":
        """Set counts from extraction if not provided."""
        if self.concept_count == 0 and self.extraction:
            self.concept_count = len(self.extraction.concepts)
        if self.relationship_count == 0 and self.extraction:
            self.relationship_count = len(self.extraction.relationships)
        return self


class GraphUpdateOutput(BaseModel):
    """Contract: GraphUpdateStage output (Stage 4).

    Stage 4 updates the knowledge graph with extracted concepts and
    relationships, deduplicating against existing nodes.
    """

    nodes_added: List[KGNode] = Field(
        default_factory=list, description="Nodes added to graph"
    )
    edges_added: List[Dict[str, Any]] = Field(
        default_factory=list, description="Edges added to graph"
    )
    node_count: int = Field(default=0, ge=0, description="Number of nodes added")
    edge_count: int = Field(default=0, ge=0, description="Number of edges added")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When graph update was performed",
    )

    @model_validator(mode="after")
    def set_counts_if_missing(self) -> "GraphUpdateOutput":
        """Set counts from lists if not provided."""
        if self.node_count == 0:
            self.node_count = len(self.nodes_added)
        if self.edge_count == 0:
            self.edge_count = len(self.edges_added)
        return self


class QuestionGenerationOutput(BaseModel):
    """Contract: QuestionGenerationStage output (Stage 7).

    Stage 7 generates the next interview question based on selected
    strategy and focus, using template-based generation with LLM fallback.
    """

    question: str = Field(description="Generated question text")
    strategy: str = Field(description="Strategy used to generate question")
    focus: Optional[Dict[str, Any]] = Field(
        default=None, description="Focus target for question"
    )
    has_llm_fallback: bool = Field(
        default=False, description="Whether LLM fallback was used"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When question was generated",
    )


class ResponseSavingOutput(BaseModel):
    """Contract: ResponseSavingStage output (Stage 8).

    Stage 8 persists the generated question as a system utterance to
    the database.
    """

    turn_number: int = Field(ge=0, description="Turn number for this utterance")
    system_utterance_id: str = Field(description="Database ID of saved utterance")
    system_utterance: Utterance = Field(description="Full saved utterance record")
    question_text: str = Field(description="Question text that was saved")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When response was saved",
    )


class ContinuationOutput(BaseModel):
    """Contract: ContinuationStage output (Stage 9).

    Stage 9 determines whether the interview should continue based on
    turn count, saturation, and other signals.
    """

    should_continue: bool = Field(description="Whether to continue the interview")
    focus_concept: str = Field(default="", description="Concept to focus on next turn")
    reason: str = Field(default="", description="Reason for continuation decision")
    turns_remaining: int = Field(ge=0, description="Number of turns remaining")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When continuation decision was made",
    )


class ScoringPersistenceOutput(BaseModel):
    """Contract: ScoringPersistenceStage output (Stage 10).

    Stage 10 persists scoring metrics for observability and analysis.

    Note: The legacy two-tier scoring system has been removed. This stage now
    saves methodology-based signals from StrategySelectionStage.
    """

    turn_number: int = Field(ge=0, description="Turn number for scoring")
    strategy: str = Field(description="Strategy that was selected")
    depth_score: float = Field(ge=0.0, description="Depth metric from graph state")
    saturation_score: float = Field(
        ge=0.0, description="Saturation metric from graph state"
    )
    has_methodology_signals: bool = Field(
        default=False, description="Whether methodology signals were saved"
    )
    has_legacy_scoring: bool = Field(
        default=False, description="Legacy two-tier scoring (always False now)"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When scoring was persisted",
    )
