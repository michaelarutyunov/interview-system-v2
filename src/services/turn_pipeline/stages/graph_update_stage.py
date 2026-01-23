"""
Stage 4: Update knowledge graph.

ADR-008 Phase 3: Add extracted concepts and relationships to the graph.
"""
from typing import TYPE_CHECKING

import structlog

from ..base import TurnStage


if TYPE_CHECKING:
    from ..context import PipelineContext
log = structlog.get_logger(__name__)


class GraphUpdateStage(TurnStage):
    """
    Update knowledge graph with extracted data.

    Populates PipelineContext.nodes_added and PipelineContext.edges_added.
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
        Update knowledge graph with extraction results.

        Args:
            context: Turn context with extraction and user_utterance

        Returns:
            Modified context with nodes_added and edges_added
        """
        if not context.extraction:
            log.warning("no_extraction_to_add", session_id=context.session_id)
            return context

        if not context.user_utterance:
            log.warning("no_user_utterance_for_graph_update", session_id=context.session_id)
            return context

        nodes, edges = await self.graph.add_extraction_to_graph(
            session_id=context.session_id,
            extraction=context.extraction,
            utterance_id=context.user_utterance.id,
        )

        context.nodes_added = nodes
        context.edges_added = edges

        log.info(
            "graph_updated",
            session_id=context.session_id,
            nodes_added=len(nodes),
            edges_added=len(edges),
        )

        return context
