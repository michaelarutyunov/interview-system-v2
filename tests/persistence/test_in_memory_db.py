"""
Tests for in-memory SQLite shared connection mode.

Verifies that DATABASE_PATH=:memory: produces a single shared connection
so that all requests see the same data.
"""

import pytest
from pathlib import Path
from unittest.mock import patch

import src.persistence.database as db_module
from src.persistence.database import (
    init_database,
    get_db_connection,
    close_shared_connection,
)


@pytest.fixture(autouse=True)
async def reset_shared_connection():
    """Ensure the shared connection is cleaned up after each test."""
    # Reset before test in case a previous test left state
    await close_shared_connection()
    yield
    await close_shared_connection()


@pytest.mark.asyncio
async def test_in_memory_shared_connection_visibility():
    """
    Rows inserted via one get_db_connection() call must be visible
    through a subsequent get_db_connection() call when using :memory:.
    """
    memory_path = Path(":memory:")

    with patch.object(db_module.settings, "database_path", memory_path):
        # 1. Initialise (creates shared connection + applies schema)
        await init_database(db_path=memory_path)

        # 2. First connection — insert a session row
        conn1 = await get_db_connection()
        await conn1.execute(
            """
            INSERT INTO sessions (
                id, methodology, concept_id, concept_name, status, config, created_at, updated_at
            ) VALUES (
                'test-session-001',
                'jtbd',
                'coffee',
                'Coffee',
                'active',
                '{}',
                datetime('now'),
                datetime('now')
            )
            """
        )
        await conn1.commit()

        # 3. Second connection — must see the inserted row (same shared connection)
        conn2 = await get_db_connection()
        cursor = await conn2.execute(
            "SELECT id FROM sessions WHERE id = 'test-session-001'"
        )
        row = await cursor.fetchone()

        assert row is not None, (
            "Row inserted via conn1 was not visible via conn2 — "
            "connections are NOT sharing the same in-memory database."
        )
        assert row[0] == "test-session-001"

        # 4. Verify conn1 and conn2 are the same object (shared connection)
        assert conn1 is conn2, "get_db_connection() should return the same object in :memory: mode"


@pytest.mark.asyncio
async def test_shared_connection_not_closed_between_calls():
    """
    The shared connection must remain open after get_db_connection() is called.
    Callers must not close it.
    """
    memory_path = Path(":memory:")

    with patch.object(db_module.settings, "database_path", memory_path):
        await init_database(db_path=memory_path)

        conn = await get_db_connection()
        assert conn is not None

        # The shared connection should still be accessible
        assert db_module._shared_connection is not None


@pytest.mark.asyncio
async def test_close_shared_connection_cleanup():
    """close_shared_connection() must set _shared_connection back to None."""
    memory_path = Path(":memory:")

    with patch.object(db_module.settings, "database_path", memory_path):
        await init_database(db_path=memory_path)
        assert db_module._shared_connection is not None

        await close_shared_connection()
        assert db_module._shared_connection is None


@pytest.mark.asyncio
async def test_close_shared_connection_is_noop_in_file_mode():
    """close_shared_connection() must be safe to call in file-based mode (no-op)."""
    # _shared_connection is None (reset by fixture), calling close should not raise
    await close_shared_connection()
    assert db_module._shared_connection is None
