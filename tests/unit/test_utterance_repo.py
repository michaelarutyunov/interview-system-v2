"""Tests for utterance repository."""

import pytest
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from src.persistence.database import init_database
from src.persistence.repositories.utterance_repo import UtteranceRepository
from src.domain.models.utterance import Utterance
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
    """Create an utterance repository instance."""
    return UtteranceRepository(db_path)


def create_test_utterance(
    utterance_id: Optional[str] = None,
    session_id: str = "test-session-1",
    turn_number: int = 1,
    speaker: str = "user",
    text: str = "Test utterance",
) -> Utterance:
    """Helper to create test utterances."""
    if utterance_id is None:
        utterance_id = str(uuid.uuid4())

    return Utterance(
        id=utterance_id,
        session_id=session_id,
        turn_number=turn_number,
        speaker=speaker,
        text=text,
        discourse_markers=[],
        created_at=datetime.utcnow(),
    )


@pytest.mark.asyncio
async def test_save_utterance(db_path):
    """Test saving a new utterance."""
    repo = UtteranceRepository(db_path)
    utterance = create_test_utterance(
        utterance_id="test-utterance-1",
        session_id="session-1",
        turn_number=1,
        speaker="user",
        text="Hello world",
    )

    saved = await repo.save(utterance)

    assert saved.id == "test-utterance-1"
    assert saved.session_id == "session-1"
    assert saved.turn_number == 1
    assert saved.speaker == "user"
    assert saved.text == "Hello world"


@pytest.mark.asyncio
async def test_save_system_utterance(db_path):
    """Test saving a system utterance."""
    repo = UtteranceRepository(db_path)
    utterance = create_test_utterance(
        utterance_id="system-utterance-1",
        session_id="session-1",
        turn_number=1,
        speaker="system",
        text="How can I help you?",
    )

    saved = await repo.save(utterance)

    assert saved.id == "system-utterance-1"
    assert saved.speaker == "system"
    assert saved.text == "How can I help you?"


@pytest.mark.asyncio
async def test_get_recent_utterances(db_path):
    """Test retrieving recent utterances for a session."""
    repo = UtteranceRepository(db_path)
    session_id = "session-1"

    # Create multiple utterances
    utterance1 = create_test_utterance(
        utterance_id="utt-1",
        session_id=session_id,
        turn_number=1,
        speaker="system",
        text="Opening question",
    )
    utterance2 = create_test_utterance(
        utterance_id="utt-2",
        session_id=session_id,
        turn_number=1,
        speaker="user",
        text="User response",
    )
    utterance3 = create_test_utterance(
        utterance_id="utt-3",
        session_id=session_id,
        turn_number=2,
        speaker="system",
        text="Follow-up question",
    )

    await repo.save(utterance1)
    await repo.save(utterance2)
    await repo.save(utterance3)

    # Get recent utterances (default limit 10)
    recent = await repo.get_recent(session_id)

    assert len(recent) == 3
    assert recent[0].id == "utt-1"
    assert recent[1].id == "utt-2"
    assert recent[2].id == "utt-3"


@pytest.mark.asyncio
async def test_get_recent_with_limit(db_path):
    """Test retrieving recent utterances with a limit."""
    repo = UtteranceRepository(db_path)
    session_id = "session-1"

    # Create 5 utterances
    for i in range(5):
        utterance = create_test_utterance(
            utterance_id=f"utt-{i}",
            session_id=session_id,
            turn_number=i,
            speaker="user",
            text=f"Utterance {i}",
        )
        await repo.save(utterance)

    # Get only 3 recent
    recent = await repo.get_recent(session_id, limit=3)

    assert len(recent) == 3
    assert recent[0].id == "utt-0"
    assert recent[1].id == "utt-1"
    assert recent[2].id == "utt-2"


@pytest.mark.asyncio
async def test_get_recent_empty_session(db_path):
    """Test retrieving utterances from a session with no utterances."""
    repo = UtteranceRepository(db_path)

    recent = await repo.get_recent("nonexistent-session")

    assert len(recent) == 0


@pytest.mark.asyncio
async def test_get_by_turn(db_path):
    """Test retrieving all utterances for a specific turn."""
    repo = UtteranceRepository(db_path)
    session_id = "session-1"

    # Create utterances for different turns
    system_turn1 = create_test_utterance(
        utterance_id="utt-1",
        session_id=session_id,
        turn_number=1,
        speaker="system",
        text="Question 1",
    )
    user_turn1 = create_test_utterance(
        utterance_id="utt-2",
        session_id=session_id,
        turn_number=1,
        speaker="user",
        text="Answer 1",
    )
    system_turn2 = create_test_utterance(
        utterance_id="utt-3",
        session_id=session_id,
        turn_number=2,
        speaker="system",
        text="Question 2",
    )

    await repo.save(system_turn1)
    await repo.save(user_turn1)
    await repo.save(system_turn2)

    # Get utterances for turn 1
    turn1_utterances = await repo.get_by_turn(session_id, 1)

    assert len(turn1_utterances) == 2
    speakers = [u.speaker for u in turn1_utterances]
    assert "system" in speakers
    assert "user" in speakers


@pytest.mark.asyncio
async def test_get_by_turn_empty(db_path):
    """Test retrieving utterances for a turn that doesn't exist."""
    repo = UtteranceRepository(db_path)

    turn_utterances = await repo.get_by_turn("session-1", 99)

    assert len(turn_utterances) == 0


@pytest.mark.asyncio
async def test_get_recent_only_for_session(db_path):
    """Test that get_recent only returns utterances for the specified session."""
    repo = UtteranceRepository(db_path)

    # Create utterances for different sessions
    utterance1 = create_test_utterance(
        utterance_id="utt-1",
        session_id="session-1",
        turn_number=1,
        speaker="user",
        text="Session 1",
    )
    utterance2 = create_test_utterance(
        utterance_id="utt-2",
        session_id="session-2",
        turn_number=1,
        speaker="user",
        text="Session 2",
    )

    await repo.save(utterance1)
    await repo.save(utterance2)

    # Get recent for session-1 only
    recent = await repo.get_recent("session-1")

    assert len(recent) == 1
    assert recent[0].session_id == "session-1"
    assert recent[0].text == "Session 1"
