"""Utterance repository for database operations."""

from datetime import datetime
from typing import List

import aiosqlite

from src.domain.models.utterance import Utterance


class UtteranceRepository:
    """Repository for utterance CRUD operations."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def save(self, utterance: Utterance) -> Utterance:
        """Save utterance to database.

        Args:
            utterance: Utterance model to save

        Returns:
            Saved Utterance with database timestamps
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            await db.execute(
                """INSERT INTO utterances (
                    id, session_id, turn_number, speaker, text, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    utterance.id,
                    utterance.session_id,
                    utterance.turn_number,
                    utterance.speaker,
                    utterance.text,
                    utterance.created_at.isoformat(),
                ),
            )
            await db.commit()

            # Fetch the saved utterance to get the exact database state
            cursor = await db.execute(
                "SELECT * FROM utterances WHERE id = ?", (utterance.id,)
            )
            row = await cursor.fetchone()
            if not row:
                raise ValueError(f"Utterance {utterance.id} not found after save")
            return self._row_to_utterance(row)

    async def get_recent(self, session_id: str, limit: int = 10) -> List[Utterance]:
        """Get recent utterances for session.

        Args:
            session_id: Session ID to get utterances for
            limit: Maximum number of utterances to return (default 10)

        Returns:
            List of Utterance objects ordered by turn_number and created_at
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM utterances
                   WHERE session_id = ?
                   ORDER BY turn_number ASC, created_at ASC
                   LIMIT ?""",
                (session_id, limit),
            )
            rows = await cursor.fetchall()
            return [self._row_to_utterance(row) for row in rows]

    async def get_by_turn(self, session_id: str, turn_number: int) -> List[Utterance]:
        """Get all utterances (user + system) for a specific turn.

        Args:
            session_id: Session ID
            turn_number: Turn number to get utterances for

        Returns:
            List of Utterance objects for the specified turn
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM utterances
                   WHERE session_id = ? AND turn_number = ?
                   ORDER BY created_at ASC""",
                (session_id, turn_number),
            )
            rows = await cursor.fetchall()
            return [self._row_to_utterance(row) for row in rows]

    async def get_by_ids(self, ids: List[str]) -> List[Utterance]:
        """Get utterances by their IDs.

        Returns utterances in input order, deduplicated by ID.
        Missing IDs are dropped silently (no error if an ID doesn't exist).

        Args:
            ids: List of utterance IDs to retrieve

        Returns:
            List of Utterance objects in the order of first occurrence in ids
        """
        if not ids:
            return []

        # Deduplicate while preserving order
        ordered_ids = list(dict.fromkeys(ids))

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Build parameterized query with the right number of placeholders
            placeholders = ",".join("?" for _ in ordered_ids)
            cursor = await db.execute(
                f"SELECT * FROM utterances WHERE id IN ({placeholders})",
                ordered_ids,
            )
            rows = await cursor.fetchall()

        # Map id -> Utterance for O(1) lookup
        utterance_map = {row["id"]: self._row_to_utterance(row) for row in rows}

        # Return in input order, dropping missing IDs
        return [utterance_map[uid] for uid in ordered_ids if uid in utterance_map]

    def _row_to_utterance(self, row: aiosqlite.Row) -> Utterance:
        """Convert a database row to an Utterance model.

        Args:
            row: aiosqlite Row object

        Returns:
            Utterance model instance
        """
        return Utterance(
            id=row["id"],
            session_id=row["session_id"],
            turn_number=row["turn_number"],
            speaker=row["speaker"],
            text=row["text"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
