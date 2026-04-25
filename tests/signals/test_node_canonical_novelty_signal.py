"""Tests for NodeCanonicalNoveltySignal — canonical-slot-based novelty detection.

In the new design, Stage 4.7 pre-populates canonical_slot_first_seen on the
sealed tracker before signals run. The signal is now read-only: it reads
canonical_slot_first_seen to classify nodes as new / confirming / orphan.
"""

from unittest.mock import MagicMock

import pytest

from src.signals.graph.node_signals import NodeCanonicalNoveltySignal


def _make_tracker(node_ids: list[str], first_seen: dict[str, int]) -> MagicMock:
    """Build a mock NodeStateTracker with pre-populated canonical_slot_first_seen.

    Args:
        node_ids: tracking keys present in tracker.states
        first_seen: canonical_slot_first_seen dict (maps tracking_key → first_seen_turn)
    """
    tracker = MagicMock()
    tracker.get_all_states.return_value = {nid: MagicMock() for nid in node_ids}
    tracker.canonical_slot_first_seen = first_seen
    return tracker


def _make_context(turn_number: int = 5) -> MagicMock:
    ctx = MagicMock()
    ctx.turn_number = turn_number
    return ctx


def _make_signal(node_ids: list[str], first_seen: dict[str, int]) -> NodeCanonicalNoveltySignal:
    tracker = _make_tracker(node_ids, first_seen)
    return NodeCanonicalNoveltySignal(tracker)


# ---------------------------------------------------------------------------
# Core category tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_node_with_new_slot_returns_new():
    """Node whose tracking key first appeared on the current turn -> 'new'."""
    signal = _make_signal(["node-a"], first_seen={"node-a": 3})
    result = await signal.detect(_make_context(turn_number=3), MagicMock(), "")
    assert result["node-a"] == "new"


@pytest.mark.asyncio
async def test_node_with_preexisting_slot_returns_confirming():
    """Node whose tracking key first appeared on a prior turn -> 'confirming'."""
    signal = _make_signal(["node-b"], first_seen={"node-b": 2})
    result = await signal.detect(_make_context(turn_number=5), MagicMock(), "")
    assert result["node-b"] == "confirming"


@pytest.mark.asyncio
async def test_node_not_in_first_seen_returns_orphan():
    """Node whose tracking key is absent from canonical_slot_first_seen -> 'orphan'.

    canonical_slot_first_seen must be non-empty overall (otherwise signal
    returns {} immediately), but the specific node is absent.
    """
    # "other-node" keeps the dict non-empty; "node-c" is absent → orphan
    signal = _make_signal(["node-c"], first_seen={"other-node": 1})
    result = await signal.detect(_make_context(turn_number=4), MagicMock(), "")
    assert result["node-c"] == "orphan"


# ---------------------------------------------------------------------------
# Feature flag: canonical slots effectively disabled (empty first_seen)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_returns_empty_dict_when_first_seen_is_empty():
    """When canonical_slot_first_seen is empty, returns {} (canonical slots not yet active)."""
    signal = _make_signal(["node-d"], first_seen={})
    result = await signal.detect(_make_context(turn_number=1), MagicMock(), "")
    assert result == {}


# ---------------------------------------------------------------------------
# Multi-node tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multiple_nodes_correct_categories():
    """Mixed nodes: some new, some confirming, some orphan."""
    first_seen = {
        "node-new": 5,       # first seen this turn → new
        "node-confirming": 1,  # first seen on turn 1 → confirming
        # node-orphan absent → orphan
        "sentinel": 1,         # keeps dict non-empty so signal doesn't short-circuit
    }
    signal = _make_signal(["node-new", "node-confirming", "node-orphan"], first_seen=first_seen)
    result = await signal.detect(_make_context(turn_number=5), MagicMock(), "")

    assert result["node-new"] == "new"
    assert result["node-confirming"] == "confirming"
    assert result["node-orphan"] == "orphan"


@pytest.mark.asyncio
async def test_empty_tracker_returns_empty_dict():
    """When no nodes are tracked, result is an empty dict."""
    signal = _make_signal([], first_seen={"slot-x": 1})
    result = await signal.detect(_make_context(turn_number=5), MagicMock(), "")
    assert result == {}


# ---------------------------------------------------------------------------
# Slot first-seen persistence across turns (simulated via tracker state)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_slot_first_seen_persists_across_turns():
    """Slot first seen on turn 2 is correctly identified as confirming on turn 3.

    In production, canonical_slot_first_seen is persisted to DB and loaded
    next turn by SessionService → NodeStateTracker.from_dict(). This test
    simulates that by constructing the second-turn tracker with the prior
    first_seen dict already populated.
    """
    # Turn 2: slot-alpha first seen
    signal_t2 = _make_signal(["node-e"], first_seen={"node-e": 2})
    result_t2 = await signal_t2.detect(_make_context(turn_number=2), MagicMock(), "")
    assert result_t2["node-e"] == "new"

    # Turn 3: same node, same slot still present in first_seen with turn=2 → confirming
    signal_t3 = _make_signal(["node-e"], first_seen={"node-e": 2})
    result_t3 = await signal_t3.detect(_make_context(turn_number=3), MagicMock(), "")
    assert result_t3["node-e"] == "confirming"
