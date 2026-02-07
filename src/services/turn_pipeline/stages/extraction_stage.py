"""
Stage 3: Extract concepts and relationships.

ADR-008 Phase 3: Use ExtractionService to extract knowledge from user input.
Phase 6: Output ExtractionOutput contract.
"""

import structlog

from ..base import TurnStage
from ..context import PipelineContext
from src.core.exceptions import ConfigurationError
from src.domain.models.pipeline_contracts import ExtractionOutput, SrlPreprocessingOutput
from src.services.extraction_service import ExtractionService

log = structlog.get_logger(__name__)


class ExtractionStage(TurnStage):
    """
    Extract concepts and relationships from user input.

    Populates PipelineContext.extraction.
    """

    def __init__(self, extraction_service: ExtractionService):
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
        # Validate Stage 2 (UtteranceSavingStage) completed first
        if context.utterance_saving_output is None:
            raise RuntimeError(
                "Pipeline contract violation: ExtractionStage (Stage 3) requires "
                "UtteranceSavingStage (Stage 2) to complete first."
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
            except FileNotFoundError:
                # Concept file not found - this is a configuration error
                raise ConfigurationError(
                    f"Concept '{context.concept_id}' not found. "
                    f"Ensure concept YAML exists in concepts/ directory."
                )
            except Exception as e:
                raise ConfigurationError(
                    f"Failed to load concept '{context.concept_id}': {e}"
                ) from e

        # Get source utterance ID for traceability (ADR-010 Phase 2)
        source_utterance_id = (
            context.user_utterance.id
            if hasattr(context, "user_utterance") and context.user_utterance
            else None
        )

        # Format extraction context with optional SRL hints
        extraction_context = self._format_context_for_extraction(context)

        extraction = await self.extraction.extract(
            text=context.user_input,
            methodology=context.methodology,
            context=extraction_context,
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

        Phase 1: Optionally inject SRL hints if available.

        Args:
            context: Turn context

        Returns:
            Context string with optional SRL structural analysis
        """
        if not context.recent_utterances:
            # Check for SRL hints even without conversation history
            srl_hints = self._format_srl_hints(context.srl_preprocessing_output)
            return srl_hints if srl_hints else ""

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

        # Inject SRL hints if available
        srl_hints = self._format_srl_hints(context.srl_preprocessing_output)
        if srl_hints:
            lines.append("")
            lines.append(srl_hints)
            log.debug(
                "srl_context_added",
                session_id=context.session_id,
                approximate_token_count=len(srl_hints) // 4,  # Rough estimate
            )

        return "\n".join(lines)

    def _format_srl_hints(self, srl_output: SrlPreprocessingOutput | None) -> str:
        """
        Format SRL preprocessing output into extraction hints.

        Args:
            srl_output: SRL preprocessing output (may be None or empty)

        Returns:
            Formatted structural analysis section, or empty string if no data
        """
        if not srl_output:
            return ""

        # Check if there's actually any data
        if not srl_output.discourse_relations and not srl_output.srl_frames:
            return ""

        lines = ["## STRUCTURAL ANALYSIS (use to guide relationship extraction):"]

        # Add discourse relations (causal/temporal markers)
        if srl_output.discourse_relations:
            lines.append("")
            lines.append("Causal/temporal markers detected:")
            for rel in srl_output.discourse_relations:
                marker = rel.get("marker", "implicit")
                antecedent = rel.get("antecedent", "")[:60]  # Truncate for readability
                consequent = rel.get("consequent", "")[:60]
                lines.append(f"  - [{marker}]: \"{antecedent}\" → \"{consequent}\"")

        # Add SRL frames (predicate-argument structures)
        # Limit to top 5 to avoid prompt bloat
        if srl_output.srl_frames:
            frames_to_show = srl_output.srl_frames[:5]
            lines.append("")
            lines.append("Predicate-argument structures:")
            for frame in frames_to_show:
                predicate = frame.get("predicate", "")
                arguments = frame.get("arguments", {})
                arg_str = ", ".join([f"{k}={v}" for k, v in arguments.items()])
                lines.append(f"  - {predicate}: {arg_str}")

        return "\n".join(lines)
