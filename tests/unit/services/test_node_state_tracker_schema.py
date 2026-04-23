"""Test NodeStateTracker schema v2 changes for canonical_slot_first_seen."""

from unittest.mock import AsyncMock
from dataclasses import dataclass

import pytest
from src.services.node_state_tracker import (
    NodeStateTracker,
    NODE_TRACKER_SCHEMA_VERSION,
)
from src.domain.models.node_state import NodeState


@dataclass
class FakeSlotMapping:
    surface_node_id: str
    canonical_slot_id: str


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


class TestRemapToCanonicalSlots:
    """Test NodeStateTracker.remap_to_canonical_slots() re-keying logic."""

    def _make_tracker_with_repo(self, mappings: dict[str, str]):
        """Create tracker with a fake canonical_slot_repo returning given mappings."""
        repo = AsyncMock()
        repo.get_mapping_for_node = AsyncMock(
            side_effect=lambda sid: (
                FakeSlotMapping(sid, mappings[sid]) if sid in mappings else None
            )
        )
        return NodeStateTracker(canonical_slot_repo=repo)

    def _register_surface_node(self, tracker, node_id, label="test", turn=1):
        """Register a node directly under its surface ID (bypassing KGNode)."""
        state = NodeState(
            node_id=node_id, label=label, created_at_turn=turn, depth=0, node_type="attribute"
        )
        tracker.states[node_id] = state
        return state

    @pytest.mark.asyncio
    async def test_remap_simple_rekey(self):
        """Surface node re-keyed to canonical slot when no collision."""
        tracker = self._make_tracker_with_repo({"uuid-a": "slot-1"})
        state = self._register_surface_node(tracker, "uuid-a")

        await tracker.remap_to_canonical_slots()

        assert "uuid-a" not in tracker.states
        assert "slot-1" in tracker.states
        assert tracker.states["slot-1"] is state
        assert state.node_id == "slot-1"

    @pytest.mark.asyncio
    async def test_remap_merges_paraphrases(self):
        """Two surface nodes mapping to same slot merge their state."""
        tracker = self._make_tracker_with_repo(
            {"uuid-a": "slot-1", "uuid-b": "slot-1"}
        )
        state_a = self._register_surface_node(tracker, "uuid-a", "taste", 1)
        state_a.focus_count = 3
        state_a.yield_count = 2
        state_b = self._register_surface_node(tracker, "uuid-b", "flavor", 2)
        state_b.focus_count = 1
        state_b.yield_count = 1

        await tracker.remap_to_canonical_slots()

        assert "uuid-a" not in tracker.states
        assert "uuid-b" not in tracker.states
        merged = tracker.states["slot-1"]
        assert merged.focus_count == 4  # 3 + 1
        assert merged.yield_count == 3  # 2 + 1

    @pytest.mark.asyncio
    async def test_remap_updates_previous_focus(self):
        """previous_focus is re-keyed if it was a surface UUID."""
        tracker = self._make_tracker_with_repo({"uuid-a": "slot-1"})
        self._register_surface_node(tracker, "uuid-a")
        tracker.previous_focus = "uuid-a"

        await tracker.remap_to_canonical_slots()

        assert tracker.previous_focus == "slot-1"

    @pytest.mark.asyncio
    async def test_remap_noop_without_repo(self):
        """remap is a no-op when canonical_slot_repo is None."""
        tracker = NodeStateTracker()
        self._register_surface_node(tracker, "uuid-a")

        await tracker.remap_to_canonical_slots()

        assert "uuid-a" in tracker.states

    @pytest.mark.asyncio
    async def test_remap_noop_when_no_mappings(self):
        """remap is a no-op when no surface nodes have mappings."""
        tracker = self._make_tracker_with_repo({})
        self._register_surface_node(tracker, "uuid-a")

        await tracker.remap_to_canonical_slots()

        assert "uuid-a" in tracker.states
