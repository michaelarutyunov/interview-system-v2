"""
Stage 8: Generate follow-up question.

ADR-008 Phase 3: Use QuestionService to generate next question.
Phase 6: Output QuestionGenerationOutput contract.
"""

from typing import TYPE_CHECKING

import structlog

from ..base import TurnStage
from src.domain.models.pipeline_contracts import QuestionGenerationOutput


if TYPE_CHECKING:
    from ..context import PipelineContext
log = structlog.get_logger(__name__)


class QuestionGenerationStage(TurnStage):
    """
    Generate follow-up question.

    Populates PipelineContext.next_question.
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
        Generate follow-up question or closing message.

        Args:
            context: Turn context with should_continue, focus_concept, recent_utterances

        Returns:
            Modified context with next_question
        """
        if context.should_continue:
            # Add current utterance to recent for context
            updated_utterances = context.recent_utterances + [
                {"speaker": "user", "text": context.user_input}
            ]

            next_question = await self.question.generate_question(
                focus_concept=context.focus_concept,
                recent_utterances=updated_utterances,
                graph_state=context.graph_state,
                recent_nodes=context.recent_nodes,
                strategy=context.strategy,
                topic=context.concept_name,  # Anchor questions to research topic
            )
        else:
            next_question = "Thank you for sharing your thoughts with me today. This has been very helpful."

        # Create contract output (single source of truth)
        # No need to set individual fields - they're derived from the contract
        # TODO: Track has_llm_fallback when QuestionService supports it
        context.question_generation_output = QuestionGenerationOutput(
            question=next_question,
            strategy=context.strategy,
            focus=context.focus,
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
