"""
Stage 4: Update knowledge graph.

Adds extracted concepts and relationships to the graph. Outputs
GraphUpdateOutput contract. Integrates with NodeStateTracker for
per-node state tracking.
"""

from typing import TYPE_CHECKING

import structlog

from ..base import TurnStage
from src.domain.models.pipeline_contracts import GraphUpdateOutput
from src.services.graph_service import GraphService


if TYPE_CHECKING:
    from ..context import PipelineContext
log = structlog.get_logger(__name__)


class GraphUpdateStage(TurnStage):
    """
    Update knowledge graph with extracted data.

    Populates PipelineContext.nodes_added and PipelineContext.edges_added.
    """

    def __init__(
        self,
        graph_service: GraphService,
    ):
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
        # Validate Stage 2 (UtteranceSavingStage) completed first
        if context.utterance_saving_output is None:
            raise RuntimeError(
                "Pipeline contract violation: GraphUpdateStage (Stage 4) requires "
                "UtteranceSavingStage (Stage 2) to complete first."
            )

        # Validate Stage 3 (ExtractionStage) completed first
        if context.extraction_output is None:
            raise RuntimeError(
                "Pipeline contract violation: GraphUpdateStage (Stage 4) requires "
                "ExtractionStage (Stage 3) to complete first."
            )

        # Get extraction and utterance from contract outputs
        extraction = context.extraction_output.extraction
        utterance_id = context.utterance_saving_output.user_utterance.id

        # Get methodology from context for permitted_connections validation
        methodology = context.methodology

        # Build per-turn concept→node bridge as a local dict, then emit via contract.
        concept_to_node_id: dict[str, str] = {}
        nodes, edges = await self.graph.add_extraction_to_graph(
            session_id=context.session_id,
            extraction=extraction,
            utterance_id=utterance_id,
            methodology=methodology,
            out_concept_to_node_id=concept_to_node_id,
        )

        # Convert edges to dicts for contract output
        # The contract expects List[Dict[str, Any]] but service returns List[KGEdge]
        edges_as_dicts = []
        for edge in edges:
            if hasattr(edge, "model_dump"):
                edges_as_dicts.append(edge.model_dump())
            elif hasattr(edge, "to_dict"):
                edges_as_dicts.append(edge.to_dict())  # type: ignore[attr-defined]
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
            concept_to_node_id=concept_to_node_id,
            # timestamp, node_count, edge_count auto-set
        )

        # Integrate with NodeStateTracker if available
        if context._evolving_node_tracker is not None:
            context._evolving_node_tracker = await self._update_node_state_tracker(
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
    ):
        """Functionally update the evolving NodeStateTracker; returns new instance."""
        tracker = context._evolving_node_tracker
        assert tracker is not None  # guarded by caller at line 121

        # Batch-register new nodes (single dict rebuild)
        if nodes_added:
            tracker = tracker.register_nodes(nodes_added, context.turn_number)

        # Resolve edge source/target surface IDs to tracking keys and batch-update
        edge_deltas: dict[str, tuple[int, int]] = {}
        for edge in edges_added:
            source_id = getattr(edge, "source_node_id", None) or edge.get(
                "source_node_id"
            )
            target_id = getattr(edge, "target_node_id", None) or edge.get(
                "target_node_id"
            )

            if source_id:
                key = source_id
                if key in tracker.states:
                    out_d, in_d = edge_deltas.get(key, (0, 0))
                    edge_deltas[key] = (out_d + 1, in_d)
                else:
                    log.debug("edge_count_skip_untracked", tracking_key=key)

            if target_id:
                key = target_id
                if key in tracker.states:
                    out_d, in_d = edge_deltas.get(key, (0, 0))
                    edge_deltas[key] = (out_d, in_d + 1)
                else:
                    log.debug("edge_count_skip_untracked", tracking_key=key)

        if edge_deltas:
            tracker = tracker.update_edge_counts_batch(edge_deltas)

        # record_yield ownership moved to EdgeExtractionBridgeStage (D4/B7)
        # Yield credit is now emitted unconditionally by Stage 4.6 after both
        # Stage 4 node writes and Stage 4.5B edge writes are complete.

        log.debug(
            "node_state_tracker_updated",
            session_id=context.session_id,
            nodes_registered=len(nodes_added),
            edges_updated=len(edge_deltas),
        )
        return tracker
