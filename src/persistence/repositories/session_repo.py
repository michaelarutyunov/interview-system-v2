"""Session repository for database operations."""
import json
from datetime import datetime
from typing import Optional, Dict, Any

import aiosqlite

from src.domain.models.session import Session, SessionState
from src.domain.models.utterance import Utterance


class SessionRepository:
    """Repository for session CRUD operations."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def create(self, session: Session, config: Optional[Dict[str, Any]] = None) -> Session:
        """Create a new session."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            config_json = json.dumps(config or {})
            await db.execute(
                "INSERT INTO sessions (id, methodology, concept_id, concept_name, status, "
                "config, turn_count, coverage_score, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
                (session.id, session.methodology, session.concept_id,
                 session.concept_name, session.status, config_json,
                 session.state.turn_count, session.state.coverage_score)
            )
            await db.commit()

            # Fetch the created session to get the timestamps
            cursor = await db.execute(
                "SELECT * FROM sessions WHERE id = ?", (session.id,)
            )
            row = await cursor.fetchone()
            if not row:
                raise ValueError(f"Session {session.id} not found after creation")
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

    async def get_utterances(self, session_id: str) -> list:
        """Get all utterances for a session."""

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM utterances WHERE session_id = ? ORDER BY turn_number",
                (session_id,)
            )
            rows = await cursor.fetchall()
            return [self._row_to_utterance(row) for row in rows]

    async def get_scoring_history(self, session_id: str) -> list:
        """Get scoring history for a session."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM scoring_history WHERE session_id = ? ORDER BY turn_number",
                (session_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_config(self, session_id: str) -> Dict[str, Any]:
        """Get session configuration."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT config FROM sessions WHERE id = ?",
                (session_id,)
            )
            row = await cursor.fetchone()
            if row:
                return json.loads(row["config"]) if row["config"] else {}
            return {}

    async def save_scoring_history(
        self,
        scoring_id: str,
        session_id: str,
        turn_number: int,
        coverage_score: float,
        depth_score: float,
        saturation_score: float,
        strategy_selected: str,
        strategy_reasoning: Optional[str] = None,
        scorer_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Save scoring history entry."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO scoring_history (
                    id, session_id, turn_number,
                    coverage_score, depth_score, saturation_score,
                    strategy_selected, strategy_reasoning, scorer_details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    scoring_id,
                    session_id,
                    turn_number,
                    coverage_score,
                    depth_score,
                    saturation_score,
                    strategy_selected,
                    strategy_reasoning,
                    json.dumps(scorer_details or {}),
                )
            )
            await db.commit()

    async def save_scoring_candidate(
        self,
        candidate_id: str,
        session_id: str,
        turn_number: int,
        strategy_id: str,
        strategy_name: str,
        focus_type: str,
        focus_description: str,
        final_score: float,
        is_selected: bool,
        vetoed_by: Optional[str] = None,
        tier1_results: Optional[list] = None,
        tier2_results: Optional[list] = None,
        reasoning: Optional[str] = None,
    ) -> None:
        """Save a scoring candidate to the candidates table."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO scoring_candidates (
                    id, session_id, turn_number,
                    strategy_id, strategy_name, focus_type, focus_description,
                    final_score, is_selected, vetoed_by,
                    tier1_results, tier2_results, reasoning
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    candidate_id,
                    session_id,
                    turn_number,
                    strategy_id,
                    strategy_name,
                    focus_type,
                    focus_description[:500],  # Limit length
                    final_score,
                    1 if is_selected else 0,
                    vetoed_by,
                    json.dumps(tier1_results or []),
                    json.dumps(tier2_results or []),
                    reasoning,
                )
            )
            await db.commit()

    async def get_turn_scoring(self, session_id: str, turn_number: int) -> list:
        """Get all scoring candidates for a specific turn."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT
                    id, strategy_id, strategy_name, focus_type, focus_description,
                    final_score, is_selected, vetoed_by,
                    tier1_results, tier2_results, reasoning
                   FROM scoring_candidates
                   WHERE session_id = ? AND turn_number = ?
                   ORDER BY final_score DESC""",
                (session_id, turn_number),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_all_turn_numbers_with_scoring(self, session_id: str) -> list:
        """Get all turn numbers that have scoring data."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT DISTINCT turn_number
                   FROM scoring_candidates
                   WHERE session_id = ?
                   ORDER BY turn_number DESC""",
                (session_id,),
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def get_coverage_stats(self, session_id: str) -> Dict[str, Any]:
        """Get coverage statistics from concept_elements table."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN is_covered = 1 THEN 1 ELSE 0 END) as covered
                   FROM concept_elements
                   WHERE session_id = ?""",
                (session_id,),
            )
            row = await cursor.fetchone()
            return {
                "total_elements": row[0] if row else 0,
                "covered_elements": row[1] if row else 0,
            }

    async def get_latest_strategy(self, session_id: str) -> Dict[str, Any]:
        """Get the most recent strategy from scoring_history."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT strategy_selected, strategy_reasoning
                   FROM scoring_history
                   WHERE session_id = ?
                   ORDER BY turn_number DESC
                   LIMIT 1""",
                (session_id,),
            )
            row = await cursor.fetchone()
            return {
                "strategy": row[0] if row else "unknown",
                "reasoning": row[1] if row and len(row) > 1 else None,
            }

    def _row_to_utterance(self, row: aiosqlite.Row) -> Utterance:
        """Convert a database row to an Utterance model."""
        return Utterance(
            id=row["id"],
            session_id=row["session_id"],
            turn_number=row["turn_number"],
            speaker=row["speaker"],
            text=row["text"],
            discourse_markers=json.loads(row["discourse_markers"]) if row["discourse_markers"] else [],
            created_at=datetime.fromisoformat(row["created_at"])
        )

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
