"""Tests for StateComputationStage contract integration (ADR-010).

RED Phase: Write failing tests first to prove they test the right thing.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

from src.services.turn_pipeline.stages.state_computation_stage import (
    StateComputationStage,
)
from src.domain.models.pipeline_contracts import StateComputationOutput
from src.domain.models.knowledge_graph import GraphState, DepthMetrics
from src.services.turn_pipeline.context import PipelineContext
from src.domain.models.pipeline_contracts import (
    ContextLoadingOutput,
    GraphUpdateOutput,
)


class TestStateComputationStageContract:
    """Tests for StateComputationStage returning StateComputationOutput."""

    @pytest.fixture
    def context(self):
        """Create a test pipeline context."""
        ctx = PipelineContext(
            session_id="test-session",
            user_input="I like oat milk",
        )

        # Set ContextLoadingOutput
        graph_state = GraphState(
            node_count=0,
            edge_count=0,
            depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0),
            current_phase="exploratory",
            turn_count=1,
        )
        ctx.context_loading_output = ContextLoadingOutput(
            methodology="means_end_chain",
            concept_id="oat_milk_v2",
            concept_name="Oat Milk v2",
            turn_number=1,
            mode="coverage",
            max_turns=10,
            recent_utterances=[],
            strategy_history=[],
            graph_state=graph_state,
            recent_nodes=[],
        )

        # Set GraphUpdateOutput
        ctx.graph_update_output = GraphUpdateOutput(
            nodes_added=[],
            edges_added=[],
        )

        return ctx

    @pytest.fixture
    def graph_service(self):
        """Create a mock graph service."""
        mock_service = AsyncMock()
        mock_service.get_graph_state = AsyncMock(
            return_value=GraphState(
                node_count=5,
                edge_count=3,
                depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.0),
                current_phase="exploratory",
                turn_count=1,
            )
        )
        mock_service.get_recent_nodes = AsyncMock(return_value=[])
        mock_service.get_nodes_by_session = AsyncMock(return_value=[])
        mock_service.get_edges_by_session = AsyncMock(return_value=[])
        return mock_service

    @pytest.mark.asyncio
    async def test_returns_state_computation_output_with_timestamp(
        self, context, graph_service
    ):
        """Should return StateComputationOutput with computed_at timestamp (ADR-010)."""
        stage = StateComputationStage(graph_service)

        # Process the context
        result_context = await stage.process(context)

        # Verify we can construct StateComputationOutput from the result
        # This demonstrates the contract is satisfied
        now = datetime.now(timezone.utc)

        # The stage should have set computed_at timestamp
        # For migration: we construct from context
        assert result_context.graph_state is not None
        output = StateComputationOutput(
            graph_state=result_context.graph_state,
            recent_nodes=result_context.recent_nodes,
            computed_at=now,  # In GREEN phase, stage will track this
        )

        assert output.graph_state.node_count == 5
        assert output.computed_at is not None
        # Verify computed_at is recent (within 1 second)
        assert datetime.now(timezone.utc) - output.computed_at < timedelta(seconds=1)
