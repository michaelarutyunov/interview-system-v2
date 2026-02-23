"""
Stage 3: Extract concepts and relationships.

Uses ExtractionService to extract knowledge from user input, producing
concepts and relationships that will be added to the knowledge graph.
Outputs ExtractionOutput contract for downstream stages.
"""

import structlog

from ..base import TurnStage
from ..context import PipelineContext
from src.core.exceptions import ConfigurationError
from src.domain.models.pipeline_contracts import (
    ExtractionOutput,
    SrlPreprocessingOutput,
)
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
                self.extraction.element_alias_map = get_element_alias_map(self.extraction.concept)
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

        # Get source utterance ID for traceability
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

        Highlights interviewer's most recent question for conversational
        implicit relationship extraction. Optionally injects SRL hints
        if available from preprocessing stage.

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

        # Inject existing node labels for cross-turn relationship bridging
        node_labels = self._format_node_labels(context)
        if node_labels:
            lines.append("")
            lines.append(node_labels)
            log.info(
                "cross_turn_node_context_injected",
                session_id=context.session_id,
                node_label_count=len(
                    context.context_loading_output.recent_node_labels
                    if context.context_loading_output
                    else []
                ),
                context_length=len(node_labels),
            )
        else:
            log.debug(
                "cross_turn_node_context_skipped",
                session_id=context.session_id,
                reason="no_existing_nodes",
            )

        return "\n".join(lines)

    def _format_node_labels(self, context: "PipelineContext") -> str:
        """
        Format existing node labels for cross-turn relationship bridging.

        Provides the LLM with labels of concepts already in the graph
        so it can reference them in relationship source_text/target_text
        fields, enabling cross-turn edge creation.

        Args:
            context: Turn context with recent_node_labels

        Returns:
            Formatted node labels section, or empty string if no nodes
        """
        labels = (
            context.context_loading_output.recent_node_labels
            if context.context_loading_output
            else []
        )
        if not labels:
            return ""

        # Limit to most recent 30 labels to avoid prompt bloat
        labels_to_show = labels[-30:]
        label_items = "\n".join(f'  - "{label}"' for label in labels_to_show)

        return (
            f"[Existing graph concepts from previous turns]\n"
            f"{label_items}\n"
            f"[Task] When creating relationships, you may reference these exact labels as source_text "
            f"or target_text to connect new concepts to existing ones. Do NOT re-extract these as new concepts."
        )

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
                lines.append(f'  - [{marker}]: "{antecedent}" → "{consequent}"')

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
