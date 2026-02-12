"""NodeStateTracker service for maintaining per-node state across interview sessions.

Tracks engagement patterns, yield history, response quality, relationships,
and strategy usage for each knowledge graph node. Supports dual-graph
architecture by tracking canonical slots that aggregate surface nodes.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Optional, TYPE_CHECKING, Any

import structlog

from src.domain.models.knowledge_graph import KGNode
from src.domain.models.node_state import NodeState

if TYPE_CHECKING:
    from src.persistence.repositories.canonical_slot_repo import CanonicalSlotRepository


# Schema version for node_tracker_state serialization
# Increment when structure changes to handle migration
NODE_TRACKER_SCHEMA_VERSION = 1


@dataclass
class GraphChangeSummary:
    """Summary of graph changes for yield detection.

    Used to determine if focusing on a node produced new information.

    Attributes:
        nodes_added: Number of new nodes added
        edges_added: Number of new edges added
        nodes_modified: Number of existing nodes that were modified
    """

    nodes_added: int
    edges_added: int
    nodes_modified: int = 0


class NodeStateTracker:
    """Service for maintaining persistent per-node state across interview sessions.

    NodeStateTracker tracks state for all knowledge graph nodes throughout
    an interview, enabling node-level signal computation and strategy-node
    joint scoring.

    The tracker maintains:
    - Engagement metrics (focus count, streak, recency)
    - Yield metrics (yield count, rate, stagnation)
    - Response quality aggregation
    - Relationship tracking (edges, orphans)
    - Strategy usage patterns
    """

    def __init__(
        self, canonical_slot_repo: Optional["CanonicalSlotRepository"] = None
    ) -> None:
        """Initialize the NodeStateTracker with optional canonical slot support.

        Args:
            canonical_slot_repo: Optional CanonicalSlotRepository for resolving
                surface node IDs to canonical slot IDs. If provided, tracking
                uses canonical_slot_id as the key for aggregation across paraphrases.
                When None (enable_canonical_slots=False), uses surface node_id directly.

        Implementation notes:
            - canonical_slot_repo is optional based on enable_canonical_slots feature flag
            - If provided, uses canonical_slot_id as tracking dict key for paraphrase aggregation
            - Falls back to surface node_id if no mapping exists (normal behavior)
        """
        self.states: Dict[str, NodeState] = {}
        self.previous_focus: Optional[str] = None
        self.canonical_slot_repo = canonical_slot_repo
        self.log = structlog.get_logger(__name__)

    async def _resolve_canonical_slot_id(self, surface_node_id: str) -> str:
        """Resolve a surface node ID to its canonical slot ID.

        If canonical_slot_repo is available, queries the surface_to_slot_mapping
        table to find the canonical slot for this surface node. Returns the
        canonical_slot_id if found, otherwise falls back to the surface node_id.

        Args:
            surface_node_id: Surface node ID to resolve

        Returns:
            canonical_slot_id if mapping exists, otherwise surface_node_id

        Implementation notes:
            - Fallback to surface_node_id is normal behavior (not an error)
            - Database errors propagate immediately for visibility of issues
        """
        if self.canonical_slot_repo is None:
            return surface_node_id

        mapping = await self.canonical_slot_repo.get_mapping_for_node(
            surface_node_id
        )

        if mapping is None:
            # No mapping exists - use surface node_id as tracking key
            # This is expected for unmapped nodes or when canonical slots disabled
            return surface_node_id

        return mapping.canonical_slot_id

    async def register_node(self, node: KGNode, turn_number: int) -> NodeState:
        """
        Register a new node when it's added to the graph.

        If the node is already registered, returns the existing NodeState.
        Otherwise, creates a new NodeState with initial values.

        Args:
            node: KGNode to register
            turn_number: Current turn number

        Returns:
            NodeState for the node (existing or newly created)
        """
        # Check if already registered
        if node.id in self.states:
            self.log.debug(
                "node_already_registered",
                node_id=node.id,
                label=node.label,
                turn_number=turn_number,
            )
            return self.states[node.id]

        # Create new NodeState
        node_state = NodeState(
            node_id=node.id,
            label=node.label,
            created_at_turn=turn_number,
            depth=self._calculate_node_depth(node),
            node_type=node.node_type,
            is_terminal=node.properties.get("is_terminal", False),
            level=node.properties.get("level", 0),
        )

        self.states[node.id] = node_state

        self.log.info(
            "node_registered",
            node_id=node.id,
            label=node.label,
            turn_number=turn_number,
            depth=node_state.depth,
        )

        return node_state

    async def update_focus(self, node_id: str, turn_number: int, strategy: str) -> None:
        """
        Update focus metrics when a node is selected as focus.

        Updates:
        - Increments focus_count
        - Sets last_focus_turn to current turn
        - Resets or increments current_focus_streak based on previous focus
        - Updates strategy usage tracking

        Args:
            node_id: ID of node being focused (surface node ID)
            turn_number: Current turn number
            strategy: Strategy being used for this focus

        Implementation notes:
            - Resolves node_id to canonical_slot_id for tracking dict key
            - Focus selection continues to target surface nodes (for question generation)
            - Tracking key is canonical_slot_id for aggregation across paraphrases
        """
        # Resolve to canonical_slot_id for tracking key
        tracking_key = await self._resolve_canonical_slot_id(node_id)

        if tracking_key not in self.states:
            self.log.warning(
                "focus_update_failed_node_not_found",
                node_id=node_id,
                tracking_key=tracking_key,
                turn_number=turn_number,
            )
            return

        state = self.states[tracking_key]

        # Update focus count and timing
        state.focus_count += 1
        state.last_focus_turn = turn_number

        # Update streak: reset if focus changed, increment if same
        if self.previous_focus == tracking_key:
            state.current_focus_streak += 1
        else:
            state.current_focus_streak = 1

        # Update turns_since_last_focus for all nodes
        for nid, s in self.states.items():
            if nid == tracking_key:
                s.turns_since_last_focus = 0
            else:
                s.turns_since_last_focus += 1

        # Update strategy usage
        if strategy not in state.strategy_usage_count:
            state.strategy_usage_count[strategy] = 0
        state.strategy_usage_count[strategy] += 1

        # Track consecutive same strategy
        if state.last_strategy_used == strategy:
            state.consecutive_same_strategy += 1
        else:
            state.consecutive_same_strategy = 1

        state.last_strategy_used = strategy

        # Update previous focus (use tracking_key for comparison)
        self.previous_focus = tracking_key

        self.log.debug(
            "node_focus_updated",
            node_id=node_id,
            tracking_key=tracking_key,
            turn_number=turn_number,
            strategy=strategy,
            focus_count=state.focus_count,
            streak=state.current_focus_streak,
        )

    async def record_yield(
        self, node_id: str, turn_number: int, graph_changes: GraphChangeSummary
    ) -> None:
        """
        Record yield when a node produces new graph changes.

        Updates:
        - Sets last_yield_turn to current turn
        - Resets turns_since_last_yield for this node
        - Increments yield_count
        - Recalculates yield_rate
        - Resets current_focus_streak to 0 (yield breaks the streak)

        Args:
            node_id: ID of node that produced changes (surface node ID)
            turn_number: Current turn number
            graph_changes: Summary of graph changes

        Implementation notes:
            - Resolves node_id to canonical_slot_id for tracking dict key
        """
        tracking_key = await self._resolve_canonical_slot_id(node_id)

        if tracking_key not in self.states:
            self.log.warning(
                "yield_record_failed_node_not_found",
                node_id=node_id,
                tracking_key=tracking_key,
                turn_number=turn_number,
            )
            return

        # Only record yield if there were actual changes (nodes/edges added or modified)
        if (
            graph_changes.nodes_added == 0
            and graph_changes.edges_added == 0
            and graph_changes.nodes_modified == 0
        ):
            self.log.debug(
                "no_yield_no_changes",
                node_id=node_id,
                tracking_key=tracking_key,
                turn_number=turn_number,
                nodes_added=graph_changes.nodes_added,
                edges_added=graph_changes.edges_added,
                nodes_modified=graph_changes.nodes_modified,
            )
            return

        state = self.states[tracking_key]

        # Update yield metrics
        state.last_yield_turn = turn_number
        state.turns_since_last_yield = 0
        state.yield_count += 1

        # Recalculate yield rate: yield_count / max(focus_count, 1)
        state.yield_rate = state.yield_count / max(state.focus_count, 1)

        # Reset focus streak (yield breaks the streak)
        state.current_focus_streak = 0

        self.log.debug(
            "node_yield_recorded",
            node_id=node_id,
            tracking_key=tracking_key,
            turn_number=turn_number,
            yield_count=state.yield_count,
            yield_rate=state.yield_rate,
            nodes_added=graph_changes.nodes_added,
            edges_added=graph_changes.edges_added,
            nodes_modified=graph_changes.nodes_modified,
        )

    async def append_response_signal(
        self, focus_node_id: str, response_depth: str
    ) -> None:
        """
        Append response depth to the node that was asked about.

        The response depth belongs to the focus node from the PREVIOUS turn,
        not the node being selected for the next question.

        Args:
            focus_node_id: ID of the node that was focused when question was asked
            response_depth: Response depth (surface/shallow/deep)

        Note:
            Resolves focus_node_id to canonical_slot_id for tracking dict key.
        """
        tracking_key = await self._resolve_canonical_slot_id(focus_node_id)

        if tracking_key not in self.states:
            self.log.warning(
                "response_signal_append_failed_node_not_found",
                focus_node_id=focus_node_id,
                tracking_key=tracking_key,
                response_depth=response_depth,
            )
            return

        state = self.states[tracking_key]
        state.all_response_depths.append(response_depth)

        self.log.debug(
            "response_signal_appended",
            node_id=focus_node_id,
            tracking_key=tracking_key,
            response_depth=response_depth,
            total_responses=len(state.all_response_depths),
        )

    async def update_edge_counts(
        self, node_id: str, outgoing_delta: int, incoming_delta: int
    ) -> None:
        """
        Update edge counts when edges are added or removed.

        Args:
            node_id: ID of node to update (surface node ID)
            outgoing_delta: Change in outgoing edge count (+/-)
            incoming_delta: Change in incoming edge count (+/-)

        Implementation notes:
            - Resolves node_id to canonical_slot_id for tracking dict key
        """
        tracking_key = await self._resolve_canonical_slot_id(node_id)

        if tracking_key not in self.states:
            self.log.warning(
                "edge_count_update_failed_node_not_found",
                node_id=node_id,
                tracking_key=tracking_key,
                outgoing_delta=outgoing_delta,
                incoming_delta=incoming_delta,
            )
            return

        state = self.states[tracking_key]
        state.edge_count_outgoing += outgoing_delta
        state.edge_count_incoming += incoming_delta

        # Ensure counts don't go negative
        state.edge_count_outgoing = max(0, state.edge_count_outgoing)
        state.edge_count_incoming = max(0, state.edge_count_incoming)

        self.log.debug(
            "node_edge_counts_updated",
            node_id=node_id,
            tracking_key=tracking_key,
            outgoing_delta=outgoing_delta,
            incoming_delta=incoming_delta,
            total_outgoing=state.edge_count_outgoing,
            total_incoming=state.edge_count_incoming,
        )

    async def get_state(self, node_id: str) -> Optional[NodeState]:
        """
        Get NodeState for a node.

        Args:
            node_id: ID of node to get state for (surface node ID)

        Returns:
            NodeState if tracked, None otherwise

        Note:
            Resolves node_id to canonical_slot_id for lookup.
        """
        tracking_key = await self._resolve_canonical_slot_id(node_id)
        return self.states.get(tracking_key)

    def get_all_states(self) -> Dict[str, NodeState]:
        """
        Get all tracked node states.

        Returns:
            Dictionary mapping node_id to NodeState
        """
        return self.states.copy()

    def _calculate_node_depth(self, node: KGNode) -> int:
        """Calculate the depth of a node in the knowledge graph.

        This is a simple heuristic. In a full implementation, this would
        traverse the graph to determine the actual depth.

        Args:
            node: KGNode to calculate depth for

        Returns:
            Estimated depth (0 for root/unknown)
        """
        # For now, use a simple heuristic based on node properties
        # A full implementation would traverse the graph
        if "depth" in node.properties:
            return node.properties.get("depth", 0)

        # Default to depth 0 (root level)
        return 0

    # ==================== SERIALIZATION FOR PERSISTENCE ====================

    def to_dict(self) -> Dict[str, Any]:
        """Serialize node tracker state to dictionary for database persistence.

        Converts the tracker's state to a JSON-serializable dictionary that
        can be stored in the sessions.node_tracker_state column and loaded
        in subsequent turns to maintain continuity.

        Returns:
            Dictionary with schema_version, previous_focus, and states data
        """
        # Convert each NodeState to a dict, handling Set serialization
        states_dict = {}
        for node_id, state in self.states.items():
            # Use dataclass.asdict but convert Set to list for JSON compatibility
            state_dict = asdict(state)
            # Convert Set to list for JSON serialization
            state_dict["connected_node_ids"] = list(state.connected_node_ids)
            states_dict[node_id] = state_dict

        return {
            "schema_version": NODE_TRACKER_SCHEMA_VERSION,
            "previous_focus": self.previous_focus,
            "states": states_dict,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NodeStateTracker":
        """Deserialize node tracker state from database-persisted dictionary.

        Reconstructs a NodeStateTracker from previously persisted state,
        restoring all per-node metrics for continuity across turns.

        Args:
            data: Dictionary previously created by to_dict()

        Returns:
            Reconstructed NodeStateTracker with restored state

        Raises:
            ValueError: If schema version is incompatible
        """
        # Validate schema version
        schema_version = data.get("schema_version", 1)
        if schema_version != NODE_TRACKER_SCHEMA_VERSION:
            raise ValueError(
                f"Incompatible node_tracker_state schema version: "
                f"expected {NODE_TRACKER_SCHEMA_VERSION}, got {schema_version}"
            )

        tracker = cls()

        # Restore previous_focus
        tracker.previous_focus = data.get("previous_focus")

        # Restore each NodeState
        states_data = data.get("states", {})
        for node_id, state_dict in states_data.items():
            # Convert list back to Set for connected_node_ids
            state_dict["connected_node_ids"] = set(state_dict.get("connected_node_ids", []))

            # Reconstruct NodeState from dict
            tracker.states[node_id] = NodeState(**state_dict)

        return tracker

    def is_empty(self) -> bool:
        """Check if tracker has no tracked state.

        Returns:
            True if no nodes are tracked, False otherwise
        """
        return len(self.states) == 0
