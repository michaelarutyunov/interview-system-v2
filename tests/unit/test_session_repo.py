"""Tests for session repository."""

import pytest
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from src.persistence.database import init_database
from src.persistence.repositories.session_repo import SessionRepository
from src.domain.models.session import Session, SessionState
from typing import Optional


@pytest.fixture
async def db_path():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        await init_database(db_path)
        yield str(db_path)


@pytest.fixture
def repo(db_path):
    """Create a session repository instance."""
    return SessionRepository(db_path)


def create_test_session(
    session_id: Optional[str] = None,
    methodology: str = "mec",
    concept_id: str = "concept-1",
    concept_name: str = "Test Concept",
    status: str = "active",
    turn_count: int = 0,
    coverage_score: float = 0.0
) -> Session:
    """Helper to create test sessions."""
    if session_id is None:
        session_id = str(uuid.uuid4())

    now = datetime.now()
    return Session(
        id=session_id,
        methodology=methodology,
        concept_id=concept_id,
        concept_name=concept_name,
        created_at=now,
        updated_at=now,
        status=status,
        state=SessionState(
            methodology=methodology,
            concept_id=concept_id,
            concept_name=concept_name,
            turn_count=turn_count,
            coverage_score=coverage_score,
            last_strategy=None
        )
    )


@pytest.mark.asyncio
async def test_create_session(db_path):
    """Test creating a new session."""
    repo = SessionRepository(db_path)
    session = create_test_session(session_id="test-session-1")

    created = await repo.create(session)

    assert created.id == "test-session-1"
    assert created.methodology == "mec"
    assert created.concept_id == "concept-1"
    assert created.concept_name == "Test Concept"
    assert created.status == "active"
    assert created.state.turn_count == 0
    assert created.state.coverage_score == 0.0


@pytest.mark.asyncio
async def test_get_session(db_path):
    """Test retrieving a session by ID."""
    repo = SessionRepository(db_path)
    session = create_test_session(session_id="test-session-2")
    await repo.create(session)

    retrieved = await repo.get("test-session-2")

    assert retrieved is not None
    assert retrieved.id == "test-session-2"
    assert retrieved.methodology == "mec"
    assert retrieved.concept_name == "Test Concept"


@pytest.mark.asyncio
async def test_get_nonexistent_session(db_path):
    """Test retrieving a session that doesn't exist."""
    repo = SessionRepository(db_path)

    result = await repo.get("nonexistent-id")

    assert result is None


@pytest.mark.asyncio
async def test_update_state(db_path):
    """Test updating session state."""
    repo = SessionRepository(db_path)
    session = create_test_session(session_id="test-session-3")
    await repo.create(session)

    # Update the state
    new_state = SessionState(
        methodology="mec",
        concept_id="concept-1",
        concept_name="Test Concept",
        turn_count=5,
        coverage_score=0.75,
        last_strategy="ladder_up"
    )
    await repo.update_state("test-session-3", new_state)

    # Verify update
    updated = await repo.get("test-session-3")
    assert updated is not None
    assert updated.state.turn_count == 5
    assert updated.state.coverage_score == 0.75


@pytest.mark.asyncio
async def test_list_active(db_path):
    """Test listing active sessions."""
    repo = SessionRepository(db_path)

    # Create multiple sessions with different statuses
    session1 = create_test_session(session_id="active-1", status="active")
    session2 = create_test_session(session_id="active-2", status="active")
    session3 = create_test_session(session_id="completed-1", status="completed")

    await repo.create(session1)
    await repo.create(session2)
    await repo.create(session3)

    active = await repo.list_active()

    assert len(active) == 2
    active_ids = [s.id for s in active]
    assert "active-1" in active_ids
    assert "active-2" in active_ids
    assert "completed-1" not in active_ids


@pytest.mark.asyncio
async def test_delete_session(db_path):
    """Test deleting a session."""
    repo = SessionRepository(db_path)
    session = create_test_session(session_id="to-delete")
    await repo.create(session)

    # Verify it exists
    assert await repo.get("to-delete") is not None

    # Delete it
    deleted = await repo.delete("to-delete")

    assert deleted is True
    assert await repo.get("to-delete") is None


@pytest.mark.asyncio
async def test_delete_nonexistent_session(db_path):
    """Test deleting a session that doesn't exist."""
    repo = SessionRepository(db_path)

    deleted = await repo.delete("nonexistent")

    assert deleted is False


@pytest.mark.asyncio
async def test_session_timestamps(db_path):
    """Test that timestamps are properly set."""
    repo = SessionRepository(db_path)
    session = create_test_session(session_id="timestamp-test")

    created = await repo.create(session)

    assert created.created_at is not None
    assert created.updated_at is not None
    assert isinstance(created.created_at, datetime)
    assert isinstance(created.updated_at, datetime)


@pytest.mark.asyncio
async def test_update_state_updates_timestamp(db_path):
    """Test that update_state updates the updated_at timestamp."""
    repo = SessionRepository(db_path)
    session = create_test_session(session_id="update-timestamp-test")
    created = await repo.create(session)
    original_updated_at = created.updated_at

    # Small delay to ensure timestamp difference
    import asyncio
    await asyncio.sleep(0.1)

    # Update state
    new_state = SessionState(
        methodology="mec",
        concept_id="concept-1",
        concept_name="Test Concept",
        turn_count=1,
        coverage_score=0.1
    )
    await repo.update_state("update-timestamp-test", new_state)

    updated = await repo.get("update-timestamp-test")
    assert updated is not None
    assert updated.updated_at >= original_updated_at
