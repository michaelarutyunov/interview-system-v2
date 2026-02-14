"""
Stage 5: Compute graph state and saturation metrics.

Refreshes graph state after graph updates, computes saturation metrics for
interview continuation decisions, and tracks computation timestamp for
freshness validation. Optionally computes canonical graph state for
dual-graph architecture.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, TYPE_CHECKING, Optional

import structlog

from ..base import TurnStage
from src.domain.models.pipeline_contracts import StateComputationOutput
from src.domain.models.knowledge_graph import SaturationMetrics, GraphState
from src.services.graph_service import GraphService


if TYPE_CHECKING:
    from ..context import PipelineContext
    from src.services.canonical_graph_service import CanonicalGraphService

log = structlog.get_logger(__name__)


# =============================================================================
# Saturation thresholds (centralized here, consumed by ContinuationStage)
# =============================================================================
CONSECUTIVE_ZERO_YIELD_THRESHOLD = 5  # Turns with 0 new nodes+edges
CONSECUTIVE_SHALLOW_THRESHOLD = 6  # Turns with only shallow responses (was 4)
DEPTH_PLATEAU_THRESHOLD = 6  # Turns at same max_depth


@dataclass
class _SaturationTrackingState:
    """Per-session rolling state for saturation tracking.

    Tracks metrics across turns that require session-scoped state:
    - consecutive_zero_yield: Turns with no new nodes or edges
    - consecutive_shallow: Turns with only shallow response depths
    - prev_max_depth: For detecting depth plateau
    - consecutive_depth_plateau: Turns at same max_depth
    """

    consecutive_zero_yield: int = 0
    consecutive_shallow: int = 0
    prev_max_depth: int = -1
    consecutive_depth_plateau: int = 0


class StateComputationStage(TurnStage):
    """Compute graph state and saturation metrics after graph updates.

    Centralizes all graph state computation including:
    - Node and edge counts, depth metrics, orphan detection
    - Saturation metrics for continuation decisions (zero yield, shallow responses, depth plateau)
    - Freshness timestamp to prevent stale state bugs in downstream stages
    - Optional canonical graph state for dual-graph architecture

    ContinuationStage consumes saturation_metrics to decide interview termination.
    """

    def __init__(
        self,
        graph_service: GraphService,
        canonical_graph_service: Optional["CanonicalGraphService"] = None,
    ):
        """Initialize state computation stage.

        Args:
            graph_service: GraphService instance for surface graph state computation
            canonical_graph_service: Optional service for canonical graph state in dual-graph architecture.
                When provided, computes aggregated canonical state alongside surface state.
        """
        self.graph = graph_service
        self.canonical_graph_service = canonical_graph_service
        # Session-scoped saturation tracking (persists across turns)
        self._saturation_tracking: Dict[str, _SaturationTrackingState] = {}

    async def process(self, context: "PipelineContext") -> "PipelineContext":
        """Compute graph state and saturation metrics after graph updates.

        Reads from GraphUpdateStage results and produces StateComputationOutput with:
        - Fresh graph state metrics (node/edge counts, depth, orphans)
        - Saturation metrics for continuation decisions
        - Computation timestamp for freshness validation in StrategySelectionStage
        - Optional canonical graph state for dual-graph architecture

        Args:
            context: Turn context with graph_update_output from GraphUpdateStage

        Returns:
            Modified context with state_computation_output contract populated
        """
        graph_state = await self.graph.get_graph_state(context.session_id)
        recent_nodes = await self.graph.get_recent_nodes(context.session_id, limit=5)

        if graph_state:
            # Update turn_count (now a direct field, not in properties)
            graph_state.turn_count = context.turn_number

            # Update strategy_history (now a direct field, not in properties)
            graph_state.strategy_history = context.strategy_history

            # Note: Chain depth metrics are now available via graph_state.depth_metrics
            # The signal pools architecture provides this through GraphMaxDepthSignal
            # No need for methodology-specific calculation here

        # Compute saturation metrics
        saturation = self._compute_saturation_metrics(context, graph_state)

        # Compute canonical graph state (optional, for dual-graph architecture)
        canonical_graph_state = None
        if self.canonical_graph_service is not None:
            canonical_graph_state = (
                await self.canonical_graph_service.compute_canonical_state(
                    context.session_id
                )
            )

            # Log surface vs canonical node counts with reduction percentage
            surface_count = graph_state.node_count if graph_state else 0
            canonical_count = canonical_graph_state.concept_count
            if surface_count > 0:
                reduction_pct = (1 - canonical_count / surface_count) * 100
                log.info(
                    "dual_graph_states_computed",
                    session_id=context.session_id,
                    surface_count=surface_count,
                    canonical_count=canonical_count,
                    reduction_pct=round(reduction_pct, 1),
                    canonical_edge_count=canonical_graph_state.edge_count,
                    canonical_orphan_count=canonical_graph_state.orphan_count,
                )
            else:
                log.debug(
                    "dual_graph_states_computed_empty",
                    session_id=context.session_id,
                    canonical_count=canonical_count,
                )

        # Track when graph_state was computed for freshness validation
        computed_at = datetime.now(timezone.utc)

        # Create contract output (single source of truth)
        context.state_computation_output = StateComputationOutput(
            graph_state=graph_state,
            recent_nodes=recent_nodes,
            computed_at=computed_at,
            saturation_metrics=saturation,
            canonical_graph_state=canonical_graph_state,
        )

        log.debug(
            "graph_state_computed",
            session_id=context.session_id,
            node_count=graph_state.node_count if graph_state else 0,
            edge_count=graph_state.edge_count if graph_state else 0,
            saturation_is_saturated=saturation.is_saturated if saturation else False,
        )

        return context

    def _get_saturation_tracking(self, session_id: str) -> _SaturationTrackingState:
        """Get or create per-session saturation tracking state."""
        if session_id not in self._saturation_tracking:
            self._saturation_tracking[session_id] = _SaturationTrackingState()
        return self._saturation_tracking[session_id]

    def _compute_saturation_metrics(
        self,
        context: "PipelineContext",
        graph_state: Optional[GraphState],
    ) -> SaturationMetrics:
        """Compute interview saturation metrics for continuation decisions.

        Tracks session-scoped counters across turns to detect:
        - Consecutive zero yield (no new nodes or edges)
        - Consecutive shallow responses (low depth answers)
        - Depth plateau (max depth unchanged)

        When thresholds are exceeded, ContinuationStage may terminate the interview.

        Args:
            context: Pipeline context with graph_update_output for yield detection
            graph_state: Current graph state for depth metrics

        Returns:
            SaturationMetrics with is_saturated flag and individual metric values
        """
        tracking = self._get_saturation_tracking(context.session_id)

        # --- Graph yield tracking (consecutive_zero_yield → consecutive_low_info) ---
        nodes_added = 0
        edges_added = 0
        if context.graph_update_output:
            nodes_added = context.graph_update_output.node_count
            edges_added = context.graph_update_output.edge_count

        if nodes_added + edges_added == 0:
            tracking.consecutive_zero_yield += 1
        else:
            tracking.consecutive_zero_yield = 0

        # --- Depth plateau tracking ---
        current_max_depth = 0
        if graph_state and graph_state.depth_metrics:
            current_max_depth = graph_state.depth_metrics.max_depth

        if (
            tracking.prev_max_depth >= 0
            and current_max_depth == tracking.prev_max_depth
        ):
            tracking.consecutive_depth_plateau += 1
        else:
            tracking.consecutive_depth_plateau = 0
        tracking.prev_max_depth = current_max_depth

        # --- Quality degradation tracking (shallow responses) ---
        if context.node_tracker and context.node_tracker.states:
            # Check if the most recent response depths are all shallow/surface
            # Note: response_depth is appended in Stage 6 (StrategySelectionStage)
            # so we need to look at the PREVIOUS turn's data
            has_any_depth_data = False
            has_any_deep = False
            for ns in context.node_tracker.states.values():
                if ns.all_response_depths:
                    has_any_depth_data = True
                    if ns.all_response_depths[-1] in ("moderate", "deep"):
                        has_any_deep = True
                        break
            # Only assess quality if we have response depth data
            # Empty response_depths means we can't assess quality yet
            if has_any_depth_data:
                if not has_any_deep:
                    tracking.consecutive_shallow += 1
                else:
                    tracking.consecutive_shallow = 0
        # If no node_tracker or no depth data, don't increment — we can't assess quality

        # --- Calculate new_info_rate ---
        total_nodes = graph_state.node_count if graph_state else 0
        new_info = nodes_added + edges_added
        if total_nodes > 0:
            new_info_rate = min(1.0, new_info / max(total_nodes * 0.1, 1))
        else:
            new_info_rate = 1.0 if new_info > 0 else 0.0

        # --- Derive is_saturated ---
        is_saturated = (
            tracking.consecutive_zero_yield >= CONSECUTIVE_ZERO_YIELD_THRESHOLD
            or tracking.consecutive_shallow >= CONSECUTIVE_SHALLOW_THRESHOLD
            or tracking.consecutive_depth_plateau >= DEPTH_PLATEAU_THRESHOLD
        )

        return SaturationMetrics(
            chao1_ratio=0.0,  # Placeholder for future Chao1 estimator
            new_info_rate=new_info_rate,
            consecutive_low_info=tracking.consecutive_zero_yield,
            is_saturated=is_saturated,
            consecutive_shallow=tracking.consecutive_shallow,
            consecutive_depth_plateau=tracking.consecutive_depth_plateau,
            prev_max_depth=tracking.prev_max_depth,
        )
