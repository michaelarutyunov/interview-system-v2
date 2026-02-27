"""
Stage 8: Generate follow-up question.

Uses QuestionService to generate next question. Outputs
QuestionGenerationOutput contract.
"""

from typing import TYPE_CHECKING

import structlog

from ..base import TurnStage
from src.domain.models.pipeline_contracts import QuestionGenerationOutput
from src.services.question_service import QuestionService


if TYPE_CHECKING:
    from ..context import PipelineContext
log = structlog.get_logger(__name__)


class QuestionGenerationStage(TurnStage):
    """
    Generate follow-up question.

    Populates PipelineContext.next_question.
    """

    def __init__(self, question_service: QuestionService):
        """
        Initialize stage.

        Args:
            question_service: QuestionService instance
        """
        self.question = question_service

    async def process(self, context: "PipelineContext") -> "PipelineContext":
        """
        Generate follow-up question or closing message.

        Args:
            context: Turn context with should_continue, focus_concept, recent_utterances

        Returns:
            Modified context with next_question
        """
        # Validate Stage 6 (StrategySelectionStage) completed first
        if context.strategy_selection_output is None:
            raise RuntimeError(
                "Pipeline contract violation: QuestionGenerationStage (Stage 8) requires "
                "StrategySelectionStage (Stage 6) to complete first."
            )

        # Validate Stage 7 (ContinuationStage) completed first
        if context.continuation_output is None:
            raise RuntimeError(
                "Pipeline contract violation: QuestionGenerationStage (Stage 8) requires "
                "ContinuationStage (Stage 7) to complete first."
            )

        if (
            context.should_continue
            or context.strategy_selection_output.generates_closing_question
        ):
            # Add current utterance to recent for context
            updated_utterances = context.recent_utterances + [
                {"speaker": "user", "text": context.user_input}
            ]

            # Get values from contract outputs
            strategy = context.strategy_selection_output.strategy
            focus_concept = context.continuation_output.focus_concept

            next_question = await self.question.generate_question(
                focus_concept=focus_concept,
                recent_utterances=updated_utterances,
                graph_state=context.graph_state,
                recent_nodes=context.recent_nodes,
                strategy=strategy,
                topic=context.concept_name,  # Anchor questions to research topic
            )
        else:
            next_question = "Thank you for sharing your thoughts with me today. This has been very helpful."

        # Create contract output (single source of truth)
        # No need to set individual fields - they're derived from the contract
        # TODO: Track has_llm_fallback when QuestionService supports it
        context.question_generation_output = QuestionGenerationOutput(
            question=next_question,
            strategy=context.strategy_selection_output.strategy,
            focus=context.strategy_selection_output.focus,
            has_llm_fallback=False,  # TODO: Track actual LLM fallback usage
            # timestamp auto-set
        )

        log.debug(
            "question_generated",
            session_id=context.session_id,
            should_continue=context.should_continue,
            question_length=len(next_question),
        )

        return context
