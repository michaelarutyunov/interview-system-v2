"""Tests for NodeCanonicalNoveltySignal — canonical-slot-based novelty detection.

After surface-primary inversion (B3), the signal reads state.slot_id from each
tracked surface node, then looks up slot_first_seen[slot_id]. Surfaces without
a slot membership return 'orphan'.
"""

from unittest.mock import MagicMock

import pytest

from src.domain.models.node_state import NodeState
from src.services.node_state_tracker import NodeStateTracker
from src.signals.graph.node_signals import NodeCanonicalNoveltySignal


def _make_state(node_id: str, slot_id: str | None = None) -> NodeState:
    return NodeState(
        node_id=node_id,
        slot_id=slot_id,
        label="test",
        created_at_turn=1,
        depth=0,
        node_type="attribute",
    )


def _make_tracker_with_slots(
    surfaces: dict[str, str | None],
    first_seen: dict[str, int],
) -> NodeStateTracker:
    """Build a real NodeStateTracker with surface states and slot memberships.

    Args:
        surfaces: {surface_id: slot_id_or_None} — surface node states to register.
        first_seen: canonical_slot_first_seen dict (slot_id → turn_number).
    """
    states = {sid: _make_state(sid, slot_id=slot) for sid, slot in surfaces.items()}
    return NodeStateTracker(
        states=states,
        canonical_slot_first_seen=first_seen,
    )


def _make_context(turn_number: int = 5) -> MagicMock:
    ctx = MagicMock()
    ctx.turn_number = turn_number
    return ctx


# ---------------------------------------------------------------------------
# Core category tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_surface_with_new_slot_returns_new():
    """Surface whose slot_id first appeared on the current turn -> 'new'."""
    tracker = _make_tracker_with_slots(
        surfaces={"a": "slot_X"},
        first_seen={"slot_X": 3},
    )
    signal = NodeCanonicalNoveltySignal(tracker)
    result = await signal.detect(_make_context(turn_number=3), MagicMock(), "")
    assert result["a"] == "new"


@pytest.mark.asyncio
async def test_surface_with_preexisting_slot_returns_confirming():
    """Surface whose slot_id first appeared on a prior turn -> 'confirming'."""
    tracker = _make_tracker_with_slots(
        surfaces={"b": "slot_X"},
        first_seen={"slot_X": 2},
    )
    signal = NodeCanonicalNoveltySignal(tracker)
    result = await signal.detect(_make_context(turn_number=5), MagicMock(), "")
    assert result["b"] == "confirming"


@pytest.mark.asyncio
async def test_surface_without_slot_returns_orphan():
    """Surface with slot_id=None returns 'orphan'."""
    tracker = _make_tracker_with_slots(
        surfaces={"c": None},
        first_seen={"slot_X": 1},  # non-empty to avoid short-circuit
    )
    signal = NodeCanonicalNoveltySignal(tracker)
    result = await signal.detect(_make_context(turn_number=4), MagicMock(), "")
    assert result["c"] == "orphan"


@pytest.mark.asyncio
async def test_surface_slot_not_in_first_seen_returns_orphan():
    """Surface with slot_id not present in canonical_slot_first_seen -> 'orphan'."""
    tracker = _make_tracker_with_slots(
        surfaces={"d": "slot_Y"},
        first_seen={"slot_X": 1},  # slot_Y absent
    )
    signal = NodeCanonicalNoveltySignal(tracker)
    result = await signal.detect(_make_context(turn_number=4), MagicMock(), "")
    assert result["d"] == "orphan"


# ---------------------------------------------------------------------------
# Feature flag: canonical slots effectively disabled (empty first_seen)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_returns_empty_dict_when_first_seen_is_empty():
    """When canonical_slot_first_seen is empty, returns {}."""
    tracker = _make_tracker_with_slots(
        surfaces={"d": "slot_X"},
        first_seen={},
    )
    signal = NodeCanonicalNoveltySignal(tracker)
    result = await signal.detect(_make_context(turn_number=1), MagicMock(), "")
    assert result == {}


# ---------------------------------------------------------------------------
# Multi-node tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multiple_nodes_correct_categories():
    """Mixed surfaces: some new, some confirming, some orphan."""
    tracker = _make_tracker_with_slots(
        surfaces={
            "new-surface": "slot_new",
            "confirming-surface": "slot_confirming",
            "orphan-surface": None,
        },
        first_seen={
            "slot_new": 5,  # first seen this turn → new
            "slot_confirming": 1,  # first seen on turn 1 → confirming
        },
    )
    signal = NodeCanonicalNoveltySignal(tracker)
    result = await signal.detect(_make_context(turn_number=5), MagicMock(), "")

    assert result["new-surface"] == "new"
    assert result["confirming-surface"] == "confirming"
    assert result["orphan-surface"] == "orphan"


@pytest.mark.asyncio
async def test_empty_tracker_returns_empty_dict():
    """When no surfaces are tracked, result is an empty dict."""
    tracker = _make_tracker_with_slots(surfaces={}, first_seen={"slot-x": 1})
    signal = NodeCanonicalNoveltySignal(tracker)
    result = await signal.detect(_make_context(turn_number=5), MagicMock(), "")
    assert result == {}


# ---------------------------------------------------------------------------
# Multiple surfaces sharing one slot
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_two_surfaces_same_slot_both_new():
    """Two surfaces mapped to the same slot both return 'new' when slot is first seen."""
    tracker = _make_tracker_with_slots(
        surfaces={"a": "slot_X", "b": "slot_X"},
        first_seen={"slot_X": 2},
    )
    signal = NodeCanonicalNoveltySignal(tracker)
    result = await signal.detect(_make_context(turn_number=2), MagicMock(), "")
    assert result["a"] == "new"
    assert result["b"] == "new"


@pytest.mark.asyncio
async def test_two_surfaces_same_slot_both_confirming():
    """Two surfaces mapped to the same slot both return 'confirming' on later turns."""
    tracker = _make_tracker_with_slots(
        surfaces={"a": "slot_X", "b": "slot_X"},
        first_seen={"slot_X": 2},
    )
    signal = NodeCanonicalNoveltySignal(tracker)
    result = await signal.detect(_make_context(turn_number=3), MagicMock(), "")
    assert result["a"] == "confirming"
    assert result["b"] == "confirming"


@pytest.mark.asyncio
async def test_mixed_slotted_and_unslotted():
    """Mix of slotted and unslotted surfaces."""
    tracker = _make_tracker_with_slots(
        surfaces={"a": "slot_X", "b": "slot_X", "c": None},
        first_seen={"slot_X": 2},
    )
    signal = NodeCanonicalNoveltySignal(tracker)
    result = await signal.detect(_make_context(turn_number=2), MagicMock(), "")
    assert result["a"] == "new"
    assert result["b"] == "new"
    assert result["c"] == "orphan"
