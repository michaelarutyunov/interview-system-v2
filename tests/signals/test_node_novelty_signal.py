"""Tests for NodeNoveltySignal — age-based novelty score for recently-created nodes."""

from unittest.mock import MagicMock

import pytest

from src.signals.graph.node_signals import NodeNoveltySignal


def _make_node_state(node_id: str, created_at_turn: int) -> MagicMock:
    """Build a mock NodeState with the given creation turn."""
    state = MagicMock()
    state.created_at_turn = created_at_turn
    return state


def _make_tracker(node_states: dict) -> MagicMock:
    """Build a mock NodeStateTracker returning the given node_states dict."""
    tracker = MagicMock()
    tracker.get_all_states.return_value = node_states
    return tracker


def _make_context(turn_number: int) -> MagicMock:
    ctx = MagicMock()
    ctx.turn_number = turn_number
    return ctx


def _make_signal(node_states: dict) -> NodeNoveltySignal:
    """Instantiate NodeNoveltySignal with a mocked node_tracker."""
    signal = NodeNoveltySignal.__new__(NodeNoveltySignal)
    signal.node_tracker = _make_tracker(node_states)
    return signal


# ---------------------------------------------------------------------------
# Category boundary tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_node_created_this_turn_is_high():
    """Node created at current turn -> age=0, score=1.0, category='high'."""
    current_turn = 5
    states = {"node-a": _make_node_state("node-a", created_at_turn=current_turn)}
    signal = _make_signal(states)
    ctx = _make_context(current_turn)

    result = await signal.detect(ctx, MagicMock(), "")

    assert result["node-a"] == "high"


@pytest.mark.asyncio
async def test_node_created_3_turns_ago_is_medium():
    """Node created 3 turns ago -> age=3, score=0.4, category='medium'."""
    current_turn = 10
    states = {"node-b": _make_node_state("node-b", created_at_turn=7)}
    signal = _make_signal(states)
    ctx = _make_context(current_turn)

    result = await signal.detect(ctx, MagicMock(), "")

    assert result["node-b"] == "medium"


@pytest.mark.asyncio
async def test_node_created_5_turns_ago_is_low():
    """Node created 5+ turns ago -> age=5, score=0.0, category='low'."""
    current_turn = 8
    states = {"node-c": _make_node_state("node-c", created_at_turn=3)}
    signal = _make_signal(states)
    ctx = _make_context(current_turn)

    result = await signal.detect(ctx, MagicMock(), "")

    assert result["node-c"] == "low"


@pytest.mark.asyncio
async def test_node_created_10_turns_ago_is_low():
    """Node created well past decay window -> score clamped at 0.0, category='low'."""
    current_turn = 15
    states = {"node-d": _make_node_state("node-d", created_at_turn=5)}
    signal = _make_signal(states)
    ctx = _make_context(current_turn)

    result = await signal.detect(ctx, MagicMock(), "")

    assert result["node-d"] == "low"


# ---------------------------------------------------------------------------
# Decay formula linearity tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decay_at_turn_0_is_1_0():
    """At age=0 (created this turn), raw score is 1.0 (high)."""
    signal = NodeNoveltySignal.__new__(NodeNoveltySignal)
    assert signal._categorize_novelty(1.0) == "high"


@pytest.mark.asyncio
async def test_decay_at_turn_2_is_0_6():
    """At age=2, raw score = 1.0 - (2/5) = 0.6 -> boundary between high and medium."""
    current_turn = 5
    states = {"node-e": _make_node_state("node-e", created_at_turn=3)}  # age=2, score=0.6
    signal = _make_signal(states)
    ctx = _make_context(current_turn)

    result = await signal.detect(ctx, MagicMock(), "")

    # score=0.6 exactly -> high (>= 0.6)
    assert result["node-e"] == "high"


@pytest.mark.asyncio
async def test_decay_at_turn_5_is_0_0():
    """At age=5 (DECAY_WINDOW), raw score = 0.0 -> low."""
    current_turn = 10
    states = {"node-f": _make_node_state("node-f", created_at_turn=5)}  # age=5, score=0.0
    signal = _make_signal(states)
    ctx = _make_context(current_turn)

    result = await signal.detect(ctx, MagicMock(), "")

    assert result["node-f"] == "low"


# ---------------------------------------------------------------------------
# Multiple nodes at different ages
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multiple_nodes_different_ages():
    """Mixture of node ages produces correct category for each."""
    current_turn = 10
    states = {
        "fresh": _make_node_state("fresh", created_at_turn=10),   # age=0 -> high
        "mid": _make_node_state("mid", created_at_turn=7),        # age=3, score=0.4 -> medium
        "old": _make_node_state("old", created_at_turn=5),        # age=5, score=0.0 -> low
    }
    signal = _make_signal(states)
    ctx = _make_context(current_turn)

    result = await signal.detect(ctx, MagicMock(), "")

    assert result["fresh"] == "high"
    assert result["mid"] == "medium"
    assert result["old"] == "low"


# ---------------------------------------------------------------------------
# Empty tracker
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_tracker_returns_empty_dict():
    """When no nodes are tracked, result is an empty dict."""
    signal = _make_signal({})
    ctx = _make_context(turn_number=5)

    result = await signal.detect(ctx, MagicMock(), "")

    assert result == {}
