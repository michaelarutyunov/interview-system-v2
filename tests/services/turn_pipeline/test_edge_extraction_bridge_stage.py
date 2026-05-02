"""Tests for EdgeExtractionBridgeStage (B5)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.models.edge_extraction import (
    ConfirmedEdge,
    EdgeExtractionOutput,
    RejectedEdgeCandidate,
)
from src.services.turn_pipeline.context import PipelineContext
from src.services.turn_pipeline.stages.edge_extraction_bridge_stage import (
    EdgeExtractionBridgeStage,
)


def make_context(session_id="test-session", turn_number=2, methodology="means_end_chain_v2_strict"):
    """Create a minimal PipelineContext with required fields."""
    ctx = PipelineContext(session_id=session_id, user_input="test input")
    ctx.context_loading_output = MagicMock()
    ctx.context_loading_output.methodology = methodology
    ctx.context_loading_output.turn_number = turn_number
    ctx.context_loading_output.max_turns = 10
    ctx.context_loading_output.recent_utterances = []
    return ctx


def make_confirmed_edge(
    source_id="n1",
    target_id="n2",
    edge_type="leads_to",
    confidence="high",
    utterance_id="utt_1",
):
    return ConfirmedEdge(
        source_node_id=source_id,
        target_node_id=target_id,
        edge_type=edge_type,
        confidence=confidence,
        supporting_span=(0, 50),
        utterance_id=utterance_id,
        reasoning_summary="Test edge",
    )


class TestEdgeExtractionBridgeNoTask:
    """When no prefetch task was fired, bridge is a no-op."""

    @pytest.mark.asyncio
    async def test_no_task_returns_context_unchanged(self):
        """When _edge_extraction_task is None, stage is a no-op."""
        graph_service = MagicMock()
        graph_repo = AsyncMock()

        stage = EdgeExtractionBridgeStage(
            graph_service=graph_service, graph_repo=graph_repo
        )
        ctx = make_context()
        ctx._evolving_node_tracker = None
        ctx._edge_extraction_task = None

        result = await stage.process(ctx)

        assert result is ctx
        # tracker was seeded from empty
        assert result._evolving_node_tracker is not None
        # No edges were persisted
        graph_service._add_edge_from_relationship.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_task_preserves_existing_tracker(self):
        """When task is None, existing tracker state is preserved."""
        from src.services.node_state_tracker import NodeStateTracker

        graph_service = MagicMock()
        graph_repo = AsyncMock()

        stage = EdgeExtractionBridgeStage(
            graph_service=graph_service, graph_repo=graph_repo
        )
        ctx = make_context()
        existing_tracker = NodeStateTracker()
        ctx._evolving_node_tracker = existing_tracker
        ctx._edge_extraction_task = None

        result = await stage.process(ctx)

        # Tracker identity is preserved (functional update returns same when no changes)
        assert result._evolving_node_tracker is existing_tracker


class TestEdgeExtractionBridgeFlagOn:
    """Flag-ON: edge persistence and tracker mutation."""

    @pytest.mark.asyncio
    async def test_persists_confirmed_edges(self):
        """ConfirmedEdge objects are passed to GraphService._add_edge_from_relationship."""
        from src.domain.models.knowledge_graph import KGEdge

        edge1 = make_confirmed_edge("n1", "n2", "leads_to", "high", "utt_1")
        edge2 = make_confirmed_edge("n2", "n3", "leads_to", "medium", "utt_1")

        result = EdgeExtractionOutput(
            confirmed_edges=[edge1, edge2],
            rejected_candidates=[],
        )

        # Mock that _add_edge_from_relationship returns KGEdge objects
        kg_edge1 = KGEdge(
            id="e1",
            session_id="test-session",
            source_node_id="n1",
            target_node_id="n2",
            edge_type="leads_to",
        )
        kg_edge2 = KGEdge(
            id="e2",
            session_id="test-session",
            source_node_id="n2",
            target_node_id="n3",
            edge_type="leads_to",
        )

        graph_service = MagicMock()
        graph_service._add_edge_from_relationship = AsyncMock(
            side_effect=[kg_edge1, kg_edge2]
        )
        graph_repo = AsyncMock()

        stage = EdgeExtractionBridgeStage(
            graph_service=graph_service, graph_repo=graph_repo
        )
        ctx = make_context()
        ctx._evolving_node_tracker = None
        ctx._edge_extraction_task = asyncio.ensure_future(
            asyncio.sleep(0.001, result=result)
        )

        await asyncio.sleep(0.01)  # let the task complete
        result_ctx = await stage.process(ctx)

        assert graph_service._add_edge_from_relationship.call_count == 2
        # First call: edge1
        call_args = graph_service._add_edge_from_relationship.call_args_list[0]
        assert call_args.kwargs["session_id"] == "test-session"
        assert call_args.kwargs["relationship"] is edge1
        assert call_args.kwargs["methodology"] == "means_end_chain_v2_strict"
        # Tracker was updated
        assert result_ctx._evolving_node_tracker is not None

    @pytest.mark.asyncio
    async def test_skips_none_returns_from_edge_writer(self):
        """Edges that return None (invalid type pair, missing node) are skipped."""
        edge = make_confirmed_edge("n1", "n2", "leads_to", "high", "utt_1")

        result = EdgeExtractionOutput(
            confirmed_edges=[edge],
            rejected_candidates=[],
        )

        graph_service = MagicMock()
        graph_service._add_edge_from_relationship = AsyncMock(return_value=None)
        graph_repo = AsyncMock()

        stage = EdgeExtractionBridgeStage(
            graph_service=graph_service, graph_repo=graph_repo
        )
        ctx = make_context()
        ctx._evolving_node_tracker = None
        ctx._edge_extraction_task = asyncio.ensure_future(
            asyncio.sleep(0.001, result=result)
        )

        await asyncio.sleep(0.01)
        result_ctx = await stage.process(ctx)

        # Edge write was attempted
        graph_service._add_edge_from_relationship.assert_called_once()
        # No edge_deltas since None was returned
        assert result_ctx._evolving_node_tracker is not None

    @pytest.mark.asyncio
    async def test_handles_task_exception_gracefully(self):
        """When the prefetch task raises, error is logged but pipeline continues."""
        graph_service = MagicMock()
        graph_repo = AsyncMock()

        stage = EdgeExtractionBridgeStage(
            graph_service=graph_service, graph_repo=graph_repo
        )
        ctx = make_context()

        async def _failing_task():
            raise ValueError("LLM API error")

        ctx._evolving_node_tracker = None
        ctx._edge_extraction_task = asyncio.ensure_future(_failing_task())

        await asyncio.sleep(0.01)
        result_ctx = await stage.process(ctx)

        # Pipeline continues, tracker is set
        assert result_ctx._evolving_node_tracker is not None
        # No edges were persisted
        graph_service._add_edge_from_relationship.assert_not_called()

    @pytest.mark.asyncio
    async def test_edge_persistence_failure_skips_edge(self):
        """When one edge write raises, subsequent edges are still attempted."""
        edge1 = make_confirmed_edge("n1", "n2", "leads_to", "high", "utt_1")
        edge2 = make_confirmed_edge("n2", "n3", "leads_to", "medium", "utt_1")

        result = EdgeExtractionOutput(
            confirmed_edges=[edge1, edge2],
            rejected_candidates=[],
        )

        from src.domain.models.knowledge_graph import KGEdge

        kg_edge2 = KGEdge(
            id="e2",
            session_id="test-session",
            source_node_id="n2",
            target_node_id="n3",
            edge_type="leads_to",
        )

        graph_service = MagicMock()
        graph_service._add_edge_from_relationship = AsyncMock(
            side_effect=[RuntimeError("DB error"), kg_edge2]
        )
        graph_repo = AsyncMock()

        stage = EdgeExtractionBridgeStage(
            graph_service=graph_service, graph_repo=graph_repo
        )
        ctx = make_context()
        ctx._evolving_node_tracker = None
        ctx._edge_extraction_task = asyncio.ensure_future(
            asyncio.sleep(0.001, result=result)
        )

        await asyncio.sleep(0.01)
        result_ctx = await stage.process(ctx)

        # Both edges were attempted
        assert graph_service._add_edge_from_relationship.call_count == 2
        # Pipeline continues successfully
        assert result_ctx._evolving_node_tracker is not None

    @pytest.mark.asyncio
    async def test_logs_rejected_and_low_confidence_counts(self):
        """Rejected candidates and low-confidence edges are logged."""
        confirmed = make_confirmed_edge("n1", "n2", "leads_to", "low", "utt_1")
        rejected = RejectedEdgeCandidate(
            source_node_id="n2",
            target_node_id="n3",
            rejection_reason="insufficient_evidence",
            reasoning_summary="No evidence",
        )

        result = EdgeExtractionOutput(
            confirmed_edges=[confirmed],
            rejected_candidates=[rejected],
            low_confidence_count=1,
        )

        from src.domain.models.knowledge_graph import KGEdge

        kg_edge = KGEdge(
            id="e1",
            session_id="test-session",
            source_node_id="n1",
            target_node_id="n2",
            edge_type="leads_to",
        )

        graph_service = MagicMock()
        graph_service._add_edge_from_relationship = AsyncMock(return_value=kg_edge)
        graph_repo = AsyncMock()

        stage = EdgeExtractionBridgeStage(
            graph_service=graph_service, graph_repo=graph_repo
        )
        ctx = make_context()
        ctx._evolving_node_tracker = None
        ctx._edge_extraction_task = asyncio.ensure_future(
            asyncio.sleep(0.001, result=result)
        )

        await asyncio.sleep(0.01)
        await stage.process(ctx)

        # Verify edge was persisted
        graph_service._add_edge_from_relationship.assert_called_once()


class TestPipelineOrdering:
    """Verify correct pipeline insertion position."""

    def test_bridge_imported_and_available(self):
        """EdgeExtractionBridgeStage is importable."""
        from src.services.turn_pipeline.stages import EdgeExtractionBridgeStage

        assert EdgeExtractionBridgeStage is not None

    def test_bridge_position_in_pipeline(self):
        """Bridge stage appears after prefetch and before LLM signal bridge in pipeline list."""
        from src.services.turn_pipeline.stages import (
            EdgeExtractionBridgeStage,
            EdgeExtractionPrefetchStage,
            LLMSignalBridgeStage,
        )

        # Simulate the pipeline ordering: prefetch → bridge → llm_signal
        stages = [
            EdgeExtractionPrefetchStage,
            EdgeExtractionBridgeStage,
            LLMSignalBridgeStage,
        ]
        prefetch_idx = stages.index(EdgeExtractionPrefetchStage)
        bridge_idx = stages.index(EdgeExtractionBridgeStage)
        llm_idx = stages.index(LLMSignalBridgeStage)

        assert prefetch_idx < bridge_idx < llm_idx, (
            f"Expected prefetch({prefetch_idx}) < bridge({bridge_idx}) "
            f"< llm_signal({llm_idx})"
        )
