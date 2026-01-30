"""Tests for database module."""

import pytest
import tempfile
from pathlib import Path

from src.persistence.database import (
    init_database,
    get_db_connection,
    check_database_health,
)


@pytest.mark.asyncio
async def test_init_database_creates_file():
    """Database initialization creates the database file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        assert not db_path.exists()

        await init_database(db_path)

        assert db_path.exists()


@pytest.mark.asyncio
async def test_init_database_creates_tables():
    """Database initialization creates all required tables."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        await init_database(db_path)

        import aiosqlite

        async with aiosqlite.connect(db_path) as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [row[0] for row in await cursor.fetchall()]

        # Core tables
        assert "sessions" in tables
        assert "utterances" in tables
        assert "kg_nodes" in tables
        assert "kg_edges" in tables
        # Scoring tables
        assert "scoring_history" in tables
        assert "scoring_candidates" in tables


@pytest.mark.asyncio
async def test_get_db_connection():
    """get_db_connection returns a usable connection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        await init_database(db_path)

        # Temporarily override settings
        from src.core import config

        original_path = config.settings.database_path
        config.settings.database_path = db_path

        try:
            db = await get_db_connection()
            try:
                cursor = await db.execute("SELECT 1")
                row = await cursor.fetchone()
                assert row is not None
                assert row[0] == 1
            finally:
                await db.close()
        finally:
            config.settings.database_path = original_path


@pytest.mark.asyncio
async def test_check_database_health():
    """Health check returns status information."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        await init_database(db_path)

        from src.core import config

        original_path = config.settings.database_path
        config.settings.database_path = db_path

        try:
            health = await check_database_health()

            assert health["status"] == "healthy"
            assert health["integrity"] == "ok"
            assert health["session_count"] == 0
        finally:
            config.settings.database_path = original_path


@pytest.mark.asyncio
async def test_foreign_keys_enforced():
    """Foreign key constraints are enforced."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        await init_database(db_path)

        import aiosqlite

        async with aiosqlite.connect(db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")

            # Try to insert utterance with non-existent session
            with pytest.raises(aiosqlite.IntegrityError):
                await db.execute(
                    "INSERT INTO utterances (id, session_id, turn_number, speaker, text) "
                    "VALUES ('u1', 'nonexistent', 1, 'user', 'test')"
                )
