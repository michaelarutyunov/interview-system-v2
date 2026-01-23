"""
Stage 1: Load session context.

ADR-008 Phase 3: Load session metadata, graph state, and recent utterances.
"""
from typing import TYPE_CHECKING

import aiosqlite
import json
import structlog

from ..base import TurnStage

log = structlog.get_logger(__name__)

if TYPE_CHECKING:
    from ..context import PipelineContext


class ContextLoadingStage(TurnStage):
    """
    Load session context at the start of turn processing.

    Populates PipelineContext with:
    - Session metadata (methodology, concept, turn number, mode)
    - Graph state (node count, edge count, depth)
    - Recent nodes
    - Recent utterances
    """

    def __init__(
        self,
        session_repo,
        graph_service,
    ):
        """
        Initialize stage.

        Args:
            session_repo: SessionRepository instance
            graph_service: GraphService instance
        """
        self.session_repo = session_repo
        self.graph = graph_service

    async def process(self, context: "PipelineContext") -> "PipelineContext":
        """
        Load session context into the context object.

        Args:
            context: Turn context with session_id

        Returns:
            Modified context with session data loaded
        """
        session = await self.session_repo.get(context.session_id)
        if not session:
            raise ValueError(f"Session {context.session_id} not found")

        # Get session config to read max_turns
        max_turns = 20  # Default
        async with aiosqlite.connect(str(self.session_repo.db_path)) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT config FROM sessions WHERE id = ?",
                (context.session_id,)
            )
            row = await cursor.fetchone()
            if row:
                config = json.loads(row["config"]) if row["config"] else {}
                max_turns = config.get("max_turns", 20)

        # Get recent utterances
        recent_utterances = await self._get_recent_utterances(context.session_id, limit=10)

        # Get graph state
        graph_state = await self.graph.get_graph_state(context.session_id)

        # Get recent nodes
        recent_nodes = await self.graph.get_recent_nodes(context.session_id, limit=5)

        # Update context
        context.methodology = session.methodology
        context.concept_id = session.concept_id
        context.concept_name = session.concept_name
        context.turn_number = session.state.turn_count or 1
        context.mode = session.mode.value
        context.max_turns = max_turns
        context.recent_utterances = recent_utterances
        context.graph_state = graph_state
        context.recent_nodes = recent_nodes

        log.info(
            "context_loaded",
            session_id=context.session_id,
            turn_number=context.turn_number,
            mode=context.mode,
            graph_nodes=graph_state.node_count if graph_state else 0,
        )

        return context

    async def _get_recent_utterances(
        self, session_id: str, limit: int = 10
    ) -> list:
        """
        Get recent utterances for context.

        Args:
            session_id: Session ID
            limit: Max utterances to return

        Returns:
            List of {"speaker": str, "text": str} dicts
        """
        from src.persistence.database import get_db_connection

        db = await get_db_connection()
        try:
            cursor = await db.execute(
                """
                SELECT speaker, text FROM utterances
                WHERE session_id = ?
                ORDER BY turn_number DESC, created_at DESC
                LIMIT ?
                """,
                (session_id, limit),
            )
            rows = await cursor.fetchall()
        finally:
            await db.close()

        # Reverse to get chronological order
        return list(reversed([{"speaker": row[0], "text": row[1]} for row in rows]))
