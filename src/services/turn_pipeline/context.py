"""
Turn processing pipeline context for contract-based state accumulation.

Carries state through all pipeline stages, accumulating formal contract outputs
from each stage. Provides the single source of truth for turn data with
freshness tracking for graph state validation.

ADR-010: All stage outputs use Pydantic BaseModel contracts. Convenience
properties provide backward compatibility while keeping contracts as source of truth.

Key responsibilities:
- Accumulate contract outputs from each pipeline stage
- Provide typed access to stage results via convenience properties
- Enforce pipeline ordering through RuntimeError on premature access
- Track graph state freshness via StateComputationOutput.computed_at
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from src.domain.models.knowledge_graph import GraphState, KGNode
from src.domain.models.utterance import Utterance
from src.domain.models.pipeline_contracts import (
    ContextLoadingOutput,
    UtteranceSavingOutput,
    SrlPreprocessingOutput,
    ExtractionOutput,
    GraphUpdateOutput,
    SlotDiscoveryOutput,
    StateComputationOutput,
    StrategySelectionOutput,
    ContinuationOutput,
    QuestionGenerationOutput,
    ResponseSavingOutput,
    ScoringPersistenceOutput,
)

if TYPE_CHECKING:
    from src.domain.models.canonical_graph import CanonicalGraphState
    from src.services.node_state_tracker import NodeStateTracker


@dataclass
class PipelineContext:
    """Pipeline context for contract-based state accumulation across turn stages.

    Accumulates formal Pydantic contract outputs from each pipeline stage.
    Contracts are the single source of truth for all turn data.

    Pipeline ordering enforcement: Convenience properties raise RuntimeError
    if accessed before their producing stage completes, preventing bugs from
    stale or missing state.

    Stage outputs (contracts):
    - Stage 1: ContextLoadingOutput - session metadata, turn number, history
    - Stage 2: UtteranceSavingOutput - persisted user utterance
    - Stage 2.5: SrlPreprocessingOutput - discourse relations, SRL frames (optional)
    - Stage 3: ExtractionOutput - extracted concepts and relationships
    - Stage 4: GraphUpdateOutput - nodes and edges added to graph
    - Stage 4.5: SlotDiscoveryOutput - canonical slot mappings (dual-graph)
    - Stage 5: StateComputationOutput - graph state metrics, recent nodes, saturation
    - Stage 6: StrategySelectionOutput - selected strategy, focus, signals
    - Stage 7: ContinuationOutput - should_continue flag, focus concept
    - Stage 8: QuestionGenerationOutput - generated next question
    - Stage 9: ResponseSavingOutput - persisted system utterance
    - Stage 10: ScoringPersistenceOutput - scoring metrics for observability
    """

    # =============================================================================
    # Input parameters (immutable after creation)
    # =============================================================================
    session_id: str
    user_input: str

    # =============================================================================
    # Service References (shared across stages)
    # =============================================================================
    node_tracker: Optional["NodeStateTracker"] = None

    # =============================================================================
    # Stage Outputs (Contracts)
    # =============================================================================
    # Each stage produces a formal contract output. These contracts ARE the state.

    # Stage 1: ContextLoadingStage output
    context_loading_output: Optional[ContextLoadingOutput] = None

    # Stage 2: UtteranceSavingStage output
    utterance_saving_output: Optional[UtteranceSavingOutput] = None

    # Stage 2.5: SRLPreprocessingStage output (optional, can be None if disabled)
    srl_preprocessing_output: Optional[SrlPreprocessingOutput] = None

    # Stage 3: ExtractionStage output
    extraction_output: Optional[ExtractionOutput] = None

    # Stage 4: GraphUpdateStage output
    graph_update_output: Optional[GraphUpdateOutput] = None

    # Stage 4.5: SlotDiscoveryStage output
    slot_discovery_output: Optional[SlotDiscoveryOutput] = None

    # Stage 5: StateComputationStage output
    state_computation_output: Optional[StateComputationOutput] = None

    # Stage 6: StrategySelectionStage output
    strategy_selection_output: Optional[StrategySelectionOutput] = None

    # Stage 7: ContinuationStage output
    continuation_output: Optional[ContinuationOutput] = None

    # Stage 8: QuestionGenerationStage output
    question_generation_output: Optional[QuestionGenerationOutput] = None

    # Stage 9: ResponseSavingStage output
    response_saving_output: Optional[ResponseSavingOutput] = None

    # Stage 10: ScoringPersistenceStage output
    scoring_persistence_output: Optional[ScoringPersistenceOutput] = None

    # =============================================================================
    # Convenience Properties (derive from contracts, don't duplicate state)
    # =============================================================================
    # These provide backward compatibility while keeping contracts as source of truth

    @property
    def methodology(self) -> str:
        """Get methodology identifier (e.g., 'means_end_chain', 'repertory_grid').

        Returns:
            Methodology identifier from ContextLoadingOutput (Stage 1)

        Raises:
            RuntimeError: If ContextLoadingStage (Stage 1) has not completed
        """
        if self.context_loading_output:
            return self.context_loading_output.methodology
        raise RuntimeError(
            "Pipeline contract violation: methodology accessed before "
            "ContextLoadingStage (Stage 1) completed. "
            f"Session: {self.session_id}"
        )

    @property
    def concept_id(self) -> str:
        """Get concept identifier for the current session.

        Returns:
            Concept ID from ContextLoadingOutput (Stage 1)

        Raises:
            RuntimeError: If ContextLoadingStage (Stage 1) has not completed
        """
        if self.context_loading_output:
            return self.context_loading_output.concept_id
        raise RuntimeError(
            "Pipeline contract violation: concept_id accessed before "
            "ContextLoadingStage (Stage 1) completed. "
            f"Session: {self.session_id}"
        )

    @property
    def concept_name(self) -> str:
        """Get human-readable concept name for the current session.

        Returns:
            Concept name from ContextLoadingOutput (Stage 1)

        Raises:
            RuntimeError: If ContextLoadingStage (Stage 1) has not completed
        """
        if self.context_loading_output:
            return self.context_loading_output.concept_name
        raise RuntimeError(
            "Pipeline contract violation: concept_name accessed before "
            "ContextLoadingStage (Stage 1) completed. "
            f"Session: {self.session_id}"
        )

    @property
    def turn_number(self) -> int:
        """Get current turn number (0-indexed) for this interview turn.

        Returns:
            Turn number from ContextLoadingOutput (Stage 1)

        Raises:
            RuntimeError: If ContextLoadingStage (Stage 1) has not completed
        """
        if self.context_loading_output:
            return self.context_loading_output.turn_number
        raise RuntimeError(
            "Pipeline contract violation: turn_number accessed before "
            "ContextLoadingStage (Stage 1) completed. "
            f"Session: {self.session_id}"
        )

    @property
    def mode(self) -> str:
        """Get interview mode (e.g., 'exploratory', 'synthetic').

        Returns:
            Interview mode from ContextLoadingOutput (Stage 1)

        Raises:
            RuntimeError: If ContextLoadingStage (Stage 1) has not completed
        """
        if self.context_loading_output:
            return self.context_loading_output.mode
        raise RuntimeError(
            "Pipeline contract violation: mode accessed before "
            "ContextLoadingStage (Stage 1) completed. "
            f"Session: {self.session_id}"
        )

    @property
    def max_turns(self) -> int:
        """Get maximum number of turns configured for this session.

        Returns:
            Max turns from ContextLoadingOutput (Stage 1)

        Raises:
            RuntimeError: If ContextLoadingStage (Stage 1) has not completed
        """
        if self.context_loading_output:
            return self.context_loading_output.max_turns
        raise RuntimeError(
            "Pipeline contract violation: max_turns accessed before "
            "ContextLoadingStage (Stage 1) completed. "
            f"Session: {self.session_id}"
        )

    @property
    def recent_utterances(self) -> List[Dict[str, str]]:
        """Get conversation history of recent utterances.

        Returns:
            List of recent utterance dictionaries from ContextLoadingOutput (Stage 1),
            or empty list if stage not yet completed.
        """
        if self.context_loading_output:
            return self.context_loading_output.recent_utterances
        return []

    @property
    def strategy_history(self) -> List[str]:
        """Get history of strategies used in previous turns.

        Returns:
            List of strategy IDs from ContextLoadingOutput (Stage 1),
            or empty list if stage not yet completed.
        """
        if self.context_loading_output:
            return self.context_loading_output.strategy_history
        return []

    @property
    def graph_state(self) -> Optional[GraphState]:
        """Get current knowledge graph state with node/edge metrics.

        Returns:
            GraphState from StateComputationOutput (Stage 5), or None if
            stage not yet completed.

        Note:
            Graph state is only available AFTER StateComputationStage completes.
            Stages 2-4 should not access this property as state is computed
            after graph updates in Stage 4.
        """
        if self.state_computation_output:
            return self.state_computation_output.graph_state
        return None

    @property
    def graph_state_computed_at(self) -> Optional[datetime]:
        """Get timestamp when graph state was computed for freshness validation.

        Returns:
            Computed timestamp from StateComputationOutput (Stage 5), or None
            if stage not yet completed.

        Note:
            Used for freshness validation to prevent stale state bugs in
            StrategySelectionStage (ADR-010).
        """
        if self.state_computation_output:
            return self.state_computation_output.computed_at
        return None

    @property
    def recent_nodes(self) -> List[KGNode]:
        """Get list of recently added knowledge graph nodes.

        Returns:
            List of KGNode objects from StateComputationOutput (Stage 5),
            or empty list if stage not yet completed.

        Note:
            Recent nodes are only available AFTER StateComputationStage completes.
        """
        if self.state_computation_output:
            return self.state_computation_output.recent_nodes
        return []

    @property
    def canonical_graph_state(self) -> Optional["CanonicalGraphState"]:
        """Get canonical (deduplicated) graph state for dual-graph architecture.

        Returns:
            CanonicalGraphState from StateComputationOutput (Stage 5), or None
            if stage not yet completed.

        Note:
            Part of dual-graph architecture (ADR-013). Provides aggregate
            metrics on canonical slots rather than surface nodes.
        """
        if self.state_computation_output:
            return self.state_computation_output.canonical_graph_state
        return None

    @property
    def extraction(self) -> Optional[Any]:
        """Get extraction result with concepts and relationships.

        Returns:
            ExtractionResult from ExtractionOutput (Stage 3), or None if
            stage not yet completed.
        """
        if self.extraction_output:
            return self.extraction_output.extraction
        return None

    @property
    def user_utterance(self) -> Optional[Utterance]:
        """Get persisted user utterance record from database.

        Returns:
            Utterance object from UtteranceSavingOutput (Stage 2), or None if
            stage not yet completed.
        """
        if self.utterance_saving_output:
            return self.utterance_saving_output.user_utterance
        return None

    @property
    def system_utterance(self) -> Optional[Utterance]:
        """Get persisted system utterance (generated question) from database.

        Returns:
            Utterance object from ResponseSavingOutput (Stage 9), or None if
            stage not yet completed.
        """
        if self.response_saving_output:
            return self.response_saving_output.system_utterance
        return None

    @property
    def nodes_added(self) -> List[KGNode]:
        """Get list of nodes added to knowledge graph this turn.

        Returns:
            List of KGNode objects from GraphUpdateOutput (Stage 4), or empty
            list if stage not yet completed.
        """
        if self.graph_update_output:
            return self.graph_update_output.nodes_added
        return []

    @property
    def edges_added(self) -> List[Dict[str, Any]]:
        """Get list of edges added to knowledge graph this turn.

        Returns:
            List of edge dictionaries from GraphUpdateOutput (Stage 4), or
            empty list if stage not yet completed.
        """
        if self.graph_update_output:
            return self.graph_update_output.edges_added
        return []

    @property
    def strategy(self) -> str:
        """Get selected questioning strategy (e.g., 'deepen', 'broaden', 'ladder_deeper').

        Returns:
            Strategy ID from StrategySelectionOutput (Stage 6)

        Raises:
            RuntimeError: If StrategySelectionStage (Stage 6) has not completed
        """
        if self.strategy_selection_output:
            return self.strategy_selection_output.strategy
        raise RuntimeError(
            "Pipeline contract violation: strategy accessed before "
            "StrategySelectionStage (Stage 6) completed. "
            "Ensure stages run in order. "
            f"Session: {self.session_id}"
        )

    @property
    def focus(self) -> Optional[Dict[str, Any]]:
        """Get focus target for the next question (node_id, element_id, or description).

        Returns:
            Focus dictionary from StrategySelectionOutput (Stage 6), or None if
            stage not yet completed.
        """
        if self.strategy_selection_output:
            return self.strategy_selection_output.focus
        return None

    @property
    def node_signals(self) -> Optional[Dict[str, Dict[str, Any]]]:
        """Get per-node signals computed during joint strategy-node scoring.

        Returns:
            Dict mapping node_id to dict of signal_name: value, from
            StrategySelectionOutput (Stage 6), or None if stage not yet completed.
        """
        if self.strategy_selection_output:
            return self.strategy_selection_output.node_signals
        return None

    @property
    def signals(self) -> Optional[Dict[str, Any]]:
        """Get detected methodology signals for observability and debugging.

        Returns:
            Signals dictionary from StrategySelectionOutput (Stage 6), or None if
            stage not yet completed.

        Note:
            Includes graph.*, llm.*, temporal.*, and meta.* signals used
            for methodology-based strategy selection.
        """
        if self.strategy_selection_output:
            return self.strategy_selection_output.signals
        return None

    @property
    def strategy_alternatives(self) -> List[tuple[str, float] | tuple[str, str, float]]:
        """Get ranked alternative strategies with scores for observability.

        Returns:
            List of tuples from StrategySelectionOutput (Stage 6):
            - [(strategy, score)] for strategy-only scoring
            - [(strategy, node_id, score)] for joint strategy-node scoring
            Returns empty list if stage not yet completed.

        Note:
            Used for debugging and understanding why a strategy was selected.
        """
        if self.strategy_selection_output:
            return self.strategy_selection_output.strategy_alternatives
        return []

    @property
    def should_continue(self) -> bool:
        """Get whether the interview should continue for another turn.

        Returns:
            Boolean continuation flag from ContinuationOutput (Stage 7)

        Raises:
            RuntimeError: If ContinuationStage (Stage 7) has not completed
        """
        if self.continuation_output:
            return self.continuation_output.should_continue
        raise RuntimeError(
            "Pipeline contract violation: should_continue accessed before "
            "ContinuationStage (Stage 7) completed. "
            f"Session: {self.session_id}"
        )

    @property
    def focus_concept(self) -> str:
        """Get concept ID to focus on for the next turn.

        Returns:
            Focus concept ID from ContinuationOutput (Stage 7)

        Raises:
            RuntimeError: If ContinuationStage (Stage 7) has not completed
        """
        if self.continuation_output:
            return self.continuation_output.focus_concept
        raise RuntimeError(
            "Pipeline contract violation: focus_concept accessed before "
            "ContinuationStage (Stage 7) completed. "
            f"Session: {self.session_id}"
        )

    @property
    def next_question(self) -> str:
        """Get generated next interview question.

        Returns:
            Question text from QuestionGenerationOutput (Stage 8)

        Raises:
            RuntimeError: If QuestionGenerationStage (Stage 8) has not completed
        """
        if self.question_generation_output:
            return self.question_generation_output.question
        raise RuntimeError(
            "Pipeline contract violation: next_question accessed before "
            "QuestionGenerationStage (Stage 8) completed. "
            f"Session: {self.session_id}"
        )

    @property
    def scoring(self) -> Dict[str, Any]:
        """Get scoring metrics for observability and analysis.

        Returns:
            Dictionary with depth and saturation scores from
            ScoringPersistenceOutput (Stage 10), or empty dict if stage
            not yet completed.

        Note:
            Legacy two-tier scoring has been removed. Now saves methodology-based
            signals from StrategySelectionStage.
        """
        if self.scoring_persistence_output:
            return {
                "depth": self.scoring_persistence_output.depth_score,
                "saturation": self.scoring_persistence_output.saturation_score,
            }
        return {}

    # Legacy fields kept for extreme backward compatibility (will be removed)
    stage_timings: Dict[str, float] = field(default_factory=dict)
