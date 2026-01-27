"""Tests for QuestionGenerationStage contract integration (ADR-010).

RED Phase: Write failing tests first.
"""

import pytest
from unittest.mock import AsyncMock

from src.services.turn_pipeline.stages.question_generation_stage import (
    QuestionGenerationStage,
)
from src.services.turn_pipeline.context import PipelineContext
from src.domain.models.knowledge_graph import GraphState, DepthMetrics, CoverageState


class TestQuestionGenerationStageContract:
    """Tests for QuestionGenerationStage generating questions."""

    @pytest.fixture
    def context(self):
        """Create a test pipeline context ready for question generation."""
        graph_state = GraphState(
            node_count=5,
            edge_count=3,
            depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.0),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=1,
        )

        return PipelineContext(
            session_id="test-session",
            user_input="I like oat milk",
            turn_number=1,
            max_turns=10,
            graph_state=graph_state,
            recent_utterances=[
                {"speaker": "assistant", "text": "What do you think about oat milk?"},
                {"speaker": "user", "text": "I like oat milk"},
            ],
            should_continue=True,
            strategy="deepen",
        )

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
        context = PipelineContext(
            session_id="test-session",
            user_input="I like oat milk",
            turn_number=10,
            max_turns=10,
            should_continue=False,
            strategy="closing",
        )

        stage = QuestionGenerationStage(llm_service)
        result_context = await stage.process(context)

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
