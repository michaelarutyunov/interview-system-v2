"""
Context object for turn processing pipeline.

ADR-008 Phase 3: TurnContext carries state through all pipeline stages.
ADR-010: Added graph_state_computed_at for freshness validation.
Phase 4: Added signals and strategy_alternatives for methodology-based selection.
Phase 6: Enforced contract outputs - contracts are the single source of truth.
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
    """
    Context object that accumulates state through pipeline stages.

    Phase 6: Contracts are the single source of truth. Each stage produces
    a contract output that is consumed by subsequent stages.
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

    # Stage 4.5: SlotDiscoveryStage output (Phase 2: Dual-Graph Architecture, bead yuhv)
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
        """Get methodology from ContextLoadingOutput.

        Raises:
            RuntimeError: If context_loading_output is not set (pipeline contract violation)
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
        """Get concept_id from ContextLoadingOutput.

        Raises:
            RuntimeError: If context_loading_output is not set (pipeline contract violation)
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
        """Get concept_name from ContextLoadingOutput.

        Raises:
            RuntimeError: If context_loading_output is not set (pipeline contract violation)
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
        """Get turn_number from ContextLoadingOutput.

        Raises:
            RuntimeError: If context_loading_output is not set (pipeline contract violation)
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
        """Get mode from ContextLoadingOutput.

        Raises:
            RuntimeError: If context_loading_output is not set (pipeline contract violation)
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
        """Get max_turns from ContextLoadingOutput.

        Raises:
            RuntimeError: If context_loading_output is not set (pipeline contract violation)
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
        """Get recent_utterances from ContextLoadingOutput."""
        if self.context_loading_output:
            return self.context_loading_output.recent_utterances
        return []

    @property
    def strategy_history(self) -> List[str]:
        """Get strategy_history from ContextLoadingOutput."""
        if self.context_loading_output:
            return self.context_loading_output.strategy_history
        return []

    @property
    def graph_state(self) -> Optional[GraphState]:
        """Get graph_state from StateComputationOutput."""
        if self.state_computation_output:
            return self.state_computation_output.graph_state
        return None

    @property
    def graph_state_computed_at(self) -> Optional[datetime]:
        """Get computed_at from StateComputationOutput."""
        if self.state_computation_output:
            return self.state_computation_output.computed_at
        return None

    @property
    def recent_nodes(self) -> List[KGNode]:
        """Get recent_nodes from StateComputationOutput."""
        if self.state_computation_output:
            return self.state_computation_output.recent_nodes
        return []

    @property
    def canonical_graph_state(self) -> Optional["CanonicalGraphState"]:
        """Get canonical_graph_state from StateComputationOutput.

        Phase 3 (Dual-Graph Integration), bead ty40.
        """
        if self.state_computation_output:
            return self.state_computation_output.canonical_graph_state
        return None

    @property
    def extraction(self) -> Optional[Any]:
        """Get extraction from ExtractionOutput."""
        if self.extraction_output:
            return self.extraction_output.extraction
        return None

    @property
    def user_utterance(self) -> Optional[Utterance]:
        """Get user_utterance from UtteranceSavingOutput."""
        if self.utterance_saving_output:
            return self.utterance_saving_output.user_utterance
        return None

    @property
    def system_utterance(self) -> Optional[Utterance]:
        """Get system_utterance from ResponseSavingOutput."""
        if self.response_saving_output:
            return self.response_saving_output.system_utterance
        return None

    @property
    def nodes_added(self) -> List[KGNode]:
        """Get nodes_added from GraphUpdateOutput."""
        if self.graph_update_output:
            return self.graph_update_output.nodes_added
        return []

    @property
    def edges_added(self) -> List[Dict[str, Any]]:
        """Get edges_added from GraphUpdateOutput."""
        if self.graph_update_output:
            return self.graph_update_output.edges_added
        return []

    @property
    def strategy(self) -> str:
        """Get strategy from StrategySelectionOutput.

        Raises:
            RuntimeError: If strategy_selection_output is not set (pipeline contract violation)
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
        """Get focus from StrategySelectionOutput."""
        if self.strategy_selection_output:
            return self.strategy_selection_output.focus
        return None

    @property
    def signals(self) -> Optional[Dict[str, Any]]:
        """Get signals from StrategySelectionOutput."""
        if self.strategy_selection_output:
            return self.strategy_selection_output.signals
        return None

    @property
    def strategy_alternatives(self) -> List[tuple[str, float] | tuple[str, str, float]]:
        """Get strategy_alternatives from StrategySelectionOutput."""
        if self.strategy_selection_output:
            return self.strategy_selection_output.strategy_alternatives
        return []

    @property
    def should_continue(self) -> bool:
        """Get should_continue from ContinuationOutput.

        Raises:
            RuntimeError: If continuation_output is not set (pipeline contract violation)
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
        """Get focus_concept from ContinuationOutput.

        Raises:
            RuntimeError: If continuation_output is not set (pipeline contract violation)
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
        """Get next_question from QuestionGenerationOutput.

        Raises:
            RuntimeError: If question_generation_output is not set (pipeline contract violation)
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
        """Get scoring dict from ScoringPersistenceOutput."""
        if self.scoring_persistence_output:
            return {
                "depth": self.scoring_persistence_output.depth_score,
                "saturation": self.scoring_persistence_output.saturation_score,
            }
        return {}

    # Legacy fields kept for extreme backward compatibility (will be removed)
    stage_timings: Dict[str, float] = field(default_factory=dict)
