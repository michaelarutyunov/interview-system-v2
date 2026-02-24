"""Tests for get_slot_saturation_map in CanonicalSlotRepository."""

import pytest
import aiosqlite

from src.persistence.repositories.canonical_slot_repo import CanonicalSlotRepository


@pytest.fixture
async def db_with_slots(tmp_path):
    """Create a temp DB with canonical slots and mappings."""
    db_path = str(tmp_path / "test.db")

    async with aiosqlite.connect(db_path) as db:
        # Create tables
        await db.execute("""
            CREATE TABLE canonical_slots (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                slot_name TEXT,
                node_type TEXT,
                status TEXT DEFAULT 'candidate',
                support_count INTEGER DEFAULT 0,
                first_seen_turn INTEGER,
                promoted_turn INTEGER,
                description TEXT DEFAULT '',
                embedding BLOB
            )
        """)
        await db.execute("""
            CREATE TABLE surface_to_slot_mapping (
                surface_node_id TEXT,
                canonical_slot_id TEXT,
                similarity_score REAL,
                assigned_turn INTEGER
            )
        """)

        # Insert slots: "flavor" (support=3), "cost" (support=1)
        await db.execute(
            "INSERT INTO canonical_slots (id, session_id, slot_name, node_type, status, support_count, first_seen_turn) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("slot-1", "sess-1", "flavor_complexity", "attribute", "candidate", 3, 1),
        )
        await db.execute(
            "INSERT INTO canonical_slots (id, session_id, slot_name, node_type, status, support_count, first_seen_turn) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("slot-2", "sess-1", "cost_concerns", "consequence", "candidate", 1, 2),
        )

        # Map nodes to slots
        await db.execute(
            "INSERT INTO surface_to_slot_mapping VALUES (?, ?, ?, ?)",
            ("node-a", "slot-1", 0.9, 1),
        )
        await db.execute(
            "INSERT INTO surface_to_slot_mapping VALUES (?, ?, ?, ?)",
            ("node-b", "slot-1", 0.85, 1),
        )
        await db.execute(
            "INSERT INTO surface_to_slot_mapping VALUES (?, ?, ?, ?)",
            ("node-c", "slot-1", 0.8, 2),
        )
        await db.execute(
            "INSERT INTO surface_to_slot_mapping VALUES (?, ?, ?, ?)",
            ("node-d", "slot-2", 0.9, 2),
        )
        await db.commit()

    return db_path


@pytest.mark.asyncio
async def test_get_slot_saturation_map(db_with_slots):
    """Returns surface_node_id -> support_count for all mapped nodes."""
    repo = CanonicalSlotRepository(db_path=db_with_slots)
    result = await repo.get_slot_saturation_map(session_id="sess-1")

    assert result == {
        "node-a": 3,  # maps to slot-1 (support=3)
        "node-b": 3,  # maps to slot-1 (support=3)
        "node-c": 3,  # maps to slot-1 (support=3)
        "node-d": 1,  # maps to slot-2 (support=1)
    }


@pytest.mark.asyncio
async def test_get_slot_saturation_map_empty_session(db_with_slots):
    """Returns empty dict for session with no mappings."""
    repo = CanonicalSlotRepository(db_path=db_with_slots)
    result = await repo.get_slot_saturation_map(session_id="nonexistent")
    assert result == {}
