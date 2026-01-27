"""Tests for GraphUpdateStage contract integration (ADR-010)."""

import pytest
from unittest.mock import AsyncMock

from src.services.turn_pipeline.stages.graph_update_stage import GraphUpdateStage
from src.services.turn_pipeline.context import PipelineContext
from src.domain.models.knowledge_graph import KGNode, KGEdge
from src.domain.models.utterance import Utterance
from src.domain.models.extraction import ExtractionResult


class TestGraphUpdateStageContract:
    """Tests for GraphUpdateStage updating knowledge graph."""

    @pytest.fixture
    def context_with_extraction(self):
        """Create a test pipeline context with extraction."""
        from datetime import datetime, timezone

        return PipelineContext(
            session_id="test-session",
            user_input="I like oat milk",
            turn_number=1,
            extraction=ExtractionResult(
                timestamp=datetime.now(timezone.utc),
                concepts=[],
                relationships=[],
            ),
            user_utterance=Utterance(
                id="utter_123",
                session_id="test-session",
                turn_number=1,
                speaker="user",
                text="I like oat milk",
            ),
        )

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
        test_edge = KGEdge(
            id="edge_1",
            session_id="test-session",
            source_node_id="node_1",
            target_node_id="node_2",
            edge_type="related_to",
        )
        graph_service.add_extraction_to_graph = AsyncMock(
            return_value=([test_node], [test_edge])
        )

        stage = GraphUpdateStage(graph_service)
        result_context = await stage.process(context_with_extraction)

        # Verify nodes and edges were tracked
        assert len(result_context.nodes_added) == 1
        assert result_context.nodes_added[0].label == "oat milk"
        assert len(result_context.edges_added) == 1
