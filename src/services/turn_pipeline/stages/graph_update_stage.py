"""
Stage 4: Update knowledge graph.

ADR-008 Phase 3: Add extracted concepts and relationships to the graph.
Phase 6: Output GraphUpdateOutput contract.
"""

from typing import TYPE_CHECKING

import structlog

from ..base import TurnStage
from src.domain.models.pipeline_contracts import GraphUpdateOutput


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
            log.warning(
                "no_user_utterance_for_graph_update", session_id=context.session_id
            )
            return context

        nodes, edges = await self.graph.add_extraction_to_graph(
            session_id=context.session_id,
            extraction=context.extraction,
            utterance_id=context.user_utterance.id,
        )

        # Convert edges to dicts for contract output
        # The contract expects List[Dict[str, Any]] but service returns List[KGEdge]
        edges_as_dicts = []
        for edge in edges:
            if hasattr(edge, "model_dump"):
                edges_as_dicts.append(edge.model_dump())
            elif hasattr(edge, "to_dict"):
                edges_as_dicts.append(edge.to_dict())
            elif isinstance(edge, dict):
                edges_as_dicts.append(edge)
            else:
                # Fallback: convert to dict manually
                edges_as_dicts.append(
                    {
                        "id": getattr(edge, "id", ""),
                        "session_id": getattr(edge, "session_id", ""),
                        "source_node_id": getattr(edge, "source_node_id", ""),
                        "target_node_id": getattr(edge, "target_node_id", ""),
                        "edge_type": getattr(edge, "edge_type", ""),
                    }
                )

        # Create contract output (single source of truth)
        # No need to set individual fields - they're derived from the contract
        context.graph_update_output = GraphUpdateOutput(
            nodes_added=nodes,
            edges_added=edges_as_dicts,
            # timestamp, node_count, edge_count auto-set
        )

        log.info(
            "graph_updated",
            session_id=context.session_id,
            nodes_added=len(nodes),
            edges_added=len(edges),
        )

        return context
