"""
Stage 3: Extract concepts and relationships.

ADR-008 Phase 3: Use ExtractionService to extract knowledge from user input.
"""

import structlog

from ..base import TurnStage
from ..context import PipelineContext

log = structlog.get_logger(__name__)


class ExtractionStage(TurnStage):
    """
    Extract concepts and relationships from user input.

    Populates PipelineContext.extraction.
    """

    def __init__(self, extraction_service):
        """
        Initialize stage.

        Args:
            extraction_service: ExtractionService instance
        """
        self.extraction = extraction_service

    async def process(self, context: "PipelineContext") -> "PipelineContext":
        """
        Extract concepts/relationships from user input.

        Args:
            context: Turn context with user_input and recent_utterances

        Returns:
            Modified context with extraction result
        """
        # Update extraction service with concept_id from session context
        # This allows element linking to work with the correct concept
        if hasattr(context, "concept_id") and context.concept_id:
            self.extraction.concept_id = context.concept_id
            # Reload concept for element linking
            try:
                from src.core.concept_loader import load_concept, get_element_alias_map

                self.extraction.concept = load_concept(context.concept_id)
                self.extraction.element_alias_map = get_element_alias_map(
                    self.extraction.concept
                )
                log.debug(
                    "extraction_concept_loaded",
                    concept_id=context.concept_id,
                    element_count=len(self.extraction.concept.elements),
                )
            except Exception as e:
                log.warning(
                    "concept_load_failed",
                    concept_id=context.concept_id,
                    error=str(e),
                )

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

    def _format_context_for_extraction(self, context: "PipelineContext") -> str:
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
