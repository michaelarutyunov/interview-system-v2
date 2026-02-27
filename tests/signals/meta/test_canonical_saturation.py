"""Tests for CanonicalSaturationSignal — canonical novelty ratio."""

from unittest.mock import MagicMock

import pytest

from src.signals.meta.canonical_saturation import CanonicalSaturationSignal


def _make_context(prev_surface: int, prev_canonical: int):
    clo = MagicMock()
    clo.prev_surface_node_count = prev_surface
    clo.prev_canonical_node_count = prev_canonical
    ctx = MagicMock()
    ctx.context_loading_output = clo
    return ctx


def _make_graph_state(node_count: int):
    gs = MagicMock()
    gs.node_count = node_count
    return gs


def _make_canonical_state(concept_count: int):
    cgs = MagicMock()
    cgs.concept_count = concept_count
    return cgs


@pytest.mark.asyncio
async def test_pure_dedup_yields_one():
    """When 8 new surface nodes map to 0 new canonical -> saturation = 1.0."""
    ctx = _make_context(prev_surface=22, prev_canonical=2)
    ctx.graph_state = _make_graph_state(node_count=30)
    ctx.canonical_graph_state = _make_canonical_state(concept_count=2)
    result = await CanonicalSaturationSignal().detect(ctx, ctx.graph_state, "")
    assert result["meta.canonical.saturation"] == 1.0


@pytest.mark.asyncio
async def test_all_novel_yields_zero():
    """When every new surface node creates a new canonical slot -> saturation = 0.0."""
    ctx = _make_context(prev_surface=10, prev_canonical=5)
    ctx.graph_state = _make_graph_state(node_count=15)
    ctx.canonical_graph_state = _make_canonical_state(concept_count=10)
    result = await CanonicalSaturationSignal().detect(ctx, ctx.graph_state, "")
    assert result["meta.canonical.saturation"] == 0.0


@pytest.mark.asyncio
async def test_partial_novelty():
    """2 new canonical from 8 new surface -> novelty=0.25, saturation=0.75."""
    ctx = _make_context(prev_surface=22, prev_canonical=4)
    ctx.graph_state = _make_graph_state(node_count=30)
    ctx.canonical_graph_state = _make_canonical_state(concept_count=6)
    result = await CanonicalSaturationSignal().detect(ctx, ctx.graph_state, "")
    assert result["meta.canonical.saturation"] == 0.75


@pytest.mark.asyncio
async def test_no_surface_extraction_yields_zero():
    """When no surface nodes extracted, saturation = 0.0 (nothing to judge)."""
    ctx = _make_context(prev_surface=30, prev_canonical=10)
    ctx.graph_state = _make_graph_state(node_count=30)
    ctx.canonical_graph_state = _make_canonical_state(concept_count=10)
    result = await CanonicalSaturationSignal().detect(ctx, ctx.graph_state, "")
    assert result["meta.canonical.saturation"] == 0.0


@pytest.mark.asyncio
async def test_canonical_disabled_returns_empty():
    """When canonical graph is None (feature disabled), return empty dict."""
    ctx = _make_context(prev_surface=10, prev_canonical=0)
    ctx.graph_state = _make_graph_state(node_count=15)
    ctx.canonical_graph_state = None
    result = await CanonicalSaturationSignal().detect(ctx, ctx.graph_state, "")
    assert result == {}


@pytest.mark.asyncio
async def test_canonical_exceeds_surface_clamps():
    """Edge case: more canonical than surface (shouldn't happen, but clamp)."""
    ctx = _make_context(prev_surface=10, prev_canonical=5)
    ctx.graph_state = _make_graph_state(node_count=12)
    ctx.canonical_graph_state = _make_canonical_state(concept_count=10)
    result = await CanonicalSaturationSignal().detect(ctx, ctx.graph_state, "")
    assert result["meta.canonical.saturation"] == 0.0
