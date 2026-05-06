"""NodeStateTracker — immutable per-node state snapshot for the interview pipeline.

Frozen Pydantic model. Every mutating operation returns a NEW NodeStateTracker
instance; the original is unchanged. Stages 4→4.5→4.7 thread the evolving
instance via PipelineContext._evolving_node_tracker; Stage 4.7 seals it into
LLMSignalBridgeOutput.sealed_node_tracker. Stages 5–10 read the sealed snapshot.

The tracker is keyed by surface UUID. Slot identity is stored as a property
on NodeState.slot_id, set by register_slot_memberships (Stage 4.5).
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from src.domain.models.identity import SlotId, SurfaceNodeId

import structlog

from src.domain.models.knowledge_graph import KGNode
from src.domain.models.node_state import NodeState, NodeQualityHistory

log = structlog.get_logger(__name__)

# Increment when serialization structure changes; from_dict accepts prior versions.
NODE_TRACKER_SCHEMA_VERSION = 6


class NodeNotTrackedError(KeyError):
    """Raised when an operation references a node not registered in the tracker."""


class GraphChangeSummary:
    """Summary of graph changes for yield detection."""

    __slots__ = ("nodes_added", "edges_added", "nodes_modified")

    def __init__(
        self, nodes_added: int, edges_added: int, nodes_modified: int = 0
    ) -> None:
        self.nodes_added = nodes_added
        self.edges_added = edges_added
        self.nodes_modified = nodes_modified

    def is_empty(self) -> bool:
        return (
            self.nodes_added == 0 and self.edges_added == 0 and self.nodes_modified == 0
        )


# ---------------------------------------------------------------------------
# Immutable tracker
# ---------------------------------------------------------------------------

from pydantic import BaseModel, ConfigDict, Field  # noqa: E402 — after stdlib imports


class NodeStateTracker(BaseModel):
    """Immutable snapshot of per-node engagement state for one pipeline turn.

    Construction:
        - Seeded from DB at session start via from_dict().
        - Evolved through Stages 4, 4.5, 4.7 via functional methods.
        - Sealed into LLMSignalBridgeOutput by Stage 4.7.
        - Persisted at turn end from StrategySelectionOutput.next_turn_node_tracker.

    All public methods that modify state return a new NodeStateTracker.
    get_state() raises NodeNotTrackedError on a missing key.
    try_get_state() returns None for callers that legitimately handle absence.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    # Keys are SurfaceNodeId (surface graph UUID). Method signatures enforce
    # the type; dict[str, ...] avoids NewType invariant issues with pyright.
    states: dict[str, NodeState] = Field(default_factory=dict)
    previous_focus: Optional[SurfaceNodeId] = None
    canonical_slot_first_seen: dict[str, int] = Field(default_factory=dict)
    schema_version: int = NODE_TRACKER_SCHEMA_VERSION

    # ------------------------------------------------------------------
    # Node registration
    # ------------------------------------------------------------------

    def register_node(self, node: KGNode, turn_number: int) -> NodeStateTracker:
        """Return new tracker with the node registered. Idempotent on re-registration."""
        if node.id in self.states:
            return self

        depth = node.properties.get("depth", 0)
        new_state = NodeState(
            node_id=node.id,
            label=node.label,
            created_at_turn=turn_number,
            depth=depth,
            node_type=node.node_type,
            is_terminal=node.properties.get("is_terminal", False),
            level=node.properties.get("level", 0),
        )
        log.info(
            "node_registered",
            node_id=node.id,
            label=node.label,
            turn_number=turn_number,
            depth=depth,
        )
        return self.model_copy(update={"states": {**self.states, node.id: new_state}})

    def register_nodes(self, nodes: list[KGNode], turn_number: int) -> NodeStateTracker:
        """Batch registration — single dict rebuild regardless of node count."""
        new_states = dict(self.states)
        for node in nodes:
            if node.id in new_states:
                continue
            depth = node.properties.get("depth", 0)
            new_states[node.id] = NodeState(
                node_id=node.id,
                label=node.label,
                created_at_turn=turn_number,
                depth=depth,
                node_type=node.node_type,
                is_terminal=node.properties.get("is_terminal", False),
                level=node.properties.get("level", 0),
            )
            log.info(
                "node_registered",
                node_id=node.id,
                label=node.label,
                turn_number=turn_number,
                depth=depth,
            )
        return self.model_copy(update={"states": new_states})

    # ------------------------------------------------------------------
    # Focus update
    # ------------------------------------------------------------------

    def update_focus(
        self,
        *,
        tracking_key: SurfaceNodeId,
        turn_number: int,
        strategy: str,
    ) -> NodeStateTracker:
        """Return new tracker with focus metrics updated for tracking_key.

        Args:
            tracking_key: Surface UUID of the focused node.
            turn_number: Current turn number.
            strategy: Selected strategy name.

        Raises:
            NodeNotTrackedError: If tracking_key is not registered.
        """
        if tracking_key not in self.states:
            raise NodeNotTrackedError(
                f"update_focus: tracking_key={tracking_key!r} not registered "
                f"(turn={turn_number}, strategy={strategy!r})"
            )

        is_same = self.previous_focus == tracking_key
        new_states = {}
        for nid, state in self.states.items():
            if nid == tracking_key:
                new_states[nid] = state.with_focus(
                    turn_number=turn_number,
                    strategy=strategy,
                    is_same_as_previous=is_same,
                )
            else:
                new_states[nid] = state.tick_no_focus()

        log.debug(
            "node_focus_updated",
            tracking_key=tracking_key,
            turn_number=turn_number,
            strategy=strategy,
            focus_count=new_states[tracking_key].focus_count,
        )
        update_dict: dict[str, Any] = {
            "states": new_states,
            "previous_focus": tracking_key,
        }
        return self.model_copy(update=update_dict)

    # ------------------------------------------------------------------
    # Yield recording
    # ------------------------------------------------------------------

    def record_yield(
        self,
        *,
        tracking_key: SurfaceNodeId,
        turn_number: int,
        graph_changes: GraphChangeSummary,
    ) -> NodeStateTracker:
        """Return new tracker with yield recorded for tracking_key.

        Records yield unconditionally — the focus node was actively used this
        turn regardless of graph change counts (p4t3 fix). The is_empty() guard
        was removed because after the B7 move to EdgeExtractionBridgeStage,
        nodes_added=0 and edges_added=[] (when feature flag OFF) caused every
        yield to be silently skipped, triggering premature all_nodes_exhausted.

        Raises:
            NodeNotTrackedError: If tracking_key is not registered.
        """
        if tracking_key not in self.states:
            raise NodeNotTrackedError(
                f"record_yield: tracking_key={tracking_key!r} not registered (turn={turn_number})"
            )

        new_state = self.states[tracking_key].with_yield(turn_number=turn_number)
        log.debug(
            "node_yield_recorded",
            tracking_key=tracking_key,
            turn_number=turn_number,
            yield_count=new_state.yield_count,
        )
        return self.model_copy(
            update={"states": {**self.states, tracking_key: new_state}}
        )

    # ------------------------------------------------------------------
    # Quality appending (LLM bridge)
    # ------------------------------------------------------------------

    def append_quality(
        self, *, tracking_key: SurfaceNodeId, elaboration: float, charge: float
    ) -> NodeStateTracker:
        """Return new tracker with LLM quality scores appended for tracking_key.

        Raises:
            NodeNotTrackedError: If tracking_key is not registered.
        """
        if tracking_key not in self.states:
            raise NodeNotTrackedError(
                f"append_quality: tracking_key={tracking_key!r} not registered"
            )

        new_state = self.states[tracking_key].with_quality(
            elaboration=elaboration, charge=charge
        )
        log.debug(
            "node_quality_appended",
            tracking_key=tracking_key,
            elaboration=elaboration,
            charge=charge,
        )
        return self.model_copy(
            update={"states": {**self.states, tracking_key: new_state}}
        )

    # ------------------------------------------------------------------
    # Edge count updates
    # ------------------------------------------------------------------

    def update_edge_counts(
        self, *, tracking_key: SurfaceNodeId, outgoing_delta: int, incoming_delta: int
    ) -> NodeStateTracker:
        """Return new tracker with edge counts updated for tracking_key.

        Raises:
            NodeNotTrackedError: If tracking_key is not registered.
        """
        if tracking_key not in self.states:
            raise NodeNotTrackedError(
                f"update_edge_counts: tracking_key={tracking_key!r} not registered "
                f"(out_delta={outgoing_delta}, in_delta={incoming_delta})"
            )

        new_state = self.states[tracking_key].with_edge_delta(
            outgoing_delta=outgoing_delta, incoming_delta=incoming_delta
        )
        log.debug(
            "node_edge_counts_updated",
            tracking_key=tracking_key,
            outgoing_delta=outgoing_delta,
            incoming_delta=incoming_delta,
            total_outgoing=new_state.edge_count_outgoing,
            total_incoming=new_state.edge_count_incoming,
        )
        return self.model_copy(
            update={"states": {**self.states, tracking_key: new_state}}
        )

    def update_edge_counts_batch(
        self, deltas: dict[str, tuple[int, int]]
    ) -> NodeStateTracker:
        """Batch edge-count update — single dict rebuild for all nodes.

        Args:
            deltas: mapping of tracking_key → (outgoing_delta, incoming_delta)

        Raises:
            NodeNotTrackedError: If any tracking_key is not registered.
        """
        for key in deltas:
            if key not in self.states:
                raise NodeNotTrackedError(
                    f"update_edge_counts_batch: tracking_key={key!r} not registered"
                )

        new_states = dict(self.states)
        for key, (out_d, in_d) in deltas.items():
            new_states[key] = new_states[key].with_edge_delta(
                outgoing_delta=out_d, incoming_delta=in_d
            )
        return self.model_copy(update={"states": new_states})

    # ------------------------------------------------------------------
    # Canonical slot membership (Stage 4.5)
    # ------------------------------------------------------------------

    def register_slot_memberships(
        self, mappings: Mapping[SurfaceNodeId, SlotId]
    ) -> NodeStateTracker:
        """Return new tracker with slot_id property set on each mapped surface state.

        Does NOT change the tracker keyspace. The tracker remains keyed by surface
        UUID; slot membership is stored on NodeState.slot_id for use by
        slot-aggregating signals (e.g. canongraph.node.novelty).

        Args:
            mappings: surface_node_id → canonical_slot_id pairs to register.

        Raises:
            NodeNotTrackedError: If any surface_id in mappings is not in self.states.
        """
        if not mappings:
            return self

        new_states = dict(self.states)
        registered = 0
        for surface_id, slot_id in mappings.items():
            if surface_id not in new_states:
                raise NodeNotTrackedError(
                    f"register_slot_memberships: surface_id={surface_id!r} not in tracker"
                )
            state = new_states[surface_id]
            if state.slot_id != slot_id:
                new_states[surface_id] = state.model_copy(update={"slot_id": slot_id})
                registered += 1

        log.info("slot_memberships_registered", count=registered)
        return self.model_copy(update={"states": new_states})

    # ------------------------------------------------------------------
    # Canonical slot first-seen tracking (set by Stage 4.7, read by signals)
    # ------------------------------------------------------------------

    def record_canonical_slot_first_seen(
        self, slot_id: str, turn_number: int
    ) -> NodeStateTracker:
        """Return new tracker with slot_id recorded as first seen at turn_number.

        Idempotent: if slot_id already has a first-seen entry, returns self.
        """
        if slot_id in self.canonical_slot_first_seen:
            return self
        return self.model_copy(
            update={
                "canonical_slot_first_seen": {
                    **self.canonical_slot_first_seen,
                    slot_id: turn_number,
                }
            }
        )

    # ------------------------------------------------------------------
    # State accessors
    # ------------------------------------------------------------------

    def get_state(self, tracking_key: SurfaceNodeId) -> NodeState:
        """Return NodeState for tracking_key.

        Raises:
            NodeNotTrackedError: If tracking_key is not registered.
        """
        if tracking_key not in self.states:
            raise NodeNotTrackedError(
                f"get_state: tracking_key={tracking_key!r} not registered"
            )
        return self.states[tracking_key]

    def try_get_state(self, tracking_key: SurfaceNodeId) -> Optional[NodeState]:
        """Return NodeState for tracking_key, or None if not registered."""
        return self.states.get(tracking_key)

    def get_all_states(self) -> dict[str, NodeState]:
        """Return a copy of all tracked node states keyed by tracking_key."""
        return dict(self.states)

    def surfaces_in_slot(self, slot_id: SlotId) -> list[SurfaceNodeId]:
        """Return all surface UUIDs whose state.slot_id matches slot_id."""
        return [
            SurfaceNodeId(sid)
            for sid, state in self.states.items()
            if state.slot_id == slot_id
        ]

    def slot_id_for_surface(self, surface_id: SurfaceNodeId) -> Optional[SlotId]:
        """Return the slot_id property of the surface state, or None if untracked or unmapped."""
        state = self.states.get(surface_id)
        return state.slot_id if state is not None else None

    def is_empty(self) -> bool:
        """True if no nodes are tracked."""
        return len(self.states) == 0

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict for database persistence."""
        states_dict: dict[str, Any] = {}
        for tracking_key, state in self.states.items():
            d = state.model_dump()
            # frozenset → list for JSON
            d["connected_node_ids"] = list(state.connected_node_ids)
            # tuple → list for JSON
            d["all_response_depths"] = list(state.all_response_depths)
            d["quality_history"] = {
                "elaboration_scores": list(state.quality_history.elaboration_scores),
                "charge_scores": list(state.quality_history.charge_scores),
            }
            states_dict[tracking_key] = d

        result: dict[str, Any] = {
            "schema_version": NODE_TRACKER_SCHEMA_VERSION,
            "previous_focus": self.previous_focus,
            "states": states_dict,
            "canonical_slot_first_seen": dict(self.canonical_slot_first_seen),
        }
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NodeStateTracker:
        """Reconstruct from a previously persisted dict.

        Raises:
            ValueError: If schema version doesn't match current version.
        """
        schema_version = data.get("schema_version", 1)
        if schema_version != NODE_TRACKER_SCHEMA_VERSION:
            raise ValueError(
                f"Incompatible node_tracker_state schema version: "
                f"expected {NODE_TRACKER_SCHEMA_VERSION}, got {schema_version}"
            )

        states: dict[SurfaceNodeId, NodeState] = {}
        for tracking_key, state_dict in data.get("states", {}).items():
            state_dict = dict(state_dict)

            # connected_node_ids: list → frozenset
            state_dict["connected_node_ids"] = frozenset(
                state_dict.get("connected_node_ids", [])
            )

            # all_response_depths: list → tuple
            state_dict["all_response_depths"] = tuple(
                state_dict.get("all_response_depths", [])
            )

            # quality_history
            qh_data = state_dict.pop("quality_history", None)
            if qh_data is None:
                quality_history = NodeQualityHistory()
            else:
                quality_history = NodeQualityHistory(
                    elaboration_scores=tuple(qh_data.get("elaboration_scores", [])),
                    charge_scores=tuple(qh_data.get("charge_scores", [])),
                )
            state_dict["quality_history"] = quality_history

            states[SurfaceNodeId(tracking_key)] = NodeState(**state_dict)

        return cls(
            states=states,
            previous_focus=data.get("previous_focus"),
            canonical_slot_first_seen=dict(data.get("canonical_slot_first_seen", {})),
            schema_version=NODE_TRACKER_SCHEMA_VERSION,
        )
