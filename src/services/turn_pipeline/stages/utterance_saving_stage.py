"""
Stage 2: Save user utterance.

ADR-008 Phase 3: Persist user input to the utterances table.
"""
from typing import TYPE_CHECKING

from datetime import datetime
from uuid import uuid4

import structlog

from ..base import TurnStage


if TYPE_CHECKING:
    from ..context import PipelineContext
log = structlog.get_logger(__name__)


class UtteranceSavingStage(TurnStage):
    """
    Save user utterance to the database.

    Populates PipelineContext.user_utterance.
    """

    def __init__(self):
        """Initialize stage."""
        pass

    async def process(self, context: "PipelineContext") -> "PipelineContext":
        """
        Save user utterance to the database.

        Args:
            context: Turn context with session_id, turn_number, user_input

        Returns:
            Modified context with user_utterance set
        """
        from src.persistence.database import get_db_connection
        from src.domain.models.utterance import Utterance

        utterance_id = str(uuid4())
        now = datetime.utcnow().isoformat()

        db = await get_db_connection()
        try:
            await db.execute(
                """
                INSERT INTO utterances (id, session_id, turn_number, speaker, text, discourse_markers, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (utterance_id, context.session_id, context.turn_number, "user", context.user_input, "[]", now),
            )
            await db.commit()
        finally:
            await db.close()

        context.user_utterance = Utterance(
            id=utterance_id,
            session_id=context.session_id,
            turn_number=context.turn_number,
            speaker="user",
            text=context.user_input,
        )

        log.debug(
            "user_utterance_saved",
            session_id=context.session_id,
            utterance_id=utterance_id,
            text_length=len(context.user_input),
        )

        return context
