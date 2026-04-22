"""Tests for NodeOpportunitySignal — opportunity categorization for joint scoring.

Key regression: _get_response_depth() must read from current-turn global signals
(context.current_turn_global_signals) and NOT from the stale previous-turn
context.signals (StrategySelectionOutput from the prior turn).
"""

from unittest.mock import MagicMock

import pytest

from src.signals.meta.node_opportunity import NodeOpportunitySignal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(
    *,
    focus_count: int = 0,
    turns_since_last_yield: int = 0,
    current_focus_streak: int = 0,
    all_response_depths: list | None = None,
    label: str = "test-node",
) -> MagicMock:
    state = MagicMock()
    state.focus_count = focus_count
    state.turns_since_last_yield = turns_since_last_yield
    state.current_focus_streak = current_focus_streak
    state.all_response_depths = all_response_depths or []
    state.label = label
    return state


def _make_tracker(node_states: dict) -> MagicMock:
    tracker = MagicMock()
    tracker.get_all_states.return_value = node_states
    return tracker


def _make_signal(node_states: dict) -> NodeOpportunitySignal:
    signal = NodeOpportunitySignal.__new__(NodeOpportunitySignal)
    signal.node_tracker = _make_tracker(node_states)
    return signal


def _make_context(
    *,
    current_turn_global_signals: dict | None = None,
    previous_turn_signals: dict | None = None,
) -> MagicMock:
    """Build a mock PipelineContext.

    Sets current_turn_global_signals and/or strategy_selection_output.signals
    to mimic what the pipeline provides during detection.
    """
    ctx = MagicMock()
    # current-turn: set by MethodologyStrategyService before node detection
    if current_turn_global_signals is not None:
        ctx.current_turn_global_signals = current_turn_global_signals
    else:
        # Attribute absent — simulate first turn or test without it
        del ctx.current_turn_global_signals

    # previous-turn: comes from StrategySelectionOutput of the prior turn
    if previous_turn_signals is not None:
        ctx.signals = previous_turn_signals
    else:
        ctx.signals = None

    return ctx


# ---------------------------------------------------------------------------
# _get_response_depth — current-turn vs stale fallback
# ---------------------------------------------------------------------------


def test_get_response_depth_reads_current_turn_global_signals():
    """Must return depth from current_turn_global_signals, not context.signals."""
    signal = _make_signal({})
    ctx = _make_context(
        current_turn_global_signals={"response.semantic.llm.response_depth": "deep"},
        previous_turn_signals={
            "response.semantic.llm.response_depth": "surface"
        },  # stale — must be ignored
    )

    depth = signal._get_response_depth(ctx)

    assert depth == "deep", (
        "_get_response_depth() returned the stale previous-turn value instead of "
        "the current-turn global signal"
    )


def test_get_response_depth_falls_back_to_context_signals_when_no_current_turn():
    """Falls back to context.signals when current_turn_global_signals is absent."""
    signal = _make_signal({})
    ctx = _make_context(
        current_turn_global_signals=None,  # absent
        previous_turn_signals={"response.semantic.llm.response_depth": "moderate"},
    )

    depth = signal._get_response_depth(ctx)

    assert depth == "moderate"


def test_get_response_depth_returns_none_when_both_absent():
    """Returns None when neither source is available."""
    signal = _make_signal({})
    ctx = _make_context(
        current_turn_global_signals=None,
        previous_turn_signals=None,
    )

    depth = signal._get_response_depth(ctx)

    assert depth is None


# ---------------------------------------------------------------------------
# probe_deeper classification uses current-turn depth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_probe_deeper_triggers_with_current_turn_deep():
    """probe_deeper fires when current-turn depth=deep and streak=high."""
    state = _make_state(
        focus_count=1,
        turns_since_last_yield=3,  # NOT exhausted (shallow_ratio will be 0)
        current_focus_streak=5,  # high streak (4+)
        all_response_depths=["deep", "deep", "deep"],
    )
    states = {"node-a": state}
    signal = _make_signal(states)
    ctx = _make_context(
        current_turn_global_signals={"response.semantic.llm.response_depth": "deep"},
        previous_turn_signals={
            "response.semantic.llm.response_depth": "surface"
        },  # stale — must be ignored
    )

    result = await signal.detect(ctx, MagicMock(), "")

    assert result["node-a"] == "probe_deeper", (
        "Expected probe_deeper with high streak + deep current-turn response"
    )


@pytest.mark.asyncio
async def test_probe_deeper_does_not_trigger_with_stale_surface_depth():
    """probe_deeper must NOT fire when current-turn depth is surface, even if stale
    context.signals says deep."""
    state = _make_state(
        focus_count=1,
        turns_since_last_yield=3,
        current_focus_streak=5,
        all_response_depths=["deep", "deep", "deep"],
    )
    states = {"node-a": state}
    signal = _make_signal(states)
    # current turn: surface; stale previous turn: deep
    ctx = _make_context(
        current_turn_global_signals={"response.semantic.llm.response_depth": "surface"},
        previous_turn_signals={"response.semantic.llm.response_depth": "deep"},
    )

    result = await signal.detect(ctx, MagicMock(), "")

    assert result["node-a"] == "fresh", (
        "probe_deeper should not fire when current-turn depth is surface"
    )


# ---------------------------------------------------------------------------
# exhausted classification is independent of response_depth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exhausted_classification_independent_of_depth():
    """Exhausted nodes stay exhausted regardless of response depth."""
    state = _make_state(
        focus_count=2,
        turns_since_last_yield=3,
        current_focus_streak=2,
        all_response_depths=["surface", "shallow", "surface"],  # shallow_ratio=1.0
    )
    states = {"node-a": state}
    signal = _make_signal(states)
    ctx = _make_context(
        current_turn_global_signals={"response.semantic.llm.response_depth": "deep"},
    )

    result = await signal.detect(ctx, MagicMock(), "")

    assert result["node-a"] == "exhausted"


# ---------------------------------------------------------------------------
# fresh classification (default)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fresh_when_unfocused():
    """Nodes never focused default to fresh."""
    state = _make_state(focus_count=0)
    states = {"node-a": state}
    signal = _make_signal(states)
    ctx = _make_context(current_turn_global_signals={})

    result = await signal.detect(ctx, MagicMock(), "")

    assert result["node-a"] == "fresh"


@pytest.mark.asyncio
async def test_empty_tracker_returns_empty_dict():
    """When no nodes are tracked, result is empty."""
    signal = _make_signal({})
    ctx = _make_context(current_turn_global_signals={})

    result = await signal.detect(ctx, MagicMock(), "")

    assert result == {}
