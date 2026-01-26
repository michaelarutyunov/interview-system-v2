"""
Stage 5: Compute graph state.

ADR-008 Phase 3: Refresh graph state after updates.
"""

from typing import TYPE_CHECKING

import structlog

from ..base import TurnStage


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

        Args:
            context: Turn context

        Returns:
            Modified context with refreshed graph_state and recent_nodes
        """
        graph_state = await self.graph.get_graph_state(context.session_id)
        recent_nodes = await self.graph.get_recent_nodes(context.session_id, limit=5)

        # Set turn_count in graph_state.properties for strategy service phase detection
        # This is critical - StrategyService._determine_phase() reads from this property
        if graph_state:
            graph_state.properties["turn_count"] = context.turn_number
            # Set strategy_history for StrategyDiversityScorer
            # This is loaded from DB in context_loading_stage and copied here
            graph_state.properties["strategy_history"] = context.strategy_history

        context.graph_state = graph_state
        context.recent_nodes = recent_nodes

        log.debug(
            "graph_state_computed",
            session_id=context.session_id,
            node_count=graph_state.node_count if graph_state else 0,
            edge_count=graph_state.edge_count if graph_state else 0,
        )

        return context
