"""Tests for ConversationSaturationSignal — extraction yield ratio."""

from unittest.mock import MagicMock

import pytest

from src.signals.meta.conversation_saturation import ConversationSaturationSignal


def _make_context(prev_surface: int, peak: float, turn: int = 5):
    """Build mock context with ContextLoadingOutput and graph_state."""
    clo = MagicMock()
    clo.prev_surface_node_count = prev_surface
    clo.surface_velocity_peak = peak
    ctx = MagicMock()
    ctx.context_loading_output = clo
    ctx.turn_number = turn
    return ctx


def _make_graph_state(node_count: int):
    gs = MagicMock()
    gs.node_count = node_count
    return gs


@pytest.mark.asyncio
async def test_matching_peak_yields_zero():
    """When current extraction matches peak, saturation = 0.0."""
    ctx = _make_context(prev_surface=20, peak=10.0)
    gs = _make_graph_state(node_count=30)  # delta=10, peak=10 -> ratio=1.0 -> sat=0.0
    result = await ConversationSaturationSignal().detect(ctx, gs, "")
    assert result["meta.conversation.saturation"] == 0.0


@pytest.mark.asyncio
async def test_zero_extraction_yields_one():
    """When no new nodes extracted, saturation = 1.0."""
    ctx = _make_context(prev_surface=30, peak=10.0)
    gs = _make_graph_state(node_count=30)  # delta=0 -> sat=1.0
    result = await ConversationSaturationSignal().detect(ctx, gs, "")
    assert result["meta.conversation.saturation"] == 1.0


@pytest.mark.asyncio
async def test_half_peak_yields_half():
    """When extraction is half of peak, saturation = 0.5."""
    ctx = _make_context(prev_surface=25, peak=10.0)
    gs = _make_graph_state(node_count=30)  # delta=5, peak=10 -> ratio=0.5 -> sat=0.5
    result = await ConversationSaturationSignal().detect(ctx, gs, "")
    assert result["meta.conversation.saturation"] == 0.5


@pytest.mark.asyncio
async def test_exceeds_peak_clamps_to_zero():
    """When extraction exceeds peak, saturation clamps to 0.0."""
    ctx = _make_context(prev_surface=20, peak=5.0)
    gs = _make_graph_state(
        node_count=30
    )  # delta=10, peak=5 -> ratio=2.0 -> clamped -> sat=0.0
    result = await ConversationSaturationSignal().detect(ctx, gs, "")
    assert result["meta.conversation.saturation"] == 0.0


@pytest.mark.asyncio
async def test_zero_peak_yields_zero():
    """When peak is 0 (first turn), saturation = 0.0 (not saturated)."""
    ctx = _make_context(prev_surface=0, peak=0.0)
    gs = _make_graph_state(node_count=5)
    result = await ConversationSaturationSignal().detect(ctx, gs, "")
    assert result["meta.conversation.saturation"] == 0.0


@pytest.mark.asyncio
async def test_no_graph_state_returns_full_saturation():
    """When graph_state is None, node_count=0, so delta is clamped to 0 -> saturation=1.0."""
    ctx = _make_context(prev_surface=10, peak=5.0)
    result = await ConversationSaturationSignal().detect(ctx, None, "")
    assert result["meta.conversation.saturation"] == 1.0
