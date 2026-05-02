"""Tests for EdgeExtractionPrefetchStage (B4)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.turn_pipeline.context import PipelineContext
from src.services.turn_pipeline.stages.edge_extraction_prefetch_stage import (
    EdgeExtractionPrefetchStage,
)


def make_context(session_id="test-session", turn_number=2, methodology="means_end_chain_v2_strict"):
    """Create a minimal PipelineContext with required fields."""
    ctx = PipelineContext(session_id=session_id, user_input="test input")
    ctx.context_loading_output = MagicMock()
    ctx.context_loading_output.methodology = methodology
    ctx.context_loading_output.turn_number = turn_number
    ctx.context_loading_output.max_turns = 10
    ctx.context_loading_output.recent_utterances = [
        {"speaker": "system", "text": "Why is that important?", "id": "utt_sys_1"},
        {"speaker": "user", "text": "Because it helps me.", "id": "utt_user_1"},
    ]
    return ctx


class TestEdgeExtractionPrefetchFlagOff:
    """Flag-OFF: stage is a no-op."""

    @pytest.mark.asyncio
    async def test_flag_off_sets_task_to_none(self):
        """When feature flag is off, context._edge_extraction_task is set to None."""
        stage = EdgeExtractionPrefetchStage(
            graph_repo=MagicMock(), utterance_repo=MagicMock()
        )
        ctx = make_context()

        with patch(
            "src.services.turn_pipeline.stages.edge_extraction_prefetch_stage.interview_config"
        ) as mock_config:
            mock_config.features.enable_edge_extraction_stage = False
            result = await stage.process(ctx)

        assert result._edge_extraction_task is None
        assert result is ctx  # context returned by identity

    @pytest.mark.asyncio
    async def test_flag_off_no_llm_call(self):
        """When feature flag is off, no LLM client is fetched."""
        stage = EdgeExtractionPrefetchStage(
            graph_repo=MagicMock(), utterance_repo=MagicMock()
        )
        ctx = make_context()

        with patch(
            "src.services.turn_pipeline.stages.edge_extraction_prefetch_stage.interview_config"
        ) as mock_config:
            mock_config.features.enable_edge_extraction_stage = False
            with patch(
                "src.services.turn_pipeline.stages.edge_extraction_prefetch_stage.get_llm_client"
            ) as mock_get_client:
                await stage.process(ctx)
                mock_get_client.assert_not_called()


class TestEdgeExtractionPrefetchFlagOn:
    """Flag-ON: candidate assembly and task firing."""

    @pytest.mark.asyncio
    async def test_skips_when_no_graph_update_output(self):
        """When Stage 4 hasn't run, stage sets task to None."""
        stage = EdgeExtractionPrefetchStage(
            graph_repo=MagicMock(), utterance_repo=MagicMock()
        )
        ctx = make_context()
        ctx.graph_update_output = None  # Stage 4 not run

        with patch(
            "src.services.turn_pipeline.stages.edge_extraction_prefetch_stage.interview_config"
        ) as mock_config:
            mock_config.features.enable_edge_extraction_stage = True
            result = await stage.process(ctx)

        assert result._edge_extraction_task is None

    @pytest.mark.asyncio
    async def test_candidate_assembly_empty_when_no_data(self):
        """When there's no previous_focus and no concept_to_node_id entries,
        no candidates are assembled and task is None."""
        graph_repo = AsyncMock()
        utterance_repo = AsyncMock()

        stage = EdgeExtractionPrefetchStage(
            graph_repo=graph_repo, utterance_repo=utterance_repo
        )
        ctx = make_context(turn_number=0)
        ctx.graph_update_output = MagicMock()
        ctx.graph_update_output.concept_to_node_id = {}  # empty
        ctx._evolving_node_tracker = MagicMock()
        ctx._evolving_node_tracker.previous_focus = None  # no focus

        with patch(
            "src.services.turn_pipeline.stages.edge_extraction_prefetch_stage.interview_config"
        ) as mock_config:
            mock_config.features.enable_edge_extraction_stage = True
            result = await stage.process(ctx)

        assert result._edge_extraction_task is None

    @pytest.mark.asyncio
    async def test_candidate_assembly_with_current_nodes(self):
        """CURRENT nodes (from concept_to_node_id) are tagged correctly."""
        from src.domain.models.knowledge_graph import KGNode

        node1 = KGNode(
            id="n1",
            session_id="test-session",
            label="Health awareness",
            node_type="attribute",
            source_utterance_ids=["utt_user_1"],
        )

        graph_repo = AsyncMock()
        graph_repo.get_node = AsyncMock(return_value=node1)
        graph_repo.get_neighbours = AsyncMock(return_value=[])
        graph_repo.get_nodes_by_turn = AsyncMock(return_value=[])
        graph_repo.get_edges_by_session = AsyncMock(return_value=[])

        utterance_repo = AsyncMock()
        utterance_repo.get_by_ids = AsyncMock(return_value=[])
        utterance_repo.get_by_turn = AsyncMock(return_value=[])

        stage = EdgeExtractionPrefetchStage(
            graph_repo=graph_repo, utterance_repo=utterance_repo
        )
        ctx = make_context(turn_number=2)
        ctx.graph_update_output = MagicMock()
        ctx.graph_update_output.concept_to_node_id = {"health awareness": "n1"}
        ctx._evolving_node_tracker = MagicMock()
        ctx._evolving_node_tracker.previous_focus = None

        # We need to patch get_llm_client and interview_config to prevent
        # the actual LLM call — just check candidate assembly through
        # the internal method.
        candidates, focus = await stage._assemble_candidate_nodes(
            ctx, "test-session", 2
        )

        assert focus is None
        assert len(candidates) == 1
        assert candidates[0]["tag"] == "CURRENT"
        assert candidates[0]["node_id"] == "n1"
        assert candidates[0]["label"] == "Health awareness"
        assert candidates[0]["node_type"] == "attribute"
        assert candidates[0]["turn"] == 2

    @pytest.mark.asyncio
    async def test_candidate_assembly_with_focus_and_neighbors(self):
        """FOCUS and NEIGHBOR nodes are tagged correctly."""
        from src.domain.models.knowledge_graph import KGNode

        focus_node = KGNode(
            id="n_focus",
            session_id="test-session",
            label="Weight loss",
            node_type="consequence",
            source_utterance_ids=["utt_1"],
        )
        neighbor_node = KGNode(
            id="n_neighbor",
            session_id="test-session",
            label="Exercise",
            node_type="attribute",
            source_utterance_ids=["utt_2"],
        )

        async def get_node_side_effect(node_id):
            if node_id == "n_focus":
                return focus_node
            elif node_id == "n_neighbor":
                return neighbor_node
            return None

        graph_repo = AsyncMock()
        graph_repo.get_node = AsyncMock(side_effect=get_node_side_effect)
        graph_repo.get_neighbours = AsyncMock(return_value=["n_neighbor"])
        graph_repo.get_nodes_by_turn = AsyncMock(return_value=[])
        graph_repo.get_edges_by_session = AsyncMock(return_value=[])

        stage = EdgeExtractionPrefetchStage(
            graph_repo=graph_repo, utterance_repo=AsyncMock()
        )
        ctx = make_context(turn_number=3)
        ctx.graph_update_output = MagicMock()
        ctx.graph_update_output.concept_to_node_id = {}
        ctx._evolving_node_tracker = MagicMock()
        ctx._evolving_node_tracker.previous_focus = "n_focus"

        candidates, focus = await stage._assemble_candidate_nodes(
            ctx, "test-session", 3
        )

        assert focus == "n_focus"
        tags = {c["tag"] for c in candidates}
        assert "FOCUS" in tags
        assert "NEIGHBOR" in tags
        focus_candidate = [c for c in candidates if c["tag"] == "FOCUS"][0]
        assert focus_candidate["node_id"] == "n_focus"
        neighbor_candidate = [c for c in candidates if c["tag"] == "NEIGHBOR"][0]
        assert neighbor_candidate["node_id"] == "n_neighbor"

    @pytest.mark.asyncio
    async def test_candidate_assembly_with_recent_nodes(self):
        """RECENT nodes are tagged and deduplicated against earlier categories."""
        from src.domain.models.knowledge_graph import KGNode

        node = KGNode(
            id="n_recent",
            session_id="test-session",
            label="Diet change",
            node_type="attribute",
            source_utterance_ids=["utt_prev"],
        )

        graph_repo = AsyncMock()
        graph_repo.get_node = AsyncMock(return_value=None)  # no focus/current nodes
        graph_repo.get_neighbours = AsyncMock(return_value=[])
        graph_repo.get_nodes_by_turn = AsyncMock(return_value=[node])
        graph_repo.get_edges_by_session = AsyncMock(return_value=[])

        stage = EdgeExtractionPrefetchStage(
            graph_repo=graph_repo, utterance_repo=AsyncMock()
        )
        ctx = make_context(turn_number=3)
        ctx.graph_update_output = MagicMock()
        ctx.graph_update_output.concept_to_node_id = {}
        ctx._evolving_node_tracker = MagicMock()
        ctx._evolving_node_tracker.previous_focus = None

        candidates, focus = await stage._assemble_candidate_nodes(
            ctx, "test-session", 3
        )

        assert focus is None
        assert len(candidates) == 1
        assert candidates[0]["tag"] == "RECENT"
        assert candidates[0]["node_id"] == "n_recent"
        assert candidates[0]["turn"] == 2  # turn_number - 1

    @pytest.mark.asyncio
    async def test_dedup_across_categories(self):
        """A node appearing in CURRENT is not duplicated in RECENT."""
        from src.domain.models.knowledge_graph import KGNode

        shared_node = KGNode(
            id="n_shared",
            session_id="test-session",
            label="Shared concept",
            node_type="attribute",
            source_utterance_ids=["utt_both"],
        )

        graph_repo = AsyncMock()
        graph_repo.get_node = AsyncMock(return_value=shared_node)
        graph_repo.get_neighbours = AsyncMock(return_value=[])
        graph_repo.get_nodes_by_turn = AsyncMock(return_value=[shared_node])
        graph_repo.get_edges_by_session = AsyncMock(return_value=[])

        stage = EdgeExtractionPrefetchStage(
            graph_repo=graph_repo, utterance_repo=AsyncMock()
        )
        ctx = make_context(turn_number=3)
        ctx.graph_update_output = MagicMock()
        ctx.graph_update_output.concept_to_node_id = {"shared concept": "n_shared"}
        ctx._evolving_node_tracker = MagicMock()
        ctx._evolving_node_tracker.previous_focus = None

        candidates, focus = await stage._assemble_candidate_nodes(
            ctx, "test-session", 3
        )

        # Should appear once, tagged as CURRENT (first category seen)
        assert len(candidates) == 1
        assert candidates[0]["tag"] == "CURRENT"

    @pytest.mark.asyncio
    async def test_fires_task_when_candidates_present(self):
        """When candidates exist, an asyncio task is created."""
        from src.domain.models.knowledge_graph import KGNode

        node = KGNode(
            id="n1",
            session_id="test-session",
            label="Health",
            node_type="attribute",
            source_utterance_ids=["utt_1"],
        )

        graph_repo = AsyncMock()
        graph_repo.get_node = AsyncMock(return_value=node)
        graph_repo.get_neighbours = AsyncMock(return_value=[])
        graph_repo.get_nodes_by_turn = AsyncMock(return_value=[])
        graph_repo.get_edges_by_session = AsyncMock(return_value=[])

        utterance_repo = AsyncMock()
        utterance_repo.get_by_ids = AsyncMock(return_value=[])
        utterance_repo.get_by_turn = AsyncMock(return_value=[])

        stage = EdgeExtractionPrefetchStage(
            graph_repo=graph_repo, utterance_repo=utterance_repo
        )
        ctx = make_context(turn_number=2)
        ctx.graph_update_output = MagicMock()
        ctx.graph_update_output.concept_to_node_id = {"health": "n1"}
        ctx._evolving_node_tracker = MagicMock()
        ctx._evolving_node_tracker.previous_focus = None

        mock_llm_client = MagicMock()
        mock_llm_client.complete = AsyncMock(
            return_value=MagicMock(content="<edge_analysis></edge_analysis>")
        )

        with patch(
            "src.services.turn_pipeline.stages.edge_extraction_prefetch_stage.interview_config"
        ) as mock_config:
            mock_config.features.enable_edge_extraction_stage = True
            with patch(
                "src.services.turn_pipeline.stages.edge_extraction_prefetch_stage.get_llm_client"
            ) as mock_get_client:
                mock_get_client.return_value = mock_llm_client
                result = await stage.process(ctx)

        assert result._edge_extraction_task is not None
        assert isinstance(result._edge_extraction_task, asyncio.Task)
