"""Test NodeStateTracker schema v2 changes for canonical_slot_first_seen."""

import pytest
from src.services.node_state_tracker import (
    NodeStateTracker,
    NODE_TRACKER_SCHEMA_VERSION,
)


class TestCanonicalSlotFirstSeen:
    """Test canonical_slot_first_seen persistence in NodeStateTracker."""

    def test_schema_version_is_3(self):
        """Schema version v3 after adding NodeQualityHistory (per-concept LLM quality)."""
        assert NODE_TRACKER_SCHEMA_VERSION == 3

    def test_canonical_slot_first_seen_initialized_empty(self):
        """canonical_slot_first_seen should be initialized as empty dict."""
        tracker = NodeStateTracker()
        assert hasattr(tracker, "canonical_slot_first_seen")
        assert tracker.canonical_slot_first_seen == {}

    def test_canonical_slot_first_seen_persists_in_to_dict(self):
        """canonical_slot_first_seen should be included in to_dict output."""
        tracker = NodeStateTracker()
        tracker.canonical_slot_first_seen = {"slot-1": 1, "slot-2": 3}

        data = tracker.to_dict()
        assert "canonical_slot_first_seen" in data
        assert data["canonical_slot_first_seen"] == {"slot-1": 1, "slot-2": 3}

    def test_canonical_slot_first_seen_restores_from_dict_v2(self):
        """from_dict should restore canonical_slot_first_seen from v2 data."""
        data = {
            "schema_version": 2,
            "previous_focus": None,
            "states": {},
            "canonical_slot_first_seen": {"slot-a": 5, "slot-b": 10},
        }

        tracker = NodeStateTracker.from_dict(data)
        assert tracker.canonical_slot_first_seen == {"slot-a": 5, "slot-b": 10}

    def test_from_dict_backward_compatible_with_v1(self):
        """from_dict should handle v1 data without canonical_slot_first_seen."""
        data = {
            "schema_version": 1,
            "previous_focus": "node-123",
            "states": {},
        }

        tracker = NodeStateTracker.from_dict(data)
        assert tracker.canonical_slot_first_seen == {}
        assert tracker.previous_focus == "node-123"

    def test_from_dict_rejects_incompatible_schema_version(self):
        """from_dict should raise ValueError for unsupported schema versions."""
        data = {
            "schema_version": 99,
            "previous_focus": None,
            "states": {},
        }

        with pytest.raises(
            ValueError, match="Incompatible node_tracker_state schema version"
        ):
            NodeStateTracker.from_dict(data)

    def test_canonical_slot_first_seen_mutable_across_serialization(self):
        """canonical_slot_first_seen should survive round-trip serialization."""
        tracker = NodeStateTracker()
        tracker.canonical_slot_first_seen["slot-x"] = 7

        # Serialize and deserialize
        data = tracker.to_dict()
        restored = NodeStateTracker.from_dict(data)

        # Changes persist
        assert restored.canonical_slot_first_seen == {"slot-x": 7}

        # Further changes on restored tracker work
        restored.canonical_slot_first_seen["slot-y"] = 15
        assert restored.canonical_slot_first_seen == {"slot-x": 7, "slot-y": 15}
