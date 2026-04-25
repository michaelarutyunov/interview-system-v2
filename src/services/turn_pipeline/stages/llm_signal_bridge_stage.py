"""Stage 4.7: Await LLM prefetch task, run concept-to-node bridge, seal tracker.

Awaits the asyncio.Task fired by LLMPrefetchStage (Stage 3.1), routes per-concept
elaboration/charge ratings into NodeStateTracker via concept_to_node_id, and seals
the evolving tracker into LLMSignalBridgeOutput.sealed_node_tracker.

After this stage completes, _evolving_node_tracker is set to None. All downstream
stages (5–10) read the sealed snapshot via context.node_tracker.

Error handling: if the LLM task failed (network error, API timeout, invalid JSON),
emits contract with bridge_applied=False and error field set. The sealed tracker is
still emitted — it carries whatever state Stages 4 and 4.5 built up this turn.
"""

from typing import TYPE_CHECKING, Optional

import structlog

from ..base import TurnStage
from src.domain.models.pipeline_contracts import LLMSignalBridgeOutput
from src.services.node_state_tracker import CanonicalSlotResolver, NodeNotTrackedError, NodeStateTracker

if TYPE_CHECKING:
    from ..context import PipelineContext

log = structlog.get_logger(__name__)


class LLMSignalBridgeStage(TurnStage):
    """Await LLM prefetch task, bridge per-concept ratings to tracker, then seal."""

    def __init__(self, canonical_slot_resolver: Optional[CanonicalSlotResolver] = None) -> None:
        self._resolver = canonical_slot_resolver or CanonicalSlotResolver()

    async def process(self, context: "PipelineContext") -> "PipelineContext":
        # Seed tracker from _evolving_node_tracker; fall back to empty if not seeded
        tracker: NodeStateTracker = context._evolving_node_tracker or NodeStateTracker()

        # Record canonical_slot_first_seen for any slot newly present this turn
        turn_number = context.turn_number
        for slot_id in tracker.states:
            tracker = tracker.record_canonical_slot_first_seen(slot_id, turn_number)

        prefetch_task = getattr(context, "_llm_prefetch_task", None)

        if prefetch_task is None:
            log.debug("llm_bridge_skipped_no_task", session_id=context.session_id)
            context.llm_signal_bridge_output = LLMSignalBridgeOutput(
                sealed_node_tracker=tracker,
            )
            context._evolving_node_tracker = None
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
                sealed_node_tracker=tracker,
            )
            context._evolving_node_tracker = None
            return context

        global_signals = llm_result.get("global", {})
        per_concept_raw = llm_result.get("concepts", {})
        per_concept_ratings = {str(k).lower(): v for k, v in per_concept_raw.items()}

        # Bridge: route per-concept ratings → tracker.append_quality (functional)
        concept_to_node_id: dict = getattr(context, "concept_to_node_id", {}) or {}
        bridged_count = 0

        for concept_key, ratings in per_concept_ratings.items():
            node_id = concept_to_node_id.get(concept_key)
            if not node_id:
                continue
            elaboration = ratings.get("response.semantic.llm.elaboration")
            charge = ratings.get("response.semantic.llm.charge")
            if elaboration is None and charge is None:
                continue

            tracking_key = await self._resolver.resolve(node_id)
            try:
                tracker = tracker.append_quality(
                    tracking_key=tracking_key,
                    elaboration=float(elaboration) if elaboration is not None else 0.0,
                    charge=float(charge) if charge is not None else 0.0,
                )
                bridged_count += 1
            except NodeNotTrackedError:
                log.warning(
                    "append_quality_failed_node_not_found",
                    node_id=node_id,
                    tracking_key=tracking_key,
                )

        # SEAL — tracker is immutable from this point on
        context.llm_signal_bridge_output = LLMSignalBridgeOutput(
            global_signals=global_signals,
            per_concept_ratings=per_concept_ratings,
            bridge_applied=bridged_count > 0,
            bridged_count=bridged_count,
            sealed_node_tracker=tracker,
        )
        context._evolving_node_tracker = None

        log.info(
            "llm_bridge_complete",
            session_id=context.session_id,
            bridge_applied=bridged_count > 0,
            bridged_count=bridged_count,
            total_ratings=len(per_concept_ratings),
            global_signal_count=len(global_signals),
        )

        return context
