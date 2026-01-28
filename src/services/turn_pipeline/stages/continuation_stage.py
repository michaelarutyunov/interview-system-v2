"""
Stage 7: Determine continuation.

ADR-008 Phase 3: Decide if interview should continue or end.
Phase 6: Output ContinuationOutput contract.
"""

from typing import TYPE_CHECKING

import structlog

from ..base import TurnStage
from src.domain.models.pipeline_contracts import ContinuationOutput


if TYPE_CHECKING:
    from ..context import PipelineContext
log = structlog.get_logger(__name__)


class ContinuationStage(TurnStage):
    """
    Determine if interview should continue.

    Populates PipelineContext.should_continue and PipelineContext.focus_concept.
    """

    def __init__(self, question_service):
        """
        Initialize stage.

        Args:
            question_service: QuestionService instance
        """
        self.question = question_service

    async def process(self, context: "PipelineContext") -> "PipelineContext":
        """
        Determine if we should continue and select focus concept.

        Args:
            context: Turn context with turn_number, max_turns, graph_state, strategy

        Returns:
            Modified context with should_continue and focus_concept
        """
        # Determine if we should continue
        should_continue = self._should_continue(
            turn_number=context.turn_number,
            max_turns=context.max_turns,
            graph_state=context.graph_state,
            strategy=context.strategy,
        )

        # Calculate continuation reason
        reason = ""
        if not should_continue:
            if context.turn_number >= context.max_turns:
                reason = "Maximum turns reached"
            elif context.strategy == "close":
                reason = "Closing strategy selected"
            else:
                reason = "Interview concluded"

        # Select focus concept if continuing
        if should_continue:
            if context.selection_result and context.focus:
                # Use focus from strategy service selection
                if "node_id" in context.focus and context.recent_nodes:
                    # Find the node in recent_nodes
                    focus_concept = next(
                        (
                            n.label
                            for n in context.recent_nodes
                            if str(n.id) == context.focus["node_id"]
                        ),
                        # Fallback to description if node not found
                        context.focus.get("focus_description", "the topic"),
                    )
                else:
                    # Use focus description as fallback
                    focus_concept = context.focus.get("focus_description", "the topic")
            else:
                # Phase 2: fall back to heuristic selection
                focus_concept = await self.question.select_focus_concept(
                    recent_nodes=context.recent_nodes,
                    graph_state=context.graph_state,
                    strategy=context.strategy,
                )
        else:
            focus_concept = ""

        # Create contract output (single source of truth)
        # No need to set individual fields - they're derived from the contract
        context.continuation_output = ContinuationOutput(
            should_continue=should_continue,
            focus_concept=focus_concept,
            reason=reason,
            turns_remaining=max(0, context.max_turns - context.turn_number),
            # timestamp auto-set
        )

        log.info(
            "continuation_determined",
            session_id=context.session_id,
            should_continue=should_continue,
            focus_concept=focus_concept if should_continue else None,
        )

        return context

    def _should_continue(
        self,
        turn_number: int,
        max_turns: int,
        graph_state,
        strategy: str,
    ) -> bool:
        """
        Determine if interview should continue.

        Args:
            turn_number: Current turn number
            max_turns: Maximum turns for this session
            graph_state: Current graph state
            strategy: Selected strategy

        Returns:
            True if should continue, False if should end
        """
        # Max turns reached
        if turn_number >= max_turns:
            log.info(
                "session_ending",
                reason="max_turns",
                turn_number=turn_number,
                max_turns=max_turns,
            )
            return False

        # Strategy is close
        if strategy == "close":
            log.info("session_ending", reason="close_strategy")
            return False

        # Phase 3 will add: coverage target reached, saturation detected

        return True
