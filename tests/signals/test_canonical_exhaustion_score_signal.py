"""Tests for CanonicalExhaustionScoreSignal — canonical-slot exhaustion average."""

from unittest.mock import MagicMock

import pytest

from src.signals.graph.graph_signals import CanonicalExhaustionScoreSignal


def _make_node_state(focus_count: int = 0, turns_since_last_yield: int = 0,
                     current_focus_streak: int = 0, all_response_depths=None) -> MagicMock:
    state = MagicMock()
    state.focus_count = focus_count
    state.turns_since_last_yield = turns_since_last_yield
    state.current_focus_streak = current_focus_streak
    state.all_response_depths = all_response_depths or []
    return state


def _make_context(states: dict, canonical_slot_repo=None) -> MagicMock:
    if canonical_slot_repo is None:
        canonical_slot_repo = MagicMock()
    ctx = MagicMock()
    tracker = MagicMock()
    tracker.states = states
    tracker.canonical_slot_repo = canonical_slot_repo
    ctx.node_tracker = tracker
    return ctx


# ---------------------------------------------------------------------------
# Guard-rail tests (returns {})
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_returns_empty_when_node_tracker_is_none():
    ctx = MagicMock()
    ctx.node_tracker = None
    signal = CanonicalExhaustionScoreSignal()
    result = await signal.detect(ctx, MagicMock(), "")
    assert result == {}


@pytest.mark.asyncio
async def test_returns_empty_when_states_is_empty():
    ctx = _make_context(states={})
    signal = CanonicalExhaustionScoreSignal()
    result = await signal.detect(ctx, MagicMock(), "")
    assert result == {}


@pytest.mark.asyncio
async def test_returns_empty_when_canonical_slot_repo_is_none():
    """Bug-fix guard: must return {} rather than silently using surface nodes."""
    ctx = _make_context(
        states={"node-a": _make_node_state(focus_count=3, turns_since_last_yield=2)},
    )
    ctx.node_tracker.canonical_slot_repo = None
    signal = CanonicalExhaustionScoreSignal()
    result = await signal.detect(ctx, MagicMock(), "")
    assert result == {}


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fresh_node_scores_zero():
    """A node never focused returns exhaustion 0.0."""
    ctx = _make_context(states={"node-a": _make_node_state(focus_count=0)})
    signal = CanonicalExhaustionScoreSignal()
    result = await signal.detect(ctx, MagicMock(), "")
    assert result["graph.canonical_exhaustion_score"] == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_returns_float_in_range_for_single_node():
    """Single focused node returns a score in [0, 1]."""
    ctx = _make_context(
        states={"node-a": _make_node_state(focus_count=2, turns_since_last_yield=5,
                                            current_focus_streak=2)}
    )
    signal = CanonicalExhaustionScoreSignal()
    result = await signal.detect(ctx, MagicMock(), "")
    score = result["graph.canonical_exhaustion_score"]
    assert 0.0 <= score <= 1.0


@pytest.mark.asyncio
async def test_returns_average_across_multiple_nodes():
    """Fresh node (0.0) + max-exhaustion node should average to a value in (0, 1)."""
    fresh = _make_node_state(focus_count=0)
    exhausted = _make_node_state(
        focus_count=10, turns_since_last_yield=10, current_focus_streak=5
    )
    ctx = _make_context(states={"fresh": fresh, "exhausted": exhausted})
    signal = CanonicalExhaustionScoreSignal()
    result = await signal.detect(ctx, MagicMock(), "")
    score = result["graph.canonical_exhaustion_score"]
    # fresh=0.0, exhausted=0.7 (max: 0.4+0.3+0.0) → average 0.35
    assert 0.0 < score < 1.0
