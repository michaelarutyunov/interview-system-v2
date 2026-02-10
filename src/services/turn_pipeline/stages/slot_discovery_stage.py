"""
Slot Discovery Stage (Stage 4.5) - Dual-Graph Architecture.

Discovers or updates canonical slots for newly added surface nodes.
Maps surface KGNodes to abstract canonical slots via LLM proposal and
embedding similarity matching. Also aggregates surface edges to canonical edges.
"""

from typing import TYPE_CHECKING, Optional

import structlog

from ..base import TurnStage
from src.domain.models.pipeline_contracts import SlotDiscoveryOutput
from src.services.canonical_slot_service import CanonicalSlotService

if TYPE_CHECKING:
    from ..context import PipelineContext
    from src.services.graph_service import GraphService

log = structlog.get_logger(__name__)


class SlotDiscoveryStage(TurnStage):
    """
    Stage 4.5: Discover canonical slots for newly added surface nodes.

    Implements the dual-graph architecture by mapping surface nodes (user's
    actual language) to abstract canonical slots (latent concepts). Uses
    LLM to propose slot groupings and embedding similarity to merge
    near-duplicates. Also aggregates surface edges to canonical edges.

    CONTRACT: Requires graph_update_output to exist (Stage 4 complete).
    Raises RuntimeError if contract violated (fail-fast).
    """

    def __init__(
        self, slot_service: CanonicalSlotService, graph_service: Optional["GraphService"] = None
    ):
        """
        Initialize slot discovery stage.

        Args:
            slot_service: CanonicalSlotService for slot discovery and mapping
            graph_service: Optional GraphService for edge aggregation to canonical graph

        Note:
            graph_service is optional for backward compatibility. If provided,
            aggregates surface edges to canonical edges after slot mapping.
        """
        self.slot_service = slot_service
        self.graph_service = graph_service

    async def process(self, context: "PipelineContext") -> "PipelineContext":
        """
        Process slot discovery for newly added surface nodes.

        CONTRACT INPUT:
            context.graph_update_output.nodes_added (from Stage 4)
            context.context_loading_output.turn_number (from Stage 1)
            context.context_loading_output.methodology (from Stage 1)

        CONTRACT OUTPUT:
            context.slot_discovery_output: SlotDiscoveryOutput
                - slots_created: int (new slots this turn)
                - slots_updated: int (existing slots with new mappings)
                - mappings_created: int (surface nodes mapped)
                - timestamp: datetime

        SIDE EFFECTS:
            - INSERT canonical_slots (new slots)
            - INSERT surface_to_slot_mapping (node mappings)
            - UPDATE canonical_slots.support_count (increment for matched)
            - Possible: UPDATE canonical_slots.status='active' (promotion)
            - LLM call for slot proposal (uses generation client)

        ERROR HANDLING (fail-fast):
            - No nodes_added: skip LLM call, return SlotDiscoveryOutput with zeros
            - graph_update_output is None: raise RuntimeError (contract violation)
            - LLM failure: exception propagates, pipeline fails for this turn

        Args:
            context: Pipeline context with graph_update_output

        Returns:
            Updated context with slot_discovery_output set

        Raises:
            RuntimeError: If graph_update_output is None (contract violation)
        """
        # CONTRACT VALIDATION: graph_update_output must exist
        if context.graph_update_output is None:
            raise RuntimeError(
                "Pipeline contract violation: SlotDiscoveryStage (4.5) requires "
                "GraphUpdateStage (4) to complete first. "
                f"Session: {context.session_id}"
            )

        surface_nodes = context.graph_update_output.nodes_added

        # GRACEFUL SKIP: No new nodes - return zeros without LLM call
        if not surface_nodes:
            log.debug(
                "slot_discovery_skipped",
                session_id=context.session_id,
                reason="no_nodes_added",
            )
            context.slot_discovery_output = SlotDiscoveryOutput()
            return context

        # Get turn number and methodology from context
        turn_number = context.turn_number
        methodology = context.methodology

        log.info(
            "slot_discovery_started",
            session_id=context.session_id,
            turn=turn_number,
            node_count=len(surface_nodes),
            methodology=methodology,
        )

        # Call CanonicalSlotService to discover/match slots
        discovered_slots = await self.slot_service.discover_slots_for_nodes(
            session_id=context.session_id,
            surface_nodes=surface_nodes,
            turn_number=turn_number,
            methodology=methodology,
        )

        # Count slots_created vs slots_updated
        # Slots with first_seen_turn == current turn were created this turn
        current_turn_slots = [s for s in discovered_slots if s.first_seen_turn == turn_number]
        slots_created = len(current_turn_slots)
        slots_updated = len(discovered_slots) - slots_created
        mappings_created = len(surface_nodes)  # Each node maps to exactly one slot

        log.info(
            "slot_discovery_complete",
            session_id=context.session_id,
            turn=turn_number,
            slots_created=slots_created,
            slots_updated=slots_updated,
            mappings_created=mappings_created,
            total_slots=len(discovered_slots),
        )

        # After slot mappings are created, aggregate surface edges to canonical edges
        canonical_edges_created = 0
        if self.graph_service is not None:
            edges_added = context.graph_update_output.edges_added
            if edges_added:
                canonical_edges = await self.graph_service.aggregate_surface_edges_to_canonical(
                    session_id=context.session_id,
                    surface_edges=edges_added,
                    turn_number=turn_number,
                )
                canonical_edges_created = len(canonical_edges)

                log.info(
                    "canonical_edges_created",
                    session_id=context.session_id,
                    turn=turn_number,
                    count=canonical_edges_created,
                )
            else:
                log.debug(
                    "canonical_edge_aggregation_skipped",
                    session_id=context.session_id,
                    turn=turn_number,
                    reason="no_edges_added",
                )
        else:
            log.debug(
                "canonical_edge_aggregation_skipped",
                session_id=context.session_id,
                turn=turn_number,
                reason="no_graph_service",
            )

        # Set contract output
        context.slot_discovery_output = SlotDiscoveryOutput(
            slots_created=slots_created,
            slots_updated=slots_updated,
            mappings_created=mappings_created,
        )

        return context
