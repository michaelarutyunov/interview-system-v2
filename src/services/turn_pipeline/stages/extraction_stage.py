"""
Stage 3: Extract concepts and relationships.

ADR-008 Phase 3: Use ExtractionService to extract knowledge from user input.
"""

from typing import TYPE_CHECKING

import structlog

from ..base import TurnStage

if TYPE_CHECKING:
    from src.domain.models.turn import TurnContext

log = structlog.get_logger(__name__)


class ExtractionStage(TurnStage):
    """
    Extract concepts and relationships from user input.

    Populates TurnContext.extraction.
    """

    def __init__(self, extraction_service):
        """
        Initialize stage.

        Args:
            extraction_service: ExtractionService instance
        """
        self.extraction = extraction_service

    async def process(self, context: "TurnContext") -> "TurnContext":
        """
        Extract concepts/relationships from user input.

        Args:
            context: Turn context with user_input and recent_utterances

        Returns:
            Modified context with extraction result
        """
        extraction = await self.extraction.extract(
            text=context.user_input,
            context=self._format_context_for_extraction(context),
        )

        context.extraction = extraction

        log.info(
            "extraction_completed",
            session_id=context.session_id,
            concepts_extracted=len(extraction.concepts),
            relationships_extracted=len(extraction.relationships),
        )

        return context

    def _format_context_for_extraction(self, context: "TurnContext") -> str:
        """
        Format context for extraction prompt.

        Args:
            context: Turn context

        Returns:
            Context string
        """
        if not context.recent_utterances:
            return ""

        lines = []
        for utt in context.recent_utterances[-5:]:
            speaker = "Respondent" if utt["speaker"] == "user" else "Interviewer"
            lines.append(f"{speaker}: {utt['text']}")

        return "\n".join(lines)
