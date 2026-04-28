"""Test NodeStateTracker schema changes and remap_to_canonical_slots logic."""

import pytest
from src.services.node_state_tracker import (
    NodeStateTracker,
    NODE_TRACKER_SCHEMA_VERSION,
)
from src.domain.models.node_state import NodeState


def _make_state(node_id: str, label: str = "test", turn: int = 1, **kwargs) -> NodeState:
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


class TestCanonicalSlotFirstSeen:
    """Test canonical_slot_first_seen persistence in NodeStateTracker."""

    def test_schema_version_is_4(self):
        """Schema version v4 after immutability migration."""
        assert NODE_TRACKER_SCHEMA_VERSION == 4

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

    def test_canonical_slot_first_seen_restores_from_dict_v2(self):
        """from_dict restores canonical_slot_first_seen from v2 data."""
        data = {
            "schema_version": 2,
            "previous_focus": None,
            "states": {},
            "canonical_slot_first_seen": {"slot-a": 5, "slot-b": 10},
        }
        tracker = NodeStateTracker.from_dict(data)
        assert tracker.canonical_slot_first_seen == {"slot-a": 5, "slot-b": 10}

    def test_from_dict_backward_compatible_with_v1(self):
        """from_dict handles v1 data without canonical_slot_first_seen."""
        data = {
            "schema_version": 1,
            "previous_focus": "node-123",
            "states": {},
        }
        tracker = NodeStateTracker.from_dict(data)
        assert tracker.canonical_slot_first_seen == {}
        assert tracker.previous_focus == "node-123"

    def test_from_dict_rejects_incompatible_schema_version(self):
        """from_dict raises ValueError for unsupported schema versions."""
        data = {"schema_version": 99, "previous_focus": None, "states": {}}
        with pytest.raises(ValueError, match="Incompatible node_tracker_state schema version"):
            NodeStateTracker.from_dict(data)

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
        tracker = tracker.record_canonical_slot_first_seen("slot-x", 7)  # should not overwrite
        assert tracker.canonical_slot_first_seen["slot-x"] == 3


class TestRemapToCanonicalSlots:
    """Test NodeStateTracker.remap_to_canonical_slots() re-keying logic."""

    def test_remap_simple_rekey(self):
        """Surface node kept alongside canonical slot entry after remap."""
        state = _make_state("uuid-a")
        tracker = _tracker_with_states({"uuid-a": state})

        tracker = tracker.remap_to_canonical_slots({"uuid-a": "slot-1"})

        assert "uuid-a" in tracker.states  # surface entry kept
        assert "slot-1" in tracker.states
        assert tracker.states["slot-1"].node_id == "slot-1"

    def test_remap_merges_paraphrases(self):
        """Two surface nodes mapping to same slot — surface entries kept, slot gets merged state."""
        state_a = _make_state("uuid-a", "taste", focus_count=3, yield_count=2)
        state_b = _make_state("uuid-b", "flavor", focus_count=1, yield_count=1)
        tracker = _tracker_with_states({"uuid-a": state_a, "uuid-b": state_b})

        tracker = tracker.remap_to_canonical_slots({"uuid-a": "slot-1", "uuid-b": "slot-1"})

        assert "uuid-a" in tracker.states  # surface entries kept
        assert "uuid-b" in tracker.states
        merged = tracker.states["slot-1"]
        assert merged.focus_count == 4   # 3 + 1
        assert merged.yield_count == 3   # 2 + 1

    def test_remap_updates_previous_focus(self):
        """previous_focus stays as surface UUID — surface entry still exists."""
        state = _make_state("uuid-a")
        tracker = NodeStateTracker(states={"uuid-a": state}, previous_focus="uuid-a")

        tracker = tracker.remap_to_canonical_slots({"uuid-a": "slot-1"})

        assert tracker.previous_focus == "uuid-a"

    def test_remap_noop_with_empty_mappings(self):
        """remap with empty mappings dict returns self unchanged."""
        state = _make_state("uuid-a")
        tracker = _tracker_with_states({"uuid-a": state})

        result = tracker.remap_to_canonical_slots({})

        assert result is tracker

    def test_remap_noop_when_no_matching_keys(self):
        """remap is a no-op when mappings refer to nodes not in states."""
        state = _make_state("uuid-a")
        tracker = _tracker_with_states({"uuid-a": state})

        tracker2 = tracker.remap_to_canonical_slots({"uuid-b": "slot-1"})

        # uuid-b not in states so nothing changes; same key still present
        assert "uuid-a" in tracker2.states
