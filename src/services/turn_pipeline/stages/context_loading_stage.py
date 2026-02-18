"""
Stage 1: Load session context.

Loads session metadata and conversation history. Outputs
ContextLoadingOutput contract.

Note: Graph state is NOT loaded here - it comes from StateComputationStage (Stage 5).
"""

from typing import TYPE_CHECKING

import aiosqlite
import json
import structlog

from ..base import TurnStage
from src.domain.models.pipeline_contracts import ContextLoadingOutput
from src.persistence.repositories.session_repo import SessionRepository
from src.services.graph_service import GraphService

log = structlog.get_logger(__name__)

if TYPE_CHECKING:
    from ..context import PipelineContext


class ContextLoadingStage(TurnStage):
    """
    Load session context at the start of turn processing.

    Populates PipelineContext with:
    - Session metadata (methodology, concept, turn number, mode)
    - Recent utterances
    - Strategy history

    Note: Graph state and recent nodes are populated by StateComputationStage (Stage 5).
    """

    def __init__(
        self,
        session_repo: SessionRepository,
        graph_service: GraphService,
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
        # Default is calculated from phase configuration
        from src.core.config import interview_config

        default_max_turns = (
            (interview_config.phases.exploratory.n_turns or 4)
            + (interview_config.phases.focused.n_turns or 6)
            + (interview_config.phases.closing.n_turns or 1)
        )
        max_turns = default_max_turns
        async with aiosqlite.connect(str(self.session_repo.db_path)) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT config FROM sessions WHERE id = ?", (context.session_id,)
            )
            row = await cursor.fetchone()
            if row:
                config = json.loads(row["config"]) if row["config"] else {}
                max_turns = config.get("max_turns", default_max_turns)

        # Get recent utterances
        recent_utterances = await self._get_recent_utterances(
            context.session_id, limit=10
        )

        # Note: Sentiment loading from turn_sentiments has been removed
        # It previously accessed context.graph_state which is not available
        # until Stage 5. This should be handled elsewhere if needed.

        # Get recent strategy history for StrategyDiversityScorer
        # This is persisted in scoring_history and loaded here for turn continuity
        strategy_history = await self.session_repo.get_recent_strategies(
            context.session_id, limit=5
        )

        # Load existing node labels for cross-turn relationship bridging
        recent_node_labels = []
        try:
            all_nodes = await self.graph.repo.get_nodes_by_session(context.session_id)
            recent_node_labels = [node.label for node in all_nodes]
        except Exception as e:
            log.warning("node_labels_load_failed", error=str(e))

        # Create contract output (single source of truth)
        # Note: graph_state and recent_nodes are NOT included here - they come
        # from StateComputationStage (Stage 5) after graph updates
        context.context_loading_output = ContextLoadingOutput(
            methodology=session.methodology,
            concept_id=session.concept_id,
            concept_name=session.concept_name,
            # turn_count is completed turns, so current turn is turn_count + 1
            turn_number=(session.state.turn_count or 0) + 1,
            mode=session.mode.value,
            max_turns=max_turns,
            recent_utterances=recent_utterances,
            strategy_history=strategy_history,
            recent_node_labels=recent_node_labels,
            # Velocity state from SessionState
            surface_velocity_ewma=session.state.surface_velocity_ewma,
            surface_velocity_peak=session.state.surface_velocity_peak,
            prev_surface_node_count=session.state.prev_surface_node_count,
            canonical_velocity_ewma=session.state.canonical_velocity_ewma,
            canonical_velocity_peak=session.state.canonical_velocity_peak,
            prev_canonical_node_count=session.state.prev_canonical_node_count,
        )

        log.info(
            "context_loaded",
            session_id=context.session_id,
            turn_number=context.turn_number,
            mode=context.mode,
        )

        return context

    async def _get_recent_utterances(self, session_id: str, limit: int = 10) -> list:
        """
        Get recent utterances for context.

        Args:
            session_id: Session ID
            limit: Max utterances to return

        Returns:
            List of {"speaker": str, "text": str, "sentiment": float|None} dicts
        """
        from src.persistence.database import get_db_connection

        db = await get_db_connection()
        try:
            cursor = await db.execute(
                """
                SELECT speaker, text, turn_number FROM utterances
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
        # Note: sentiment will be added from graph_state turn_sentiments if available
        return list(
            reversed(
                [
                    {
                        "speaker": row[0],
                        "text": row[1],
                        "turn_number": row[2],
                        "sentiment": None,
                    }
                    for row in rows
                ]
            )
        )
