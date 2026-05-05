"""Stage 4.6: Await edge extraction prefetch, persist edges, update tracker.

Awaits the asyncio.Task fired by EdgeExtractionPrefetchStage (Stage 4.5B-prefetch),
persists confirmed edges via GraphService._add_edge_from_relationship (B6 overload),
and updates the evolving NodeStateTracker with edge-count deltas.

Runs AFTER SlotDiscoveryStage and BEFORE LLMSignalBridgeStage.
SlotDiscovery runs while the edge extraction Haiku (fired at 4.5B) is in-flight.
LLMSignalBridgeStage seals the tracker after this stage completes, so edge-count
mutations here are visible to all downstream signal detectors (Stages 5+).

Per D4: record_yield ownership moves here from GraphUpdateStage (implemented in B7).
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

import structlog  # type: ignore[import-untyped]

from ..base import TurnStage
from src.domain.models.edge_extraction import EdgeExtractionOutput
from src.services.node_state_tracker import (
    NodeStateTracker,
    GraphChangeSummary,
    NodeNotTrackedError,
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
    ):
        self._graph = graph_service
        self._graph_repo = graph_repo

    async def process(self, context: "PipelineContext") -> "PipelineContext":
        # Seed tracker from evolving state; fall back to empty if not seeded
        tracker: NodeStateTracker = context._evolving_node_tracker or NodeStateTracker()

        task = getattr(context, "_edge_extraction_task", None)
        edges_added: list = []

        if task is None:
            # No prefetch task fired (flag OFF, no candidates, or setup failure).
            log.debug(
                "edge_extraction_bridge_skipped_no_task",
                session_id=context.session_id,
            )
        else:
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
            else:
                # Per D10: structured logging for rejected and low-confidence edge candidates
                session_id = context.session_id
                turn_number = context.turn_number

                for candidate in result.rejected_candidates:
                    log.debug(
                        "edge_rejected",
                        session_id=session_id,
                        turn=turn_number,
                        source_node_id=candidate.source_node_id,
                        target_node_id=candidate.target_node_id,
                        rejection_reason=candidate.rejection_reason,
                        reasoning_summary=candidate.reasoning_summary,
                    )

                if result.rejected_candidates:
                    rejection_counts: dict[str, int] = dict(
                        Counter(c.rejection_reason for c in result.rejected_candidates)
                    )
                    log.info(
                        "edge_rejected_summary",
                        session_id=session_id,
                        turn=turn_number,
                        total_rejected=len(result.rejected_candidates),
                        by_reason=rejection_counts,
                    )

                    # Persist rejected candidates for per-turn diagnostics
                    await self._graph_repo.create_rejected_edges_batch(
                        session_id=session_id,
                        turn_number=turn_number,
                        rejected=result.rejected_candidates,
                    )

                for edge in result.confirmed_edges:
                    if edge.confidence == "low":
                        log.info(
                            "edge_low_confidence",
                            session_id=session_id,
                            turn=turn_number,
                            source_node_id=edge.source_node_id,
                            target_node_id=edge.target_node_id,
                            edge_type=edge.edge_type,
                            reasoning_summary=edge.reasoning_summary,
                        )

                # Store parsed result on context for downstream export (turn diagnostics)
                context._edge_extraction_result = result

                # Persist confirmed edges via B6 ConfirmedEdge overload
                methodology = context.methodology

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
                        key = source_id
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
                        key = target_id
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

                # Per D10: summary log with aggregate counts for observability
                log.info(
                    "edge_extraction_bridge_complete",
                    session_id=session_id,
                    turn=turn_number,
                    confirmed_edges=len(result.confirmed_edges),
                    edges_persisted=len(edges_added),
                    rejected_candidates=len(result.rejected_candidates),
                    low_confidence_count=result.low_confidence_count,
                    edge_deltas_count=len(edge_deltas),
                    latency_ms=result.latency_ms,
                )

        # Record yield against previous_focus unconditionally (D4/B7).
        # record_yield represents "the focus produced graph change this turn"
        # and fires exactly once per turn from this stage, after both Stage 4
        # node writes and Stage 4.5B edge writes are complete.
        if tracker.previous_focus:
            graph_changes = GraphChangeSummary(
                nodes_added=0, edges_added=len(edges_added)
            )
            try:
                tracker = tracker.record_yield(
                    tracking_key=tracker.previous_focus,
                    turn_number=context.turn_number,
                    graph_changes=graph_changes,
                )
            except NodeNotTrackedError:
                log.warning(
                    "record_yield_failed_previous_focus_not_found",
                    previous_focus=tracker.previous_focus,
                    turn_number=context.turn_number,
                )

        context._evolving_node_tracker = tracker
        return context
