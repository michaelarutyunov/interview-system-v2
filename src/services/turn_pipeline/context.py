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

if TYPE_CHECKING:
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
    context_loading_output: Optional[Any] = None

    # Stage 2: UtteranceSavingStage output
    utterance_saving_output: Optional[Any] = None

    # Stage 3: ExtractionStage output
    extraction_output: Optional[Any] = None

    # Stage 4: GraphUpdateStage output
    graph_update_output: Optional[Any] = None

    # Stage 5: StateComputationStage output
    state_computation_output: Optional[Any] = None

    # Stage 6: StrategySelectionStage output
    strategy_selection_output: Optional[Any] = None

    # Stage 7: ContinuationStage output
    continuation_output: Optional[Any] = None

    # Stage 8: QuestionGenerationStage output
    question_generation_output: Optional[Any] = None

    # Stage 9: ResponseSavingStage output
    response_saving_output: Optional[Any] = None

    # Stage 10: ScoringPersistenceStage output
    scoring_persistence_output: Optional[Any] = None

    # =============================================================================
    # Convenience Properties (derive from contracts, don't duplicate state)
    # =============================================================================
    # These provide backward compatibility while keeping contracts as source of truth

    @property
    def methodology(self) -> str:
        """Get methodology from ContextLoadingOutput."""
        if self.context_loading_output:
            return self.context_loading_output.methodology
        return ""

    @property
    def concept_id(self) -> str:
        """Get concept_id from ContextLoadingOutput."""
        if self.context_loading_output:
            return self.context_loading_output.concept_id
        return ""

    @property
    def concept_name(self) -> str:
        """Get concept_name from ContextLoadingOutput."""
        if self.context_loading_output:
            return self.context_loading_output.concept_name
        return ""

    @property
    def turn_number(self) -> int:
        """Get turn_number from ContextLoadingOutput."""
        if self.context_loading_output:
            return self.context_loading_output.turn_number
        return 1

    @property
    def mode(self) -> str:
        """Get mode from ContextLoadingOutput."""
        if self.context_loading_output:
            return self.context_loading_output.mode
        return "coverage_driven"

    @property
    def max_turns(self) -> int:
        """Get max_turns from ContextLoadingOutput."""
        if self.context_loading_output:
            return self.context_loading_output.max_turns
        return 20

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
        """Get strategy from StrategySelectionOutput."""
        if self.strategy_selection_output:
            return self.strategy_selection_output.strategy
        return "deepen"

    @property
    def selection_result(self) -> Optional[Any]:
        """Get selection_result (None for methodology-based selection)."""
        return None  # Methodology service doesn't produce SelectionResult

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
    def strategy_alternatives(self) -> List[tuple[str, float]]:
        """Get strategy_alternatives from StrategySelectionOutput."""
        if self.strategy_selection_output:
            return self.strategy_selection_output.strategy_alternatives
        return []

    @property
    def should_continue(self) -> bool:
        """Get should_continue from ContinuationOutput."""
        if self.continuation_output:
            return self.continuation_output.should_continue
        return True

    @property
    def focus_concept(self) -> str:
        """Get focus_concept from ContinuationOutput."""
        if self.continuation_output:
            return self.continuation_output.focus_concept
        return ""

    @property
    def next_question(self) -> str:
        """Get next_question from QuestionGenerationOutput."""
        if self.question_generation_output:
            return self.question_generation_output.question
        return ""

    @property
    def scoring(self) -> Dict[str, Any]:
        """Get scoring dict from ScoringPersistenceOutput."""
        if self.scoring_persistence_output:
            return {
                "coverage": self.scoring_persistence_output.coverage_score,
                "depth": self.scoring_persistence_output.depth_score,
                "saturation": self.scoring_persistence_output.saturation_score,
            }
        return {}

    # Legacy fields kept for extreme backward compatibility (will be removed)
    stage_timings: Dict[str, float] = field(default_factory=dict)
