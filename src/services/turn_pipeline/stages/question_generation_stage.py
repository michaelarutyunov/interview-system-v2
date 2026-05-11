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
            # Get values from contract outputs
            strategy = context.strategy_selection_output.strategy
            focus_raw = context.continuation_output.focus_concept

            # Add current utterance to recent for context
            updated_utterances = context.recent_utterances + [
                {"speaker": "user", "text": context.user_input}
            ]

            # Resolve strategy config for flag-driven behavior
            strategy_config = None
            is_conversation_level = False
            try:
                from src.methodologies import get_registry

                registry = get_registry()
                meth_config = registry.get_methodology(context.methodology)
                strategy_config = next(
                    (s for s in meth_config.strategies if s.name == strategy), None
                )
                if strategy_config and strategy_config.node_binding == "none":
                    is_conversation_level = True
            except Exception:
                pass

            # If the strategy requests last system utterance prepend, do so before
            # applying the window. This replaces the old hardcoded revitalize check.
            if (
                strategy_config
                and strategy_config.history_includes_last_system_utterance
            ):
                opening = next(
                    (
                        u
                        for u in context.recent_utterances
                        if u.get("speaker") == "system"
                    ),
                    None,
                )
                if opening and opening not in updated_utterances:
                    updated_utterances = [opening] + updated_utterances
            # Keep within the last-5 window after any prepending
            updated_utterances = updated_utterances[-5:]

            if is_conversation_level:
                # Conversation-level strategies don't need a focus node.
                # Use a dedicated Haiku-friendly prompt path.
                focus_concept = None
                if isinstance(focus_raw, dict):
                    focus_concept = focus_raw.get("label", "")
                elif isinstance(focus_raw, str) and focus_raw:
                    focus_concept = focus_raw

                next_question = (
                    await self.question.generate_conversation_level_question(
                        strategy=strategy,
                        recent_utterances=updated_utterances,
                        topic=context.concept_name,
                        focus_node_label=focus_concept or None,
                    )
                )
            else:
                # Node-bound strategies use the existing focus-concept-driven path.
                # Unpack focus concept — dict (new) or string (backward compat)
                if isinstance(focus_raw, dict):
                    focus_concept = focus_raw.get("label", "")
                    focus_node_type = focus_raw.get("node_type")
                    focus_source_quote = focus_raw.get("source_quote", "")
                else:
                    focus_concept = focus_raw or ""
                    focus_node_type = None
                    focus_source_quote = ""

                # Look up ontology level for the focus node type
                focus_node_level = None
                if focus_node_type:
                    try:
                        from src.core.schema_loader import load_methodology

                        schema = load_methodology(context.methodology)
                        focus_node_level = schema.get_level_for_node_type(
                            focus_node_type
                        )
                    except Exception:
                        pass

                # Extract level_guidance from strategy config for node-type-specific prompts
                level_guidance: dict[str, str] = {}
                try:
                    from src.methodologies import get_registry

                    registry = get_registry()
                    config = registry.get_methodology(context.methodology)
                    strategy_obj = next(
                        (s for s in config.strategies if s.name == strategy), None
                    )
                    if strategy_obj:
                        level_guidance = strategy_obj.level_guidance
                except Exception:
                    pass

                # Build signal descriptions from active signals
                signal_descriptions = None
                if context.signals:
                    from src.signals.signal_base import SignalDetector

                    registry_sig = SignalDetector.get_registered_signals()
                    signal_descriptions = {
                        name: cls.description
                        for name, cls in registry_sig.items()
                        if name in context.signals
                    }

                next_question = await self.question.generate_question(
                    focus_concept=focus_concept,
                    recent_utterances=updated_utterances,
                    graph_state=context.graph_state,
                    recent_nodes=context.recent_nodes,
                    strategy=strategy,
                    topic=context.concept_name,
                    focus_node_type=focus_node_type,
                    focus_node_level=focus_node_level,
                    focus_source_quote=focus_source_quote,
                    signals=context.signals,
                    signal_descriptions=signal_descriptions or None,
                    level_guidance=level_guidance,
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
