"""
Stage 3: Extract concepts and relationships.

ADR-008 Phase 3: Use ExtractionService to extract knowledge from user input.
Phase 6: Output ExtractionOutput contract.
"""

import structlog

from ..base import TurnStage
from ..context import PipelineContext
from src.domain.models.pipeline_contracts import ExtractionOutput

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
        # Update extraction service with methodology from session context
        # This fixes P0 Issue 3: Methodology Mismatch
        if hasattr(context, "methodology") and context.methodology:
            if context.methodology != self.extraction.methodology:
                log.info(
                    "extraction_methodology_updated",
                    old_methodology=self.extraction.methodology,
                    new_methodology=context.methodology,
                )
                self.extraction.methodology = context.methodology
                # Reload methodology schema
                try:
                    from src.core.schema_loader import load_methodology

                    self.extraction.schema = load_methodology(context.methodology)
                    log.debug(
                        "extraction_schema_reloaded",
                        methodology=context.methodology,
                        node_types=len(self.extraction.schema.node_types),
                    )
                except Exception as e:
                    log.error(
                        "methodology_schema_load_failed",
                        methodology=context.methodology,
                        error=str(e),
                    )

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

        # Get source utterance ID for traceability (ADR-010 Phase 2)
        source_utterance_id = (
            context.user_utterance.id
            if hasattr(context, "user_utterance") and context.user_utterance
            else None
        )

        extraction = await self.extraction.extract(
            text=context.user_input,
            context=self._format_context_for_extraction(context),
            source_utterance_id=source_utterance_id,
        )

        # Create contract output (single source of truth)
        # No need to set individual fields - they're derived from the contract
        context.extraction_output = ExtractionOutput(
            extraction=extraction,
            methodology=context.methodology,
            # timestamp, concept_count, relationship_count auto-set
        )

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

        P0 Fix: Enhanced to highlight interviewer's most recent question
        for conversational implicit relationship extraction.

        Args:
            context: Turn context

        Returns:
            Context string
        """
        if not context.recent_utterances:
            return ""

        lines = []

        # Include last 5 turns for full context
        recent = context.recent_utterances[-5:]
        for utt in recent:
            speaker = "Respondent" if utt["speaker"] == "user" else "Interviewer"
            lines.append(f"{speaker}: {utt['text']}")

        # Highlight the most recent interviewer question if present
        # This helps LLM create implicit Q→A relationships (laddering)
        if len(recent) >= 1 and recent[-1]["speaker"] == "system":
            interviewer_question = recent[-1]["text"]
            lines.append("")
            lines.append(f"[Most recent question] Interviewer: {interviewer_question}")
            lines.append(
                "[Task] Extract concepts from the Respondent's answer AND create a relationship from the question's topic to the answer concept."
            )

        return "\n".join(lines)
