"""
Stage 1: Load session context.

ADR-008 Phase 3: Load session metadata, graph state, and recent utterances.
Phase 6: Output ContextLoadingOutput contract.
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
    - Graph state (node count, edge count, depth)
    - Recent nodes
    - Recent utterances
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

        # Attach sentiment from stored turn_sentiments (if available)
        # This loads previously computed sentiment values for each utterance
        if context.graph_state and context.graph_state.extended_properties:
            turn_sentiments = context.graph_state.extended_properties.get(
                "turn_sentiments", {}
            )
            if turn_sentiments:
                # Inline sentiment loading (from old signal_helpers)
                for utterance in recent_utterances:
                    turn_num = utterance.get("turn_number")
                    if turn_num is not None:
                        sentiment = turn_sentiments.get(str(turn_num))
                        if sentiment is not None:
                            utterance["sentiment"] = sentiment

        # Get recent nodes (used by DifficultySelectionStage)
        recent_nodes = await self.graph.get_recent_nodes(context.session_id, limit=5)

        # Get recent strategy history for StrategyDiversityScorer
        # This is persisted in scoring_history and loaded here for turn continuity
        strategy_history = await self.session_repo.get_recent_strategies(
            context.session_id, limit=5
        )

        # Note: Graph state will be loaded in StateComputationStage after graph updates
        # For now, provide a placeholder/empty GraphState to satisfy the contract
        from src.domain.models.knowledge_graph import (
            GraphState,
            DepthMetrics,
        )

        placeholder_graph_state = context.graph_state or GraphState(
            node_count=0,
            edge_count=0,
            depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0),
            current_phase="exploratory",
            turn_count=session.state.turn_count or 0,
        )

        # Create contract output (single source of truth)
        # No need to set individual fields - they're derived from the contract
        context.context_loading_output = ContextLoadingOutput(
            methodology=session.methodology,
            concept_id=session.concept_id,
            concept_name=session.concept_name,
            # turn_count is completed turns, so current turn is turn_count + 1
            turn_number=(session.state.turn_count or 0) + 1,
            mode=session.mode.value,
            max_turns=max_turns,
            recent_utterances=recent_utterances,
            recent_nodes=recent_nodes,
            strategy_history=strategy_history,
            graph_state=placeholder_graph_state,  # Will be updated by StateComputationStage
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
