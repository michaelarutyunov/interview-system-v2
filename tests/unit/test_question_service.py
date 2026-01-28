"""Tests for question service."""

import pytest
from unittest.mock import AsyncMock

from src.services.question_service import QuestionService
from src.llm.client import LLMResponse
from src.domain.models.knowledge_graph import (
    KGNode,
    GraphState,
    DepthMetrics,
    CoverageState,
)


@pytest.fixture
def mock_llm():
    """Create mock LLM client."""
    mock = AsyncMock()
    return mock


@pytest.fixture
def service(mock_llm):
    """Create question service with mock LLM."""
    return QuestionService(llm_client=mock_llm)


@pytest.fixture
def sample_graph_state():
    """Create sample graph state."""
    return GraphState(
        node_count=5,
        edge_count=3,
        nodes_by_type={"attribute": 2, "functional_consequence": 3},
        depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.5, depth_by_element={}),
        coverage_state=CoverageState(),
    )


@pytest.fixture
def sample_nodes():
    """Create sample recent nodes."""
    return [
        KGNode(id="n1", session_id="s1", label="creamy texture", node_type="attribute"),
        KGNode(
            id="n2",
            session_id="s1",
            label="satisfying",
            node_type="functional_consequence",
        ),
    ]


class TestGenerateQuestion:
    """Tests for generate_question."""

    @pytest.mark.asyncio
    async def test_returns_question(self, service, mock_llm):
        """generate_question returns formatted question."""
        mock_llm.complete.return_value = LLMResponse(
            content="Why is that important to you?",
            model="test",
            latency_ms=100,
        )

        question = await service.generate_question(
            focus_concept="creamy texture",
        )

        assert question == "Why is that important to you?"

    @pytest.mark.asyncio
    async def test_uses_default_strategy(self, service, mock_llm):
        """Uses default strategy when not specified."""
        mock_llm.complete.return_value = LLMResponse(
            content="Test question?",
            model="test",
        )

        await service.generate_question(focus_concept="test")

        # Check that deepen strategy was used in system prompt
        call_args = mock_llm.complete.call_args
        assert "Deepen" in call_args.kwargs["system"]

    @pytest.mark.asyncio
    async def test_includes_context(
        self, service, mock_llm, sample_graph_state, sample_nodes
    ):
        """Includes graph context in prompt."""
        mock_llm.complete.return_value = LLMResponse(
            content="Follow-up question?",
            model="test",
        )

        await service.generate_question(
            focus_concept="texture",
            graph_state=sample_graph_state,
            recent_nodes=sample_nodes,
        )

        call_args = mock_llm.complete.call_args
        prompt = call_args.kwargs["prompt"]

        # Should include graph summary
        assert "concepts" in prompt.lower() or "depth" in prompt.lower()

    @pytest.mark.asyncio
    async def test_includes_utterances(self, service, mock_llm):
        """Includes recent utterances in prompt."""
        mock_llm.complete.return_value = LLMResponse(
            content="Question?",
            model="test",
        )

        utterances = [
            {"speaker": "system", "text": "What do you think?"},
            {"speaker": "user", "text": "I love the taste"},
        ]

        await service.generate_question(
            focus_concept="taste",
            recent_utterances=utterances,
        )

        call_args = mock_llm.complete.call_args
        prompt = call_args.kwargs["prompt"]

        assert "I love the taste" in prompt

    @pytest.mark.asyncio
    async def test_formats_question(self, service, mock_llm):
        """Formats question output."""
        mock_llm.complete.return_value = LLMResponse(
            content='"Why is that important"',  # With quotes, no ?
            model="test",
        )

        question = await service.generate_question(focus_concept="test")

        assert not question.startswith('"')
        assert question.endswith("?")

    @pytest.mark.asyncio
    async def test_raises_on_llm_error(self, service, mock_llm):
        """Raises RuntimeError on LLM failure."""
        mock_llm.complete.side_effect = Exception("API error")

        with pytest.raises(RuntimeError, match="Question generation failed"):
            await service.generate_question(focus_concept="test")


class TestGenerateOpeningQuestion:
    """Tests for generate_opening_question."""

    @pytest.mark.asyncio
    async def test_returns_opening(self, service, mock_llm):
        """generate_opening_question returns formatted question."""
        mock_llm.complete.return_value = LLMResponse(
            content="What comes to mind when you think about Oat Milk?",
            model="test",
        )

        question = await service.generate_opening_question(
            concept_name="Oat Milk",
        )

        assert "Oat Milk" in question or len(question) > 10

    @pytest.mark.asyncio
    async def test_includes_description(self, service, mock_llm):
        """Includes description in prompt when provided."""
        mock_llm.complete.return_value = LLMResponse(
            content="Opening question?",
            model="test",
        )

        await service.generate_opening_question(
            concept_name="Oat Milk",
            concept_description="Plant-based milk alternative",
        )

        call_args = mock_llm.complete.call_args
        prompt = call_args.kwargs["prompt"]

        assert "Plant-based" in prompt


class TestSelectFocusConcept:
    """Tests for select_focus_concept."""

    def test_returns_most_recent_for_deepen(
        self, service, sample_nodes, sample_graph_state
    ):
        """Returns most recent node for deepen strategy."""
        focus = service.select_focus_concept(
            recent_nodes=sample_nodes,
            graph_state=sample_graph_state,
            strategy="deepen",
        )

        assert focus == "creamy texture"

    def test_returns_fallback_when_empty(self, service, sample_graph_state):
        """Returns fallback when no recent nodes."""
        focus = service.select_focus_concept(
            recent_nodes=[],
            graph_state=sample_graph_state,
        )

        assert focus == "the topic"


class TestFallbackQuestion:
    """Tests for fallback question."""

    @pytest.mark.asyncio
    async def test_generates_simple_question(self, service):
        """Fallback generates simple laddering question."""
        question = await service.generate_fallback_question("texture")

        assert "texture" in question
        assert "important" in question.lower()
