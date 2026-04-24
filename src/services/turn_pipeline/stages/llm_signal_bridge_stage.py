"""Stage 4.7: Await LLM prefetch task, run concept-to-node bridge, emit contract.

Awaits the asyncio.Task fired by LLMPrefetchStage (Stage 3.1), routes per-concept
elaboration/charge ratings into NodeStateTracker via concept_to_node_id, and emits
an LLMSignalBridgeOutput contract on PipelineContext.

This is the earliest point where all bridge dependencies are satisfied:
- concept_to_node_id: populated by GraphUpdateStage (Stage 4)
- NodeStateTracker keys: registered by Stage 4 + Stage 4.5 (SlotDiscoveryStage)
- LLM results: fired after Stage 3, awaited here

Error handling: if the LLM task failed (network error, API timeout, invalid JSON),
emits contract with bridge_applied=False and error field set. Downstream stages
(StrategySelectionStage) fall back to neutral signal defaults without crashing.
"""

from typing import TYPE_CHECKING

import structlog

from ..base import TurnStage
from src.domain.models.pipeline_contracts import LLMSignalBridgeOutput

if TYPE_CHECKING:
    from ..context import PipelineContext

log = structlog.get_logger(__name__)


class LLMSignalBridgeStage(TurnStage):
    """Await LLM prefetch task and bridge per-concept ratings to node tracker."""

    async def process(self, context: "PipelineContext") -> "PipelineContext":
        prefetch_task = getattr(context, "_llm_prefetch_task", None)

        if prefetch_task is None:
            log.debug(
                "llm_bridge_skipped_no_task",
                session_id=context.session_id,
            )
            context.llm_signal_bridge_output = LLMSignalBridgeOutput()
            return context

        # Await the LLM batch task
        try:
            llm_result = await prefetch_task
        except Exception as e:
            log.error(
                "llm_prefetch_failed",
                session_id=context.session_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            context.llm_signal_bridge_output = LLMSignalBridgeOutput(
                error=str(e),
            )
            return context

        global_signals = llm_result.get("global", {})
        per_concept_raw = llm_result.get("concepts", {})

        # Normalize concept keys to lowercase to match concept_to_node_id map
        per_concept_ratings = {str(k).lower(): v for k, v in per_concept_raw.items()}

        # Bridge: route per-concept ratings → NodeStateTracker.append_quality
        concept_to_node_id = getattr(context, "concept_to_node_id", {}) or {}
        node_tracker = context.node_tracker
        bridged_count = 0

        if node_tracker:
            for concept_key, ratings in per_concept_ratings.items():
                node_id = concept_to_node_id.get(concept_key)
                if not node_id:
                    continue
                elaboration = ratings.get("response.semantic.llm.elaboration")
                charge = ratings.get("response.semantic.llm.charge")
                if elaboration is None and charge is None:
                    continue
                await node_tracker.append_quality(
                    node_id=node_id,
                    elaboration=float(elaboration) if elaboration is not None else 0.0,
                    charge=float(charge) if charge is not None else 0.0,
                )
                bridged_count += 1

        context.llm_signal_bridge_output = LLMSignalBridgeOutput(
            global_signals=global_signals,
            per_concept_ratings=per_concept_ratings,
            bridge_applied=bridged_count > 0,
            bridged_count=bridged_count,
        )

        log.info(
            "llm_bridge_complete",
            session_id=context.session_id,
            bridge_applied=bridged_count > 0,
            bridged_count=bridged_count,
            total_ratings=len(per_concept_ratings),
            global_signal_count=len(global_signals),
        )

        return context
