"""
Stage 9: Save system response.

ADR-008 Phase 3: Persist system utterance to the database.
"""
from typing import TYPE_CHECKING

from datetime import datetime
from uuid import uuid4

import structlog

from ..base import TurnStage


if TYPE_CHECKING:
    from src.domain.models.turn import TurnContext
log = structlog.get_logger(__name__)


class ResponseSavingStage(TurnStage):
    """
    Save system utterance to the database.

    Populates TurnContext.system_utterance.
    """

    def __init__(self):
        """Initialize stage."""
        pass

    async def process(self, context: "TurnContext") -> "TurnContext":
        """
        Save system utterance to the database.

        Args:
            context: Turn context with session_id, turn_number, next_question

        Returns:
            Modified context with system_utterance set
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
                (utterance_id, context.session_id, context.turn_number, "system", context.next_question, "[]", now),
            )
            await db.commit()
        finally:
            await db.close()

        context.system_utterance = Utterance(
            id=utterance_id,
            session_id=context.session_id,
            turn_number=context.turn_number,
            speaker="system",
            text=context.next_question,
        )

        log.debug(
            "system_utterance_saved",
            session_id=context.session_id,
            utterance_id=utterance_id,
        )

        return context
