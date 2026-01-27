"""Tests for UtteranceSavingStage contract integration (ADR-010)."""

import pytest
from unittest.mock import AsyncMock, patch

from src.services.turn_pipeline.stages.utterance_saving_stage import (
    UtteranceSavingStage,
)
from src.services.turn_pipeline.context import PipelineContext
from src.domain.models.pipeline_contracts import UtteranceSavingOutput


class TestUtteranceSavingStageContract:
    """Tests for UtteranceSavingStage producing UtteranceSavingOutput."""

    @pytest.fixture
    def context(self):
        """Create a test pipeline context."""
        return PipelineContext(
            session_id="test-session",
            user_input="I like oat milk",
            turn_number=1,
        )

    @pytest.mark.asyncio
    @patch("src.persistence.database.get_db_connection")
    async def test_saves_user_utterance(self, mock_get_db, context):
        """Should save user utterance to database."""
        # Mock database connection
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.close = AsyncMock()
        mock_get_db.return_value = mock_db

        stage = UtteranceSavingStage()
        result_context = await stage.process(context)

        # Verify utterance was saved
        assert result_context.user_utterance is not None
        assert result_context.user_utterance.speaker == "user"
        assert result_context.user_utterance.text == "I like oat milk"

    @pytest.mark.asyncio
    @patch("src.persistence.database.get_db_connection")
    async def test_produces_utterance_saving_output(self, mock_get_db, context):
        """Should be able to construct UtteranceSavingOutput from result."""
        # Mock database connection
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.close = AsyncMock()
        mock_get_db.return_value = mock_db

        stage = UtteranceSavingStage()
        result_context = await stage.process(context)

        # Verify we can construct the contract output
        output = UtteranceSavingOutput(
            turn_number=result_context.turn_number,
            user_utterance_id=result_context.user_utterance.id,
        )

        assert output.turn_number == 1
        assert output.user_utterance_id is not None
