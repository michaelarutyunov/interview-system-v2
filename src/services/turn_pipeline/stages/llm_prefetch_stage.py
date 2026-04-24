"""Stage 3.1: Fire LLM batch signal call asynchronously after extraction.

Creates an asyncio.Task for the LLM batch detection call and stores it on
PipelineContext. The task is NOT awaited here — Stage 4.7 (LLMSignalBridgeStage)
awaits it after graph state is ready.

This removes ~300-600ms of LLM latency from the critical path by overlapping
the LLM call with Stages 4-4.5 (graph update, slot discovery).
"""

import asyncio
from typing import TYPE_CHECKING, Any, List, Optional, Type

import structlog

from ..base import TurnStage
from src.methodologies import get_registry

if TYPE_CHECKING:
    from ..context import PipelineContext
    from src.signals.llm.llm_signal_base import BaseLLMSignal

log = structlog.get_logger(__name__)


class LLMPrefetchStage(TurnStage):
    """Fire LLM batch signal call as asyncio.Task after Stage 3 (extraction).

    Dependencies (all available after Stage 3):
    - response_text: context.user_input (Stage 2)
    - concepts: context.extraction_output.extraction.concepts (Stage 3)
    - question: last system utterance from context.recent_utterances (Stage 1)
    - signal_classes: derived from methodology config
    """

    def __init__(self):
        self._methodology_registry = get_registry()

    async def process(self, context: "PipelineContext") -> "PipelineContext":
        if not context.extraction_output or not context.extraction_output.extraction:
            log.debug(
                "llm_prefetch_skipped_no_extraction",
                session_id=context.session_id,
            )
            context._llm_prefetch_task = None
            return context

        methodology_name = context.methodology
        config = self._methodology_registry.get_methodology(methodology_name)
        if not config:
            log.warning(
                "llm_prefetch_skipped_no_methodology",
                session_id=context.session_id,
                methodology=methodology_name,
            )
            context._llm_prefetch_task = None
            return context

        # Determine which LLM signal classes this methodology uses
        llm_signal_classes = self._get_llm_signal_classes(config)
        if not llm_signal_classes:
            log.debug(
                "llm_prefetch_skipped_no_llm_signals",
                session_id=context.session_id,
                methodology=methodology_name,
            )
            context._llm_prefetch_task = None
            return context

        # Create LLMBatchDetector with signal_scoring LLM client
        from src.signals.llm.batch_detector import LLMBatchDetector

        try:
            from src.llm.client import get_llm_client

            scoring_client = get_llm_client("signal_scoring")
            llm_detector = LLMBatchDetector(scoring_client)
        except Exception as e:
            log.error(
                "llm_prefetch_setup_failed",
                session_id=context.session_id,
                error=str(e),
            )
            context._llm_prefetch_task = None
            return context

        # Gather inputs
        response_text = context.user_input or ""
        concepts = list(context.extraction_output.extraction.concepts or [])

        question = self._extract_last_question(context)

        # Fire as asyncio.Task — not awaited here
        context._llm_prefetch_task = asyncio.create_task(
            llm_detector.detect(
                response_text=response_text,
                question=question or "",
                concepts=concepts,
                signal_classes=llm_signal_classes,
            )
        )

        log.info(
            "llm_prefetch_fired",
            session_id=context.session_id,
            methodology=methodology_name,
            concept_count=len(concepts),
            signal_classes=len(llm_signal_classes),
        )

        return context

    def _get_llm_signal_classes(self, config: Any) -> List[Type["BaseLLMSignal"]]:
        """Get LLM signal classes configured for this methodology."""
        from src.signals.llm.decorator import _registered_llm_signals

        # Collect all signal names from methodology config
        signal_names: list[str] = []
        for pool_signals in config.signals.values():
            signal_names.extend(pool_signals)

        # Filter to only LLM signals and get their classes
        llm_classes = []
        for name in signal_names:
            if name in _registered_llm_signals:
                llm_classes.append(_registered_llm_signals[name])

        return llm_classes

    def _extract_last_question(self, context: "PipelineContext") -> Optional[str]:
        """Get the last system utterance (interviewer question) from history."""
        if not context.recent_utterances:
            return None
        for utt in reversed(context.recent_utterances):
            if utt.get("speaker") == "system":
                return utt.get("text")
        return None
