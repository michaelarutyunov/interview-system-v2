"""
Stage 2: Save user utterance.

Persists user input to the utterances table. Outputs
UtteranceSavingOutput contract.
"""

from typing import TYPE_CHECKING

from datetime import datetime
from uuid import uuid4

import structlog

from ..base import TurnStage
from src.domain.models.pipeline_contracts import UtteranceSavingOutput


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
                INSERT INTO utterances (id, session_id, turn_number, speaker, text, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    utterance_id,
                    context.session_id,
                    context.turn_number,
                    "user",
                    context.user_input,
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
            speaker="user",
            text=context.user_input,
        )
        context.utterance_saving_output = UtteranceSavingOutput(
            turn_number=context.turn_number,
            user_utterance_id=utterance_id,
            user_utterance=utterance,
        )

        log.debug(
            "user_utterance_saved",
            session_id=context.session_id,
            utterance_id=utterance_id,
            text_length=len(context.user_input),
        )

        return context
