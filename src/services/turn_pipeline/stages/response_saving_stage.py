"""
Stage 9: Save system response.

Persists system utterance to the database. Outputs
ResponseSavingOutput contract.
"""

from typing import TYPE_CHECKING

from datetime import datetime
from uuid import uuid4

import structlog

from ..base import TurnStage
from src.domain.models.pipeline_contracts import ResponseSavingOutput


if TYPE_CHECKING:
    from ..context import PipelineContext
log = structlog.get_logger(__name__)


class ResponseSavingStage(TurnStage):
    """
    Save system utterance to the database.

    Populates PipelineContext.system_utterance.
    """

    def __init__(self):
        """Initialize stage."""
        pass

    async def process(self, context: "PipelineContext") -> "PipelineContext":
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
                INSERT INTO utterances (id, session_id, turn_number, speaker, text, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    utterance_id,
                    context.session_id,
                    context.turn_number,
                    "system",
                    context.next_question,
                    now,
                ),
            )
            await db.commit()
        finally:
            await db.close()

        # Create contract output (single source of truth)
        # No need to set individual fields - they're derived from the contract
        utterance = Utterance(
            id=utterance_id,
            session_id=context.session_id,
            turn_number=context.turn_number,
            speaker="system",
            text=context.next_question,
        )

        context.response_saving_output = ResponseSavingOutput(
            turn_number=context.turn_number,
            system_utterance_id=utterance_id,
            system_utterance=utterance,
            question_text=context.next_question,
            # timestamp auto-set
        )

        log.debug(
            "system_utterance_saved",
            session_id=context.session_id,
            utterance_id=utterance_id,
        )

        return context
