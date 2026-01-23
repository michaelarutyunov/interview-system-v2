"""
Stage 6: Select strategy.

ADR-008 Phase 3: Use two-tier scoring to select questioning strategy.
"""

import structlog

from ..base import TurnStage

log = structlog.get_logger(__name__)


class StrategySelectionStage(TurnStage):
    """
    Select questioning strategy using two-tier adaptive scoring.

    Populates TurnContext.strategy, TurnContext.selection_result, and TurnContext.focus.
    Falls back to Phase 2 hardcoded behavior if strategy_service not available.
    """

    def __init__(self, strategy_service=None):
        """
        Initialize stage.

        Args:
            strategy_service: Optional StrategyService instance
        """
        self.strategy = strategy_service

    async def process(self, context: "TurnContext") -> "TurnContext":
        """
        Select strategy using two-tier adaptive scoring.

        Args:
            context: Turn context with graph_state, recent_nodes, recent_utterances

        Returns:
            Modified context with strategy, selection_result, and focus
        """
        if self.strategy:
            selection = await self.strategy.select(
                graph_state=context.graph_state,
                recent_nodes=[n.dict() for n in context.recent_nodes],
                conversation_history=context.recent_utterances,
                mode=context.mode,
            )
            strategy = selection.selected_strategy["id"]
            focus = selection.selected_focus
            selection_result = selection
        else:
            # Phase 2: fallback to hardcoded selection
            strategy = self._select_strategy(context)
            selection_result = None
            focus = None

        context.strategy = strategy
        context.selection_result = selection_result
        context.focus = focus

        log.info(
            "strategy_selected",
            session_id=context.session_id,
            strategy=strategy,
            has_selection_result=selection_result is not None,
        )

        return context

    def _select_strategy(self, context: "TurnContext") -> str:
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
