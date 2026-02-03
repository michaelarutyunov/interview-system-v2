"""
Stage 4: Update knowledge graph.

ADR-008 Phase 3: Add extracted concepts and relationships to the graph.
Phase 6: Output GraphUpdateOutput contract.
Phase 7: Integrate NodeStateTracker for per-node state tracking.
"""

from typing import TYPE_CHECKING

import structlog

from ..base import TurnStage
from src.domain.models.pipeline_contracts import GraphUpdateOutput
from src.services.node_state_tracker import GraphChangeSummary


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

        Integrates with NodeStateTracker to:
        - Register new nodes
        - Update edge counts
        - Record yields when graph changes occur

        Args:
            context: Turn context with extraction and user_utterance

        Returns:
            Modified context with nodes_added and edges_added
        """
        if not context.extraction:
            log.error(
                "contract_violation",
                stage="GraphUpdateStage",
                session_id=context.session_id,
                violation="context.extraction is None or empty",
            )
            raise ValueError(
                "GraphUpdateStage contract violation: context.extraction is required "
                "but was None or empty. Stage 3 (ExtractionStage) must provide "
                "extraction results before GraphUpdateStage can process."
            )

        if not context.user_utterance:
            log.error(
                "contract_violation",
                stage="GraphUpdateStage",
                session_id=context.session_id,
                violation="context.user_utterance is None",
            )
            raise ValueError(
                "GraphUpdateStage contract violation: context.user_utterance is required "
                "but was None. Stage 2 (UtteranceSavingStage) must save the user "
                "utterance before GraphUpdateStage can process."
            )

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

        # Integrate with NodeStateTracker if available
        if context.node_tracker:
            await self._update_node_state_tracker(
                context=context,
                nodes_added=nodes,
                edges_added=edges,
            )

        log.info(
            "graph_updated",
            session_id=context.session_id,
            nodes_added=len(nodes),
            edges_added=len(edges),
        )

        return context

    async def _update_node_state_tracker(
        self,
        context: "PipelineContext",
        nodes_added: list,
        edges_added: list,
    ) -> None:
        """
        Update NodeStateTracker with new nodes and edges.

        This method:
        1. Registers newly created nodes
        2. Updates edge counts for affected nodes
        3. Records yield if graph changes occurred

        Args:
            context: Pipeline context
            nodes_added: List of newly added KGNode objects
            edges_added: List of newly added KGEdge objects
        """
        node_tracker = context.node_tracker
        if not node_tracker:
            return

        # Register new nodes
        for node in nodes_added:
            await node_tracker.register_node(
                node=node,
                turn_number=context.turn_number,
            )

        # Update edge counts for all affected nodes
        edge_counts = {}  # node_id -> (outgoing_delta, incoming_delta)
        for edge in edges_added:
            source_id = (
                edge.source_node_id
                if hasattr(edge, "source_node_id")
                else edge.get("source_node_id")
            )
            target_id = (
                edge.target_node_id
                if hasattr(edge, "target_node_id")
                else edge.get("target_node_id")
            )

            # Update outgoing count for source
            if source_id not in edge_counts:
                edge_counts[source_id] = [0, 0]
            edge_counts[source_id][0] += 1

            # Update incoming count for target
            if target_id not in edge_counts:
                edge_counts[target_id] = [0, 0]
            edge_counts[target_id][1] += 1

        # Apply edge count updates
        for node_id, (outgoing_delta, incoming_delta) in edge_counts.items():
            await node_tracker.update_edge_counts(
                node_id=node_id,
                outgoing_delta=outgoing_delta,
                incoming_delta=incoming_delta,
            )

        # Record yield if there were changes
        if nodes_added or edges_added:
            # Determine which node to credit with the yield
            # This should be the focus from the previous turn
            # For now, we'll record yield for all nodes that were involved
            graph_changes = GraphChangeSummary(
                nodes_added=len(nodes_added),
                edges_added=len(edges_added),
                nodes_modified=0,
            )

            # If we have a previous focus, record yield for it
            if node_tracker.previous_focus:
                await node_tracker.record_yield(
                    node_id=node_tracker.previous_focus,
                    turn_number=context.turn_number,
                    graph_changes=graph_changes,
                )

            log.debug(
                "node_state_tracker_updated",
                session_id=context.session_id,
                nodes_registered=len(nodes_added),
                edges_updated=len(edge_counts),
            )
