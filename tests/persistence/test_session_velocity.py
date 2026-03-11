"""
Tests for SessionState velocity field persistence (bead: saturation-fix).

TDD: tests written before implementation — all should fail initially.
Verifies that surface_velocity_peak, prev_surface_node_count,
canonical_velocity_peak, prev_canonical_node_count, and focus_history
survive an update_state / get round-trip.
"""

import pytest
from datetime import datetime, timezone

from src.domain.models.session import Session, SessionState, FocusEntry


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_session(session_id: str = "s-vel-test") -> Session:
    now = datetime.now(timezone.utc)
    return Session(
        id=session_id,
        methodology="jobs_to_be_done",
        concept_id="test-concept",
        concept_name="Test Product",
        created_at=now,
        updated_at=now,
        state=SessionState(
            methodology="jobs_to_be_done",
            concept_id="test-concept",
            concept_name="Test Product",
        ),
    )


# ── surface_velocity_peak ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_state_persists_surface_velocity_peak(session_repo):
    """surface_velocity_peak survives update_state → get round-trip."""
    session = await session_repo.create(_make_session("s-svp"))

    state = SessionState(
        methodology="jobs_to_be_done",
        concept_id="test-concept",
        concept_name="Test Product",
        turn_count=3,
        surface_velocity_peak=7.0,
        prev_surface_node_count=21,
    )
    await session_repo.update_state(session.id, state)

    loaded = await session_repo.get(session.id)
    assert loaded is not None
    assert loaded.state.surface_velocity_peak == 7.0
    assert loaded.state.prev_surface_node_count == 21


# ── canonical velocity ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_state_persists_canonical_velocity(session_repo):
    """canonical_velocity_peak and prev_canonical_node_count survive round-trip."""
    session = await session_repo.create(_make_session("s-cvp"))

    state = SessionState(
        methodology="jobs_to_be_done",
        concept_id="test-concept",
        concept_name="Test Product",
        turn_count=5,
        canonical_velocity_peak=3.0,
        prev_canonical_node_count=9,
    )
    await session_repo.update_state(session.id, state)

    loaded = await session_repo.get(session.id)
    assert loaded is not None
    assert loaded.state.canonical_velocity_peak == 3.0
    assert loaded.state.prev_canonical_node_count == 9


# ── focus_history ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_state_persists_focus_history(session_repo):
    """focus_history entries survive update_state → get round-trip."""
    session = await session_repo.create(_make_session("s-fh"))

    state = SessionState(
        methodology="jobs_to_be_done",
        concept_id="test-concept",
        concept_name="Test Product",
        turn_count=2,
        focus_history=[
            FocusEntry(turn=1, node_id="n1", label="convenience", strategy="explore_situation"),
            FocusEntry(turn=2, node_id="n2", label="saves time", strategy="dig_motivation"),
        ],
    )
    await session_repo.update_state(session.id, state)

    loaded = await session_repo.get(session.id)
    assert loaded is not None
    assert len(loaded.state.focus_history) == 2
    assert loaded.state.focus_history[0].node_id == "n1"
    assert loaded.state.focus_history[0].strategy == "explore_situation"
    assert loaded.state.focus_history[1].node_id == "n2"
    assert loaded.state.focus_history[1].strategy == "dig_motivation"


@pytest.mark.asyncio
async def test_update_state_empty_focus_history_round_trips(session_repo):
    """Empty focus_history round-trips as empty list (not None)."""
    session = await session_repo.create(_make_session("s-fh-empty"))

    state = SessionState(
        methodology="jobs_to_be_done",
        concept_id="test-concept",
        concept_name="Test Product",
        turn_count=1,
        focus_history=[],
    )
    await session_repo.update_state(session.id, state)

    loaded = await session_repo.get(session.id)
    assert loaded is not None
    assert loaded.state.focus_history == []


# ── all fields together ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_state_persists_all_velocity_fields(session_repo):
    """All four velocity fields persist and round-trip correctly together."""
    session = await session_repo.create(_make_session("s-all"))

    state = SessionState(
        methodology="jobs_to_be_done",
        concept_id="test-concept",
        concept_name="Test Product",
        turn_count=8,
        surface_velocity_peak=5.0,
        prev_surface_node_count=40,
        canonical_velocity_peak=2.0,
        prev_canonical_node_count=12,
        focus_history=[
            FocusEntry(turn=8, node_id="nX", label="quality", strategy="uncover_obstacles"),
        ],
    )
    await session_repo.update_state(session.id, state)

    loaded = await session_repo.get(session.id)
    assert loaded is not None
    s = loaded.state
    assert s.surface_velocity_peak == 5.0
    assert s.prev_surface_node_count == 40
    assert s.canonical_velocity_peak == 2.0
    assert s.prev_canonical_node_count == 12
    assert len(s.focus_history) == 1
    assert s.focus_history[0].label == "quality"
