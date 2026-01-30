"""Tests for GraphUpdateStage contract integration (ADR-010)."""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone

from src.services.turn_pipeline.stages.graph_update_stage import GraphUpdateStage
from src.services.turn_pipeline.context import PipelineContext
from src.domain.models.knowledge_graph import (
    KGNode,
    GraphState,
    DepthMetrics,
    CoverageState,
)
from src.domain.models.utterance import Utterance
from src.domain.models.extraction import ExtractionResult
from src.domain.models.pipeline_contracts import (
    ContextLoadingOutput,
    ExtractionOutput,
    UtteranceSavingOutput,
)


class TestGraphUpdateStageContract:
    """Tests for GraphUpdateStage updating knowledge graph."""

    @pytest.fixture
    def context_with_extraction(self):
        """Create a test pipeline context with extraction."""
        ctx = PipelineContext(
            session_id="test-session",
            user_input="I like oat milk",
        )

        # Set ContextLoadingOutput
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
            mode="exploratory",
            max_turns=20,
            recent_utterances=[],
            strategy_history=[],
            graph_state=graph_state,
            recent_nodes=[],
        )

        # Set UtteranceSavingOutput
        user_utterance = Utterance(
            id="utter_123",
            session_id="test-session",
            turn_number=1,
            speaker="user",
            text="I like oat milk",
        )
        ctx.utterance_saving_output = UtteranceSavingOutput(
            turn_number=1,
            user_utterance_id="utter_123",
            user_utterance=user_utterance,
        )

        # Set ExtractionOutput
        ctx.extraction_output = ExtractionOutput(
            extraction=ExtractionResult(
                timestamp=datetime.now(timezone.utc),
                concepts=[],
                relationships=[],
            ),
            methodology="means_end_chain",
            concept_count=0,
            relationship_count=0,
        )

        return ctx

    @pytest.fixture
    def graph_service(self):
        """Create a mock graph service."""
        mock_service = AsyncMock()
        mock_service.add_extraction_to_graph = AsyncMock(return_value=([], []))
        return mock_service

    @pytest.mark.asyncio
    async def test_adds_extracted_concepts_to_graph(
        self, context_with_extraction, graph_service
    ):
        """Should add extracted concepts to knowledge graph."""
        stage = GraphUpdateStage(graph_service)

        await stage.process(context_with_extraction)

        # Verify graph was updated
        graph_service.add_extraction_to_graph.assert_called_once()

    @pytest.mark.asyncio
    async def test_updates_graph_state_after_addition(
        self, context_with_extraction, graph_service
    ):
        """Should track nodes and edges added to graph."""
        # Mock the service to return actual nodes
        test_node = KGNode(
            id="node_1",
            session_id="test-session",
            label="oat milk",
            node_type="attribute",
        )
        # edges_added should be a list of dicts, not KGEdge objects
        test_edge = {
            "id": "edge_1",
            "session_id": "test-session",
            "source_node_id": "node_1",
            "target_node_id": "node_2",
            "edge_type": "related_to",
        }
        graph_service.add_extraction_to_graph = AsyncMock(
            return_value=([test_node], [test_edge])
        )

        stage = GraphUpdateStage(graph_service)
        result_context = await stage.process(context_with_extraction)

        # Verify nodes and edges were tracked
        assert len(result_context.nodes_added) == 1
        assert result_context.nodes_added[0].label == "oat milk"
        assert len(result_context.edges_added) == 1
