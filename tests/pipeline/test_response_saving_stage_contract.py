"""Tests for ResponseSavingStage contract integration (ADR-010)."""

import pytest
from unittest.mock import AsyncMock, patch

from src.services.turn_pipeline.stages.response_saving_stage import ResponseSavingStage
from src.services.turn_pipeline.context import PipelineContext


class TestResponseSavingStageContract:
    """Tests for ResponseSavingStage persisting system responses."""

    @pytest.fixture
    def context(self):
        """Create a test pipeline context with question."""
        return PipelineContext(
            session_id="test-session",
            user_input="I like oat milk",
            turn_number=1,
            next_question="Tell me more about why you like oat milk.",
        )

    @pytest.mark.asyncio
    @patch("src.persistence.database.get_db_connection")
    async def test_saves_system_response(self, mock_get_db, context):
        """Should save system response to database."""
        # Mock database connection
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.close = AsyncMock()
        mock_get_db.return_value = mock_db

        stage = ResponseSavingStage()
        result_context = await stage.process(context)

        # Verify utterance was saved
        assert result_context.system_utterance is not None
        assert result_context.system_utterance.speaker == "system"
        assert (
            result_context.system_utterance.text
            == "Tell me more about why you like oat milk."
        )

    @pytest.mark.asyncio
    @patch("src.persistence.database.get_db_connection")
    async def test_links_to_correct_turn_number(self, mock_get_db, context):
        """Should link response to correct turn number."""
        # Mock database connection
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.close = AsyncMock()
        mock_get_db.return_value = mock_db

        stage = ResponseSavingStage()
        result_context = await stage.process(context)

        # Verify the utterance is linked to turn 1
        assert result_context.system_utterance.turn_number == 1
