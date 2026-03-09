"""Tests for NodeCanonicalNoveltySignal — canonical-slot-based novelty detection."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.signals.graph.node_signals import NodeCanonicalNoveltySignal


def _make_mapping(slot_id: str) -> MagicMock:
    """Build a mock SlotMapping with the given canonical_slot_id."""
    mapping = MagicMock()
    mapping.canonical_slot_id = slot_id
    return mapping


def _make_tracker(
    node_states: dict,
    *,
    has_canonical_repo: bool = True,
    mapping_lookup: dict | None = None,
) -> MagicMock:
    """Build a mock NodeStateTracker.

    Args:
        node_states: Dict of node_id -> NodeState (can be mock objects)
        has_canonical_repo: Whether canonical_slot_repo is set (True = enabled)
        mapping_lookup: Dict of node_id -> slot_id (None means no mapping exists)
    """
    tracker = MagicMock()
    tracker.get_all_states.return_value = node_states

    if not has_canonical_repo:
        tracker.canonical_slot_repo = None
        return tracker

    repo = MagicMock()
    mapping_lookup = mapping_lookup or {}

    async def get_mapping(node_id: str):
        slot_id = mapping_lookup.get(node_id)
        if slot_id is None:
            return None
        return _make_mapping(slot_id)

    repo.get_mapping_for_node = AsyncMock(side_effect=get_mapping)
    tracker.canonical_slot_repo = repo
    return tracker


def _make_context(turn_number: int = 5) -> MagicMock:
    ctx = MagicMock()
    ctx.turn_number = turn_number
    return ctx


def _make_signal(
    node_states: dict,
    *,
    has_canonical_repo: bool = True,
    mapping_lookup: dict | None = None,
) -> NodeCanonicalNoveltySignal:
    """Instantiate NodeCanonicalNoveltySignal with a mocked node_tracker."""
    tracker = _make_tracker(
        node_states,
        has_canonical_repo=has_canonical_repo,
        mapping_lookup=mapping_lookup,
    )
    signal = NodeCanonicalNoveltySignal(tracker)
    return signal


# ---------------------------------------------------------------------------
# Core category tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_node_with_new_slot_returns_new():
    """Node whose slot is first seen on the current turn -> 'new'."""
    states = {"node-a": MagicMock()}
    signal = _make_signal(states, mapping_lookup={"node-a": "slot-1"})
    ctx = _make_context(turn_number=3)

    result = await signal.detect(ctx, MagicMock(), "")

    assert result["node-a"] == "new"


@pytest.mark.asyncio
async def test_node_with_preexisting_slot_returns_confirming():
    """Node whose slot was first seen on a prior turn -> 'confirming'."""
    states = {"node-b": MagicMock()}
    signal = _make_signal(states, mapping_lookup={"node-b": "slot-1"})

    # First encounter: turn 2
    await signal.detect(_make_context(turn_number=2), MagicMock(), "")

    # Subsequent encounter on different node mapping to same slot: turn 5
    states2 = {"node-b2": MagicMock()}
    signal.node_tracker = _make_tracker(
        states2,
        has_canonical_repo=True,
        mapping_lookup={"node-b2": "slot-1"},
    )
    result = await signal.detect(_make_context(turn_number=5), MagicMock(), "")

    assert result["node-b2"] == "confirming"


@pytest.mark.asyncio
async def test_node_with_no_canonical_mapping_returns_orphan():
    """Node with no slot mapping -> 'orphan'."""
    states = {"node-c": MagicMock()}
    # No mapping for node-c
    signal = _make_signal(states, mapping_lookup={})
    ctx = _make_context(turn_number=4)

    result = await signal.detect(ctx, MagicMock(), "")

    assert result["node-c"] == "orphan"


# ---------------------------------------------------------------------------
# Feature flag: canonical slots disabled
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_returns_empty_dict_when_canonical_slots_disabled():
    """When canonical_slot_repo is None, returns empty dict."""
    states = {"node-d": MagicMock()}
    signal = _make_signal(states, has_canonical_repo=False)
    ctx = _make_context(turn_number=1)

    result = await signal.detect(ctx, MagicMock(), "")

    assert result == {}


# ---------------------------------------------------------------------------
# Multi-node tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multiple_nodes_correct_categories():
    """Mixed nodes: some new, some confirming, some orphan."""
    # Pre-seed slot-existing as seen on turn 1
    signal = _make_signal(
        {"seeder": MagicMock()},
        mapping_lookup={"seeder": "slot-existing"},
    )
    await signal.detect(_make_context(turn_number=1), MagicMock(), "")

    # Now detect on turn 5 with three different nodes
    states = {
        "node-new": MagicMock(),
        "node-confirming": MagicMock(),
        "node-orphan": MagicMock(),
    }
    signal.node_tracker = _make_tracker(
        states,
        has_canonical_repo=True,
        mapping_lookup={
            "node-new": "slot-brand-new",  # first time → new
            "node-confirming": "slot-existing",  # seen on turn 1 → confirming
            # node-orphan has no mapping → orphan
        },
    )
    result = await signal.detect(_make_context(turn_number=5), MagicMock(), "")

    assert result["node-new"] == "new"
    assert result["node-confirming"] == "confirming"
    assert result["node-orphan"] == "orphan"


@pytest.mark.asyncio
async def test_empty_tracker_returns_empty_dict():
    """When no nodes are tracked, result is an empty dict."""
    signal = _make_signal({})
    ctx = _make_context(turn_number=5)

    result = await signal.detect(ctx, MagicMock(), "")

    assert result == {}


# ---------------------------------------------------------------------------
# Slot first-seen persistence across turns
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_slot_first_seen_persists_across_detect_calls():
    """Slot first seen on turn 2 is correctly identified as confirming on turn 3."""
    states = {"node-e": MagicMock()}
    signal = _make_signal(states, mapping_lookup={"node-e": "slot-alpha"})

    # Turn 2: slot-alpha first seen
    result_t2 = await signal.detect(_make_context(turn_number=2), MagicMock(), "")
    assert result_t2["node-e"] == "new"

    # Turn 3: same node, same slot → confirming (slot already in _slot_first_seen)
    result_t3 = await signal.detect(_make_context(turn_number=3), MagicMock(), "")
    assert result_t3["node-e"] == "confirming"
