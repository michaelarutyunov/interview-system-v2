"""Test NodeStateTracker schema changes and surface-primary keyspace."""

import pytest
from src.services.node_state_tracker import (
    NodeNotTrackedError,
    NodeStateTracker,
    NODE_TRACKER_SCHEMA_VERSION,
)
from src.domain.models.identity import SurfaceNodeId
from src.domain.models.node_state import NodeState


def _make_state(
    node_id: str, label: str = "test", turn: int = 1, **kwargs
) -> NodeState:
    return NodeState(
        node_id=node_id,
        label=label,
        created_at_turn=turn,
        depth=0,
        node_type="attribute",
        **kwargs,
    )


def _tracker_with_states(states: dict[str, NodeState]) -> NodeStateTracker:
    """Build a tracker with pre-populated states (bypasses register_node)."""
    return NodeStateTracker(states=states)


class TestSchemaVersion:
    """Test schema version after surface-primary inversion."""

    def test_schema_version_is_6(self):
        """Schema version v6 after surface-primary inversion."""
        assert NODE_TRACKER_SCHEMA_VERSION == 6


class TestCanonicalSlotFirstSeen:
    """Test canonical_slot_first_seen persistence in NodeStateTracker."""

    def test_canonical_slot_first_seen_initialized_empty(self):
        """canonical_slot_first_seen initialises as empty dict."""
        tracker = NodeStateTracker()
        assert hasattr(tracker, "canonical_slot_first_seen")
        assert tracker.canonical_slot_first_seen == {}

    def test_canonical_slot_first_seen_persists_in_to_dict(self):
        """canonical_slot_first_seen is included in to_dict output."""
        tracker = NodeStateTracker()
        tracker = tracker.record_canonical_slot_first_seen("slot-1", 1)
        tracker = tracker.record_canonical_slot_first_seen("slot-2", 3)

        data = tracker.to_dict()
        assert "canonical_slot_first_seen" in data
        assert data["canonical_slot_first_seen"] == {"slot-1": 1, "slot-2": 3}

    def test_canonical_slot_first_seen_round_trip(self):
        """canonical_slot_first_seen survives round-trip serialization."""
        tracker = NodeStateTracker()
        tracker = tracker.record_canonical_slot_first_seen("slot-x", 7)

        data = tracker.to_dict()
        restored = NodeStateTracker.from_dict(data)

        assert restored.canonical_slot_first_seen == {"slot-x": 7}

    def test_record_canonical_slot_first_seen_idempotent(self):
        """record_canonical_slot_first_seen does not overwrite existing entries."""
        tracker = NodeStateTracker()
        tracker = tracker.record_canonical_slot_first_seen("slot-x", 3)
        tracker = tracker.record_canonical_slot_first_seen(
            "slot-x", 7
        )  # should not overwrite
        assert tracker.canonical_slot_first_seen["slot-x"] == 3


class TestSurfacePrimaryKeyspace:
    """Test surface-primary keyspace contract (B1)."""

    def test_register_node_creates_surface_keyed_entry(self):
        """register_node creates entry keyed by surface UUID."""
        from src.domain.models.knowledge_graph import KGNode

        node = KGNode(
            id="abc-123", session_id="s1", label="test", node_type="attribute"
        )
        tracker = NodeStateTracker()
        tracker = tracker.register_node(node, turn_number=1)

        assert "abc-123" in tracker.states
        assert tracker.states["abc-123"].node_id == "abc-123"

    def test_update_focus_sets_previous_focus(self):
        """update_focus with surface UUID sets previous_focus to that UUID."""
        state = _make_state("abc-123")
        tracker = _tracker_with_states({"abc-123": state})

        result = tracker.update_focus(
            tracking_key=SurfaceNodeId("abc-123"),
            turn_number=1,
            strategy="ascend",
        )

        assert result.previous_focus == "abc-123"

    def test_update_focus_slot_id_defaults_none(self):
        """Newly registered nodes have slot_id=None until register_slot_memberships."""
        state = _make_state("abc-123")
        tracker = _tracker_with_states({"abc-123": state})

        assert tracker.states["abc-123"].slot_id is None

    def test_update_focus_raises_on_untracked_key(self):
        """update_focus raises NodeNotTrackedError for unknown keys."""
        tracker = NodeStateTracker()

        with pytest.raises(NodeNotTrackedError, match="not registered"):
            tracker.update_focus(
                tracking_key=SurfaceNodeId("nonexistent"),
                turn_number=1,
                strategy="ascend",
            )

    def test_no_previous_focus_node_id_field(self):
        """previous_focus_node_id field does not exist on tracker."""
        tracker = NodeStateTracker()
        assert not hasattr(tracker, "previous_focus_node_id")

    def test_from_dict_rejects_old_schema(self):
        """from_dict raises ValueError for schema version != 6."""
        data = {"schema_version": 5, "previous_focus": None, "states": {}}
        with pytest.raises(ValueError, match="expected 6, got 5"):
            NodeStateTracker.from_dict(data)

    def test_round_trip_preserves_surface_keys(self):
        """Surface UUID keys survive round-trip serialization."""
        state = _make_state("uuid-alpha")
        tracker = _tracker_with_states({"uuid-alpha": state})
        tracker = tracker.update_focus(
            tracking_key=SurfaceNodeId("uuid-alpha"),
            turn_number=1,
            strategy="ground",
        )

        data = tracker.to_dict()
        restored = NodeStateTracker.from_dict(data)

        assert "uuid-alpha" in restored.states
        assert restored.previous_focus == "uuid-alpha"
        assert restored.states["uuid-alpha"].focus_count == 1

    def test_slot_id_preserved_in_round_trip(self):
        """slot_id on NodeState survives round-trip."""
        state = _make_state("uuid-beta", slot_id="slot_X")
        tracker = _tracker_with_states({"uuid-beta": state})

        data = tracker.to_dict()
        restored = NodeStateTracker.from_dict(data)

        assert restored.states["uuid-beta"].slot_id == "slot_X"

    def test_register_node_no_surface_node_ids(self):
        """NodeState no longer has surface_node_ids field."""
        from src.domain.models.knowledge_graph import KGNode

        node = KGNode(id="n1", session_id="s1", label="test", node_type="attribute")
        tracker = NodeStateTracker()
        tracker = tracker.register_node(node, turn_number=1)

        assert not hasattr(tracker.states["n1"], "surface_node_ids")


