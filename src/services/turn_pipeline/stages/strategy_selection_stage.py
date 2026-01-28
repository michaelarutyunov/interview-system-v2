"""
Stage 6: Select strategy.

ADR-008 Phase 3: Use two-tier scoring to select questioning strategy.
ADR-010: Validate graph_state freshness before strategy selection.
Phase 4: Use methodology-based strategy selection with direct signal->strategy scoring.
"""

from typing import TYPE_CHECKING, Optional, Dict, Any

import structlog

from ..base import TurnStage
from src.domain.models.pipeline_contracts import StrategySelectionInput
from src.services.methodology_strategy_service import MethodologyStrategyService


if TYPE_CHECKING:
    from ..context import PipelineContext
log = structlog.get_logger(__name__)


class StrategySelectionStage(TurnStage):
    """
    Select questioning strategy using methodology-based signal detection.

    Phase 4: Uses MethodologyStrategyService for direct signal->strategy scoring.
    Falls back to two-tier scoring or hardcoded behavior if methodology service unavailable.

    Populates:
    - PipelineContext.strategy
    - PipelineContext.selection_result
    - PipelineContext.focus
    - PipelineContext.signals (NEW in Phase 4)
    - PipelineContext.strategy_alternatives (NEW in Phase 4)
    """

    def __init__(self, strategy_service=None, use_methodology_service: bool = True):
        """
        Initialize stage.

        Args:
            strategy_service: Optional StrategyService instance (two-tier scoring)
            use_methodology_service: If True, use new methodology-based service
        """
        self.strategy = strategy_service
        self.use_methodology_service = use_methodology_service
        self.methodology_strategy: Optional[MethodologyStrategyService] = None

        if use_methodology_service:
            self.methodology_strategy = MethodologyStrategyService()

    async def process(self, context: "PipelineContext") -> "PipelineContext":
        """
        Select strategy using methodology-based signal detection.

        ADR-010: Validates graph_state freshness before selection.
        Phase 4: Uses methodology-specific signals and direct signal->strategy scoring.

        Args:
            context: Turn context with graph_state, recent_nodes, recent_utterances

        Returns:
            Modified context with strategy, selection_result, focus, signals, and alternatives
        """
        # ADR-010: Validate freshness before using graph_state
        # This prevents the stale state bug where coverage_state from Stage 1
        # (before extraction) was used in Stage 6
        if context.graph_state and context.graph_state_computed_at:
            try:
                # Create StrategySelectionInput to validate freshness
                # This will raise ValidationError if state is stale
                selection_input = StrategySelectionInput(
                    graph_state=context.graph_state,
                    recent_nodes=context.recent_nodes,
                    extraction=context.extraction,  # type: ignore
                    conversation_history=context.recent_utterances,
                    turn_number=context.turn_number,
                    mode=context.mode,
                    computed_at=context.graph_state_computed_at,
                )
                log.debug(
                    "graph_state_freshness_validated",
                    session_id=context.session_id,
                    computed_at=selection_input.computed_at,
                )
            except Exception as e:
                # Freshness validation failed - state is stale
                log.error(
                    "graph_state_freshness_validation_failed",
                    session_id=context.session_id,
                    error=str(e),
                )
                # For now, log and continue - in future we might want to
                # re-compute state or use fallback behavior
                raise

        # Phase 4: Try methodology-based strategy selection
        if self.methodology_strategy:
            (
                strategy,
                focus,
                alternatives,
                signals,
            ) = await self._select_strategy_with_methodology(context)
            selection_result = (
                None  # Methodology service doesn't produce SelectionResult
            )
            # Store signals and alternatives for observability
            context.signals = signals
            context.strategy_alternatives = alternatives
        elif self.strategy:
            # Fallback to two-tier scoring
            selection = await self.strategy.select(
                graph_state=context.graph_state,
                recent_nodes=[n.model_dump() for n in context.recent_nodes],
                conversation_history=context.recent_utterances,
                mode=context.mode,
                current_user_input=context.user_input,
                current_extraction=context.extraction,
            )

            # ADR-010 Phase 2: Populate session context for conversion to new schema
            selection.session_id = context.session_id
            selection.turn_number = context.turn_number
            selection.phase = (
                context.graph_state.current_phase
                if context.graph_state
                else "exploratory"
            )
            # Get phase multiplier from scoring result if available
            if selection.scoring_result:
                selection.phase_multiplier = (
                    selection.scoring_result.phase_multiplier or 1.0
                )
            else:
                selection.phase_multiplier = 1.0

            strategy = selection.selected_strategy["id"]
            focus = selection.selected_focus
            selection_result = selection
            alternatives = []
            signals = None
        else:
            # Phase 2: fallback to hardcoded selection
            strategy = self._select_strategy(context)
            selection_result = None
            focus = None
            alternatives = []
            signals = None

        # Track strategy history for StrategyDiversityScorer
        # This enables the system to penalize repetitive questioning patterns
        if context.graph_state:
            context.graph_state.add_strategy_used(strategy)

        context.strategy = strategy
        context.selection_result = selection_result
        context.focus = focus

        log.info(
            "strategy_selected",
            session_id=context.session_id,
            strategy=strategy,
            has_selection_result=selection_result is not None,
            has_methodology_signals=signals is not None,
            alternatives_count=len(alternatives) if alternatives else 0,
        )

        return context

    async def _select_strategy_with_methodology(
        self,
        context: "PipelineContext",
    ) -> tuple[str, Optional[str], list[tuple[str, float]], Optional[Dict[str, Any]]]:
        """
        Select strategy using methodology-based service.

        Args:
            context: Turn context

        Returns:
            Tuple of (strategy_name, focus, alternatives, signals)
        """
        # Get last response text
        response_text = context.user_input or ""

        # Use new methodology-based selection
        return await self.methodology_strategy.select_strategy(
            context,
            context.graph_state,
            response_text,
        )

    def _select_strategy(self, context: "PipelineContext") -> str:
        """
        Fallback strategy selection (Phase 2 behavior).

        Args:
            context: Turn context

        Returns:
            Strategy name
        """
        # Simple heuristics for variety
        if context.turn_number >= context.max_turns - 2:
            return "close"

        # Default to deepen
        return "deepen"
