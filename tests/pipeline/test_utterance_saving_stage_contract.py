"""Tests for UtteranceSavingStage contract integration (ADR-010)."""

import pytest
from unittest.mock import AsyncMock, patch

from src.services.turn_pipeline.stages.utterance_saving_stage import (
    UtteranceSavingStage,
)
from src.services.turn_pipeline.context import PipelineContext
from src.domain.models.pipeline_contracts import (
    ContextLoadingOutput,
)
from src.domain.models.knowledge_graph import GraphState, DepthMetrics, CoverageState


class TestUtteranceSavingStageContract:
    """Tests for UtteranceSavingStage producing UtteranceSavingOutput."""

    @pytest.fixture
    def context(self):
        """Create a test pipeline context with turn_number."""
        ctx = PipelineContext(
            session_id="test-session",
            user_input="I like oat milk",
        )

        # Set ContextLoadingOutput to provide turn_number
        graph_state = GraphState(
            node_count=0,
            edge_count=0,
            depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=1,
        )
        ctx.context_loading_output = ContextLoadingOutput(
            methodology="means_end_chain",
            concept_id="oat_milk",
            concept_name="Oat Milk",
            turn_number=1,
            mode="coverage_driven",
            max_turns=20,
            recent_utterances=[],
            strategy_history=[],
            graph_state=graph_state,
            recent_nodes=[],
        )

        return ctx

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
        """Should produce UtteranceSavingOutput with all required fields."""
        # Mock database connection
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.close = AsyncMock()
        mock_get_db.return_value = mock_db

        stage = UtteranceSavingStage()
        result_context = await stage.process(context)

        # Verify the contract output was produced correctly
        # The stage sets utterance_saving_output directly
        assert result_context.utterance_saving_output is not None
        assert result_context.utterance_saving_output.turn_number == 1
        assert result_context.utterance_saving_output.user_utterance_id is not None
        assert result_context.utterance_saving_output.user_utterance is not None
        assert (
            result_context.utterance_saving_output.user_utterance.text
            == "I like oat milk"
        )
