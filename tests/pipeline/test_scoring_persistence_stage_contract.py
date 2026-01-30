"""Tests for ScoringPersistenceStage contract integration (ADR-010)."""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from src.services.turn_pipeline.stages.scoring_persistence_stage import (
    ScoringPersistenceStage,
)
from src.services.turn_pipeline.context import PipelineContext
from src.domain.models.knowledge_graph import GraphState, DepthMetrics
from src.domain.models.pipeline_contracts import (
    ContextLoadingOutput,
    StateComputationOutput,
    StrategySelectionOutput,
)


class TestScoringPersistenceStageContract:
    """Tests for ScoringPersistenceStage persisting scoring data."""

    @pytest.fixture
    def context(self):
        """Create a test pipeline context with strategy selection."""
        ctx = PipelineContext(
            session_id="test-session",
            user_input="I like oat milk",
        )

        # Set ContextLoadingOutput for basic session metadata
        graph_state = GraphState(
            node_count=5,
            edge_count=3,
            depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.0),
            current_phase="exploratory",
            turn_count=1,
        )
        ctx.context_loading_output = ContextLoadingOutput(
            methodology="means_end_chain",
            concept_id="oat_milk_v2",
            concept_name="Oat Milk v2",
            turn_number=1,
            mode="exploratory",
            max_turns=20,
            recent_utterances=[],
            strategy_history=[],
            graph_state=graph_state,
            recent_nodes=[],
        )

        # Set StateComputationOutput with graph_state
        ctx.state_computation_output = StateComputationOutput(
            graph_state=graph_state,
            recent_nodes=[],
            computed_at=datetime.now(timezone.utc),
        )

        # Set StrategySelectionOutput with methodology-based selection
        # (selection_result is None for methodology-based selection)
        ctx.strategy_selection_output = StrategySelectionOutput(
            strategy="deepen",
            focus={"focus_type": "element", "focus_description": "oat milk"},
            signals={"signal1": "value1"},
            strategy_alternatives=[("broaden", 0.8), ("deepen", 0.9)],
        )

        return ctx

    @pytest.fixture
    def session_repo(self):
        """Create a mock session repository."""
        mock_repo = AsyncMock()
        mock_repo.db_path = "/tmp/test.db"
        mock_repo.update_state = AsyncMock()
        mock_repo.save_qualitative_signals = AsyncMock()
        return mock_repo

    @pytest.mark.asyncio
    @patch("aiosqlite.connect")
    async def test_saves_scoring_data(self, mock_connect, context, session_repo):
        """Should save scoring breakdown to database."""
        # Mock aiosqlite connection - needs to return the connection from __aenter__
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.commit = AsyncMock()

        # Create the async context manager mock
        mock_connect.return_value.__aenter__.return_value = mock_conn
        mock_connect.return_value.__aexit__.return_value = None

        stage = ScoringPersistenceStage(session_repo)
        result_context = await stage.process(context)

        # Verify scoring data was saved
        assert result_context.scoring is not None
        # Verify the connection was used
        assert mock_conn.execute.called

    @pytest.mark.asyncio
    @patch("aiosqlite.connect")
    async def test_updates_turn_count_in_session(
        self, mock_connect, context, session_repo
    ):
        """Should update turn_count in session state."""
        # Mock aiosqlite connection
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.commit = AsyncMock()
        mock_connect.return_value.__aenter__.return_value = mock_conn
        mock_connect.return_value.__aexit__.return_value = None

        stage = ScoringPersistenceStage(session_repo)
        await stage.process(context)

        # Verify update_state was called with correct turn_count
        session_repo.update_state.assert_called_once()
        call_args = session_repo.update_state.call_args[0]
        assert (
            call_args[1].turn_count == context.turn_number
        )  # SessionState's turn_count

    @pytest.mark.asyncio
    @patch("aiosqlite.connect")
    async def test_populates_scoring_in_context(
        self, mock_connect, context, session_repo
    ):
        """Should populate scoring dict in context."""
        # Mock aiosqlite connection
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.commit = AsyncMock()
        mock_connect.return_value.__aenter__.return_value = mock_conn
        mock_connect.return_value.__aexit__.return_value = None

        stage = ScoringPersistenceStage(session_repo)
        result_context = await stage.process(context)

        # Verify scoring was populated in context
        assert result_context.scoring is not None
        assert "depth" in result_context.scoring
        assert "saturation" in result_context.scoring
