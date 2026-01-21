"""Session repository for database operations."""
import json
from datetime import datetime
from typing import Optional

import aiosqlite

from src.domain.models.session import Session, SessionState


class SessionRepository:
    """Repository for session CRUD operations."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def create(self, session: Session) -> Session:
        """Create a new session."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute(
                "INSERT INTO sessions (id, methodology, concept_id, concept_name, status, "
                "turn_count, coverage_score, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
                (session.id, session.methodology, session.concept_id,
                 session.concept_name, session.status,
                 session.state.turn_count, session.state.coverage_score)
            )
            await db.commit()

            # Fetch the created session to get the timestamps
            cursor = await db.execute(
                "SELECT * FROM sessions WHERE id = ?", (session.id,)
            )
            row = await cursor.fetchone()
            return self._row_to_session(row)

    async def get(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return self._row_to_session(row)

    async def update_state(self, session_id: str, state: SessionState) -> None:
        """Update session state (computed on-demand, no caching)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE sessions SET "
                "turn_count = ?, coverage_score = ?, updated_at = datetime('now') "
                "WHERE id = ?",
                (state.turn_count, state.coverage_score, session_id)
            )
            await db.commit()

    async def list_active(self) -> list[Session]:
        """List all active sessions."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM sessions WHERE status = 'active' ORDER BY created_at DESC"
            )
            rows = await cursor.fetchall()
            return [self._row_to_session(row) for row in rows]

    async def delete(self, session_id: str) -> bool:
        """Delete a session by ID. Returns True if deleted."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM sessions WHERE id = ?", (session_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    def _row_to_session(self, row: aiosqlite.Row) -> Session:
        """Convert a database row to a Session model."""
        # Parse datetime strings from SQLite
        created_at = datetime.fromisoformat(row["created_at"])
        updated_at = datetime.fromisoformat(row["updated_at"])

        return Session(
            id=row["id"],
            methodology=row["methodology"],
            concept_id=row["concept_id"],
            concept_name=row["concept_name"],
            created_at=created_at,
            updated_at=updated_at,
            status=row["status"],
            state=SessionState(
                methodology=row["methodology"],
                concept_id=row["concept_id"],
                concept_name=row["concept_name"],
                turn_count=row["turn_count"],
                coverage_score=row["coverage_score"] or 0.0,
                last_strategy=None  # Not stored in DB, computed on-demand
            )
        )
