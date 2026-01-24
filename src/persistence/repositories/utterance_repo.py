"""Utterance repository for database operations."""

import json
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

            # Convert discourse_markers to JSON
            discourse_markers_json = json.dumps(utterance.discourse_markers or [])

            await db.execute(
                """INSERT INTO utterances (
                    id, session_id, turn_number, speaker, text,
                    discourse_markers, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    utterance.id,
                    utterance.session_id,
                    utterance.turn_number,
                    utterance.speaker,
                    utterance.text,
                    discourse_markers_json,
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
            discourse_markers=json.loads(row["discourse_markers"])
            if row["discourse_markers"]
            else [],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
