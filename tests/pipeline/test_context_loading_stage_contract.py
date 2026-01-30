"""Tests for ContextLoadingStage contract integration (ADR-010)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.turn_pipeline.stages.context_loading_stage import ContextLoadingStage
from src.services.turn_pipeline.context import PipelineContext


class TestContextLoadingStageContract:
    """Tests for ContextLoadingStage producing ContextLoadingOutput."""

    @pytest.fixture
    def session_repo(self):
        """Create a mock session repository."""
        mock_repo = AsyncMock()

        # Mock session
        mock_session = MagicMock()
        mock_session.methodology = "means_end_chain"
        mock_session.concept_id = "oat_milk_v2"
        mock_session.concept_name = "Oat Milk v2"
        mock_session.mode = MagicMock()
        mock_session.mode.value = "exploratory"
        mock_session.state = MagicMock()
        mock_session.state.turn_count = 0

        mock_repo.get = AsyncMock(return_value=mock_session)
        mock_repo.get_recent_strategies = AsyncMock(return_value=[])
        mock_repo.db_path = "/tmp/test.db"
        return mock_repo

    @pytest.fixture
    def graph_service(self):
        """Create a mock graph service."""
        mock_service = AsyncMock()
        mock_service.get_recent_nodes = AsyncMock(return_value=[])
        return mock_service

    @pytest.mark.asyncio
    @patch("aiosqlite.connect")
    @patch("src.persistence.database.get_db_connection")
    async def test_loads_session_metadata(
        self, mock_get_db, mock_connect, session_repo, graph_service
    ):
        """Should load session metadata from database."""
        # Mock aiosqlite connection for config reading
        mock_db = AsyncMock()
        mock_db.row_factory = None
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=None)  # No custom config
        mock_db.execute = AsyncMock(return_value=mock_cursor)
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_connect.return_value = mock_db

        # Mock get_db_connection for recent_utterances
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_cursor.fetchall = AsyncMock(return_value=[])
        mock_conn.close = AsyncMock()
        mock_get_db.return_value = mock_conn

        stage = ContextLoadingStage(session_repo, graph_service)

        context = PipelineContext(
            session_id="test-session",
            user_input="I like oat milk",
        )

        result_context = await stage.process(context)

        # Verify metadata was loaded
        assert result_context.methodology == "means_end_chain"
        assert result_context.concept_id == "oat_milk_v2"
        assert result_context.concept_name == "Oat Milk v2"
        assert result_context.turn_number >= 0
        # max_turns comes from config, not session

    @pytest.mark.asyncio
    @patch("aiosqlite.connect")
    @patch("src.persistence.database.get_db_connection")
    async def test_produces_context_loading_output(
        self, mock_get_db, mock_connect, session_repo, graph_service
    ):
        """Should be able to construct ContextLoadingOutput from result."""

        # Mock aiosqlite connection for config reading
        mock_db = AsyncMock()
        mock_db.row_factory = None
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_cursor)
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_connect.return_value = mock_db

        # Mock get_db_connection for recent_utterances
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_cursor.fetchall = AsyncMock(return_value=[])
        mock_conn.close = AsyncMock()
        mock_get_db.return_value = mock_conn

        stage = ContextLoadingStage(session_repo, graph_service)

        context = PipelineContext(
            session_id="test-session",
            user_input="I like oat milk",
        )

        result_context = await stage.process(context)

        # Verify we can construct the contract output from the result
        # The contract output is already set by the stage
        assert result_context.context_loading_output is not None
        assert result_context.context_loading_output.methodology == "means_end_chain"
        # graph_state is a placeholder at this stage (set by StateComputationStage later)
        assert result_context.context_loading_output.graph_state.node_count == 0
