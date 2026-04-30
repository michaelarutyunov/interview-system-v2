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

    # Bridge target descriptions keyed by bridge_target config value
    _BRIDGE_TARGET_DESCRIPTIONS: dict[str, str] = {
        "most_concrete": (
            "the most concrete new concept you extracted (the one closest "
            "to the question's level, not the most abstract one the "
            "respondent mentioned)"
        ),
        "most_abstract": (
            "the most abstract new concept you extracted (the one furthest "
            "from the question level, the highest-level concept the "
            "respondent mentioned)"
        ),
        "either": (
            "whichever new concept forms the most meaningful relationship "
            "to the focus"
        ),
    }

    def __init__(
        self,
        extraction_service: ExtractionService,
        methodology_registry=None,
    ):
        """
        Initialize stage.

        Args:
            extraction_service: ExtractionService instance
            methodology_registry: Optional MethodologyRegistry for strategy config lookup
        """
        self.extraction = extraction_service
        self._methodology_registry = methodology_registry

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

        Assembles three sections in order:
        1. Conversation turns (last 5)
        2. Existing node labels — shown BEFORE the task instruction so the LLM
           can reference exact labels when it reads the bridge instruction
        3. Bridge task instruction — pins the source_text to the previous turn's
           focus node label rather than asking the LLM to infer "the question's topic"

        Optionally injects SRL hints if available from preprocessing stage.

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

        # Inject existing node labels BEFORE the bridge task instruction so the
        # LLM sees the exact label list when it reads the source_text constraint.
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

        # Bridge task instruction: only when there is a previous-turn focus node
        # and the most recent utterance is an interviewer question.
        # Uses the explicit focus node label so the LLM doesn't have to infer
        # "the question's topic" from raw question text — preventing interviewer-
        # introduced concepts from entering the graph as new nodes.
        # Bridge direction, target, and extraction mode are read from the
        # previous turn's strategy config (bridge_direction/bridge_target/extraction_mode).
        if len(recent) >= 1 and recent[-1]["speaker"] == "system":
            focus_label, _, prev_strategy = self._get_previous_focus(context)
            lines.append("")
            lines.append(f"[Most recent question] Interviewer: {recent[-1]['text']}")

            # Revitalize: suppress bridge entirely — previous focus was abandoned
            if prev_strategy == "revitalize": # TODO veirfy against concept separation principles
                lines.append(
                    "[Task] Extract concepts ONLY from the Respondent's answer above. "
                    "This is a new topic — extract fresh concepts without forcing a "
                    "relationship to previous graph nodes. "
                    "Do NOT extract new concepts from the interviewer's question text."
                )
            elif focus_label:
                # Read bridge parameters from strategy config
                bridge_config = self._get_bridge_config(
                    context.methodology, prev_strategy
                )
                bridge_dir = bridge_config.get("bridge_direction", "forward")
                bridge_target = bridge_config.get("bridge_target", "most_concrete")
                extraction_mode = bridge_config.get("extraction_mode", "extract_new")

                target_desc = self._BRIDGE_TARGET_DESCRIPTIONS.get(
                    bridge_target,
                    self._BRIDGE_TARGET_DESCRIPTIONS["most_concrete"],
                )

                if bridge_dir == "backward":
                    bridge_clause = (
                        f"Then create cross-turn relationships using {target_desc} "
                        f'→ target_text="{focus_label}" '
                        f"(the concept the question probed)."
                    )
                else:
                    bridge_clause = (
                        f"Then create cross-turn relationships using "
                        f'source_text="{focus_label}" '
                        f"(the concept the question probed) → {target_desc}."
                    )

                if extraction_mode == "prefer_existing":
                    extraction_instruction = (
                        "Focus on extracting relationships to existing graph nodes "
                        "rather than new concepts. "
                    )
                else:
                    extraction_instruction = (
                        "If the response introduces concepts at multiple levels below "
                        "the focus, create relationships for each. "
                    )

                task = (
                    f"[Task] Extract concepts ONLY from the Respondent's answer above. "
                    f"{extraction_instruction}"
                    f"{bridge_clause} "
                    f"Do NOT extract new concepts from the interviewer's question text."
                )
                lines.append(task)
            else:
                # Turn 1 or no focus history: generic bridge without pinned source
                lines.append(
                    "[Task] Extract concepts ONLY from the Respondent's answer above. "
                    "Do NOT extract new concepts from the interviewer's question text."
                )

        return "\n".join(lines)

    def _get_previous_focus(self, context: "PipelineContext") -> tuple[str, str, str]:
        """Return (label, node_type, strategy) from the previous turn's focus entry.

        The question the respondent just answered was generated around this node.
        Passing the label explicitly into the bridge instruction prevents the
        extractor from inferring (and potentially hallucinating) the source concept
        from the raw question text. The strategy enables bridge parameter lookup.

        Args:
            context: Turn context with context_loading_output.focus_history

        Returns:
            (label, node_type, strategy) — empty strings if no prior focus exists
        """
        focus_history = (
            context.context_loading_output.focus_history
            if context.context_loading_output
            else []
        )
        if not focus_history:
            return ("", "", "")
        last_focus = focus_history[-1]
        return (
            last_focus.label or "",
            last_focus.node_type or "",
            last_focus.strategy or "",
        )

    def _get_bridge_config(
        self, methodology: str, strategy: str
    ) -> dict[str, str]:
        """Read bridge parameters from the strategy's YAML config.

        Returns a dict with bridge_direction, bridge_target, and extraction_mode.
        Falls back to defaults if the registry is unavailable or the strategy
        is not found.

        Args:
            methodology: Methodology name (e.g. "jobs_to_be_done_v2")
            strategy: Strategy name (e.g. "ascend")

        Returns:
            Dict with bridge_direction, bridge_target, extraction_mode
        """
        registry = self._methodology_registry
        if registry is None:
            from src.methodologies import get_registry
            registry = get_registry()
        try:
            config = registry.get_methodology(methodology)
        except Exception:
            return {}
        for s in config.strategies:
            if s.name == strategy:
                return {
                    "bridge_direction": s.bridge_direction,
                    "bridge_target": s.bridge_target,
                    "extraction_mode": s.extraction_mode,
                }
        return {}

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

        # Limit to most recent N labels to avoid prompt bloat (configurable)
        from src.core.config import interview_config

        limit = interview_config.session_service.extraction_node_label_limit
        labels_to_show = labels[-limit:] if limit > 0 else []
        label_items = "\n".join(f'  - "{label}"' for label in labels_to_show)

        return (
            f"[Existing graph concepts from previous turns]\n"
            f"{label_items}\n"
            f"When creating relationships, you may reference these exact labels as source_text "
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
