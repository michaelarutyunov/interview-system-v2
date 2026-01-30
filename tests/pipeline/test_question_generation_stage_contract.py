"""Tests for QuestionGenerationStage contract integration (ADR-010).

RED Phase: Write failing tests first.
"""

import pytest
from unittest.mock import AsyncMock

from src.services.turn_pipeline.stages.question_generation_stage import (
    QuestionGenerationStage,
)
from src.services.turn_pipeline.context import PipelineContext
from src.domain.models.knowledge_graph import GraphState, DepthMetrics
from src.domain.models.pipeline_contracts import (
    ContextLoadingOutput,
    StateComputationOutput,
    ContinuationOutput,
    StrategySelectionOutput,
)
from datetime import datetime, timezone


class TestQuestionGenerationStageContract:
    """Tests for QuestionGenerationStage generating questions."""

    @pytest.fixture
    def context(self):
        """Create a test pipeline context ready for question generation."""
        ctx = PipelineContext(
            session_id="test-session",
            user_input="I like oat milk",
        )

        # Set ContextLoadingOutput
        graph_state = GraphState(
            node_count=5,
            edge_count=3,
            depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.0),
            current_phase="exploratory",
            turn_count=1,
        )
        ctx.context_loading_output = ContextLoadingOutput(
            methodology="means_end_chain",
            concept_id="oat_milk",
            concept_name="Oat Milk",
            turn_number=1,
            mode="exploratory",
            max_turns=10,
            recent_utterances=[
                {"speaker": "assistant", "text": "What do you think about oat milk?"},
                {"speaker": "user", "text": "I like oat milk"},
            ],
            strategy_history=[],
            graph_state=graph_state,
            recent_nodes=[],
        )

        # Set StateComputationOutput
        ctx.state_computation_output = StateComputationOutput(
            graph_state=graph_state,
            recent_nodes=[],
            computed_at=datetime.now(timezone.utc),
        )

        # Set ContinuationOutput
        ctx.continuation_output = ContinuationOutput(
            should_continue=True,
            focus_concept="oat milk",
            turns_remaining=9,
        )

        # Set StrategySelectionOutput
        ctx.strategy_selection_output = StrategySelectionOutput(
            strategy="deepen",
            focus={"focus_type": "concept", "focus_description": "oat milk"},
        )

        return ctx

    @pytest.fixture
    def llm_service(self):
        """Create a mock LLM service."""
        mock_service = AsyncMock()
        mock_service.generate_question = AsyncMock(
            return_value="Tell me more about why you like oat milk."
        )
        return mock_service

    @pytest.mark.asyncio
    async def test_generates_question_when_continuing(self, context, llm_service):
        """Should generate question when should_continue is True."""
        stage = QuestionGenerationStage(llm_service)

        result_context = await stage.process(context)

        # Verify question was generated
        assert result_context.next_question != ""
        assert (
            "oat milk" in result_context.next_question.lower()
            or "why you like" in result_context.next_question.lower()
        )

    @pytest.mark.asyncio
    async def test_generates_closing_message_when_stopping(self, llm_service):
        """Should generate closing message when should_continue is False."""
        ctx = PipelineContext(
            session_id="test-session",
            user_input="I like oat milk",
        )

        # Minimal context for stopping
        graph_state = GraphState(
            node_count=0,
            edge_count=0,
            depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0),
            current_phase="exploratory",
            turn_count=10,
        )
        ctx.context_loading_output = ContextLoadingOutput(
            methodology="means_end_chain",
            concept_id="oat_milk",
            concept_name="Oat Milk",
            turn_number=10,
            mode="exploratory",
            max_turns=10,
            recent_utterances=[],
            strategy_history=[],
            graph_state=graph_state,
            recent_nodes=[],
        )
        ctx.state_computation_output = StateComputationOutput(
            graph_state=graph_state,
            recent_nodes=[],
            computed_at=datetime.now(timezone.utc),
        )
        ctx.continuation_output = ContinuationOutput(
            should_continue=False,
            focus_concept="",
            turns_remaining=0,
        )
        ctx.strategy_selection_output = StrategySelectionOutput(
            strategy="closing",
            focus=None,
        )

        stage = QuestionGenerationStage(llm_service)
        result_context = await stage.process(ctx)

        # Verify some message was generated (closing message)
        assert result_context.next_question != ""

    @pytest.mark.asyncio
    async def test_passes_correct_context_to_llm(self, context, llm_service):
        """Should pass correct context to LLM service."""
        stage = QuestionGenerationStage(llm_service)

        await stage.process(context)

        # Verify LLM was called with context
        llm_service.generate_question.assert_called_once()
        call_args = llm_service.generate_question.call_args

        # Verify key context parameters
        assert "recent_utterances" in call_args.kwargs
        assert "graph_state" in call_args.kwargs
        assert "strategy" in call_args.kwargs