class TestRegisterSlotMemberships:
    """Test register_slot_memberships (B2)."""

    def test_register_sets_slot_id(self):
        """register_slot_memberships sets slot_id on surface states."""
        state_a = _make_state("a")
        state_b = _make_state("b")
        tracker = _tracker_with_states({"a": state_a, "b": state_b})

        result = tracker.register_slot_memberships({"a": "slot_X", "b": "slot_X"})

        assert result.states["a"].slot_id == "slot_X"
        assert result.states["b"].slot_id == "slot_X"

    def test_register_preserves_keyspace(self):
        """register_slot_memberships does NOT change the tracker keyspace."""
        state_a = _make_state("a")
        state_b = _make_state("b")
        tracker = _tracker_with_states({"a": state_a, "b": state_b})

        result = tracker.register_slot_memberships({"a": "slot_X", "b": "slot_X"})

        assert set(result.states.keys()) == {"a", "b"}
        assert "slot_X" not in result.states

    def test_register_preserves_previous_focus(self):
        """register_slot_memberships does not change previous_focus."""
        state_a = _make_state("a")
        tracker = _tracker_with_states({"a": state_a})
        tracker = tracker.update_focus(
            tracking_key=SurfaceNodeId("a"), turn_number=1, strategy="ascend"
        )

        result = tracker.register_slot_memberships({"a": "slot_X"})

        assert result.previous_focus == "a"

    def test_register_empty_mappings_is_noop(self):
        """Empty mappings returns self unchanged."""
        tracker = NodeStateTracker()
        result = tracker.register_slot_memberships({})
        assert result is tracker

    def test_register_untracked_surface_raises(self):
        """Untracked surface_id raises NodeNotTrackedError."""
        tracker = NodeStateTracker()

        with pytest.raises(NodeNotTrackedError, match="not in tracker"):
            tracker.register_slot_memberships({"unknown": "slot_X"})


class TestSlotAggregationHelpers:
    """Test surfaces_in_slot and slot_id_for_surface (B3)."""

    def test_surfaces_in_slot_returns_matching(self):
        """surfaces_in_slot returns all surfaces with matching slot_id."""
        state_a = _make_state("a", slot_id="slot_X")
        state_b = _make_state("b", slot_id="slot_X")
        state_c = _make_state("c")
        tracker = _tracker_with_states({"a": state_a, "b": state_b, "c": state_c})

        result = tracker.surfaces_in_slot("slot_X")

        assert set(result) == {"a", "b"}

    def test_surfaces_in_slot_empty_when_none_match(self):
        """surfaces_in_slot returns empty list when no surfaces have that slot."""
        state_a = _make_state("a")
        tracker = _tracker_with_states({"a": state_a})

        result = tracker.surfaces_in_slot("slot_nonexistent")

        assert result == []

    def test_slot_id_for_surface_returns_slot(self):
        """slot_id_for_surface returns slot_id for slotted surface."""
        state = _make_state("a", slot_id="slot_X")
        tracker = _tracker_with_states({"a": state})

        assert tracker.slot_id_for_surface("a") == "slot_X"

    def test_slot_id_for_surface_returns_none_unslotted(self):
        """slot_id_for_surface returns None for registered surface with no slot."""
        state = _make_state("a")
        tracker = _tracker_with_states({"a": state})

        assert tracker.slot_id_for_surface("a") is None

    def test_slot_id_for_surface_returns_none_unknown(self):
        """slot_id_for_surface returns None for nonexistent surface."""
        tracker = NodeStateTracker()

        assert tracker.slot_id_for_surface("nonexistent") is None
