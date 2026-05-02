"""Stage 4.6: Await edge extraction prefetch, persist edges, update tracker.

Awaits the asyncio.Task fired by EdgeExtractionPrefetchStage (Stage 4.5B-prefetch),
persists confirmed edges via GraphService._add_edge_from_relationship (B6 overload),
and updates the evolving NodeStateTracker with edge-count deltas.

Per D3 ordering: runs AFTER SlotDiscoveryStage and BEFORE LLMSignalBridgeStage.
LLMSignalBridgeStage seals the tracker after this stage completes, so edge-count
mutations here are visible to all downstream signal detectors (Stages 5+).

Per D4: record_yield ownership moves here from GraphUpdateStage (implemented in B7).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import structlog  # type: ignore[import-untyped]

from ..base import TurnStage
from src.domain.models.edge_extraction import EdgeExtractionOutput
from src.services.node_state_tracker import (
    CanonicalSlotResolver,
    NodeStateTracker,
)

if TYPE_CHECKING:
    from ..context import PipelineContext

log = structlog.get_logger(__name__)


class EdgeExtractionBridgeStage(TurnStage):
    """Await edge extraction prefetch, persist confirmed edges, update tracker.

    Wired unconditionally in the pipeline. When _edge_extraction_task is None
    (flag OFF, no candidates, or prefetch setup failure), this stage is a no-op.
    """

    def __init__(
        self,
        graph_service,
        graph_repo,
        canonical_slot_resolver: Optional[CanonicalSlotResolver] = None,
    ):
        self._graph = graph_service
        self._graph_repo = graph_repo
        self._resolver = canonical_slot_resolver or CanonicalSlotResolver()

    async def process(self, context: "PipelineContext") -> "PipelineContext":
        # Seed tracker from evolving state; fall back to empty if not seeded
        tracker: NodeStateTracker = context._evolving_node_tracker or NodeStateTracker()

        task = getattr(context, "_edge_extraction_task", None)

        if task is None:
            # No prefetch task fired (flag OFF, no candidates, or setup failure).
            # TODO(B7): record_yield will move here from GraphUpdateStage (D4).
            # When moved, call unconditionally even when task is None to ensure
            # previous_focus always gets yield credit. Pattern:
            #   graph_changes = GraphChangeSummary(nodes_added=0, edges_added=0)
            #   if tracker.previous_focus:
            #       tracker = tracker.record_yield(
            #           tracking_key=tracker.previous_focus,
            #           turn_number=context.turn_number,
            #           graph_changes=graph_changes,
            #       )
            log.debug(
                "edge_extraction_bridge_skipped_no_task",
                session_id=context.session_id,
            )
            context._evolving_node_tracker = tracker
            return context

        # Await the edge extraction task
        try:
            result: EdgeExtractionOutput = await task
        except Exception as e:
            log.error(
                "edge_extraction_task_failed",
                session_id=context.session_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            # TODO(B7): record_yield unconditional call site (see above)
            context._evolving_node_tracker = tracker
            return context

        # Persist confirmed edges via B6 ConfirmedEdge overload
        session_id = context.session_id
        methodology = context.methodology
        edges_added: list = []

        for edge in result.confirmed_edges:
            try:
                kg_edge = await self._graph._add_edge_from_relationship(
                    session_id=session_id,
                    relationship=edge,  # ConfirmedEdge overload (D5/B6)
                    methodology=methodology,
                )
                if kg_edge is not None:
                    edges_added.append(kg_edge)
            except Exception as e:
                log.warning(
                    "edge_persistence_failed",
                    session_id=session_id,
                    source_node_id=edge.source_node_id,
                    target_node_id=edge.target_node_id,
                    edge_type=edge.edge_type,
                    error=str(e),
                )

        # Build edge_deltas and batch-update tracker
        # Mirrors graph_update_stage.py:151-178 pattern
        edge_deltas: dict[str, tuple[int, int]] = {}
        for kg_edge in edges_added:
            source_id = getattr(kg_edge, "source_node_id", None)
            target_id = getattr(kg_edge, "target_node_id", None)

            if source_id:
                key = await self._resolver.resolve(source_id)
                if key in tracker.states:
                    out_d, in_d = edge_deltas.get(key, (0, 0))
                    edge_deltas[key] = (out_d + 1, in_d)
                else:
                    log.debug(
                        "edge_count_skip_untracked",
                        tracking_key=key,
                        node_id=source_id,
                    )

            if target_id:
                key = await self._resolver.resolve(target_id)
                if key in tracker.states:
                    out_d, in_d = edge_deltas.get(key, (0, 0))
                    edge_deltas[key] = (out_d, in_d + 1)
                else:
                    log.debug(
                        "edge_count_skip_untracked",
                        tracking_key=key,
                        node_id=target_id,
                    )

        if edge_deltas:
            tracker = tracker.update_edge_counts_batch(edge_deltas)

        # TODO(B7): record_yield moved here from GraphUpdateStage (D4).
        # Call unconditionally — even when no edges were added — so that
        # previous_focus always gets yield credit for this turn.
        # Pattern:
        #   graph_changes = GraphChangeSummary(
        #       nodes_added=0, edges_added=len(edges_added)
        #   )
        #   if tracker.previous_focus:
        #       try:
        #           tracker = tracker.record_yield(
        #               tracking_key=tracker.previous_focus,
        #               turn_number=context.turn_number,
        #               graph_changes=graph_changes,
        #           )
        #       except NodeNotTrackedError:
        #           log.warning(...)

        # Audit log: surface counts for observability (full structured logging is B8)
        log.info(
            "edge_extraction_bridge_complete",
            session_id=session_id,
            confirmed_edges=len(result.confirmed_edges),
            edges_persisted=len(edges_added),
            rejected_candidates=len(result.rejected_candidates),
            low_confidence_count=result.low_confidence_count,
            edge_deltas_count=len(edge_deltas),
            latency_ms=result.latency_ms,
        )

        context._evolving_node_tracker = tracker
        return context
