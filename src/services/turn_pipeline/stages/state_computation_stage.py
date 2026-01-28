"""
Stage 5: Compute graph state.

ADR-008 Phase 3: Refresh graph state after updates.
ADR-010: Return StateComputationOutput with freshness tracking.
Phase 6: Output StateComputationOutput contract.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import structlog

from ..base import TurnStage
from src.domain.models.pipeline_contracts import StateComputationOutput


if TYPE_CHECKING:
    from ..context import PipelineContext
log = structlog.get_logger(__name__)


class StateComputationStage(TurnStage):
    """
    Compute current graph state.

    Refreshes PipelineContext.graph_state and PipelineContext.recent_nodes.
    """

    def __init__(self, graph_service):
        """
        Initialize stage.

        Args:
            graph_service: GraphService instance
        """
        self.graph = graph_service

    async def process(self, context: "PipelineContext") -> "PipelineContext":
        """
        Refresh graph state after updates.

        ADR-010: Now tracks computed_at timestamp for freshness validation.

        Args:
            context: Turn context

        Returns:
            Modified context with refreshed graph_state and recent_nodes
        """
        graph_state = await self.graph.get_graph_state(context.session_id)
        recent_nodes = await self.graph.get_recent_nodes(context.session_id, limit=5)

        # ADR-010: Update GraphState using new typed fields instead of properties dict
        if graph_state:
            # Update turn_count (now a direct field, not in properties)
            graph_state.turn_count = context.turn_number

            # Update strategy_history (now a direct field, not in properties)
            graph_state.strategy_history = context.strategy_history

            # Note: Chain depth metrics are now available via graph_state.depth_metrics
            # The signal pools architecture provides this through GraphMaxDepthSignal
            # No need for methodology-specific calculation here

        # ADR-010: Track when graph_state was computed for freshness validation
        computed_at = datetime.now(timezone.utc)

        # Create contract output (single source of truth)
        # No need to set individual fields - they're derived from the contract
        context.state_computation_output = StateComputationOutput(
            graph_state=graph_state,
            recent_nodes=recent_nodes,
            computed_at=computed_at,
        )

        log.debug(
            "graph_state_computed",
            session_id=context.session_id,
            node_count=graph_state.node_count if graph_state else 0,
            edge_count=graph_state.edge_count if graph_state else 0,
        )

        return context
