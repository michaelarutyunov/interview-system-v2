"""Tests for synthetic service."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.services.synthetic_service import (
    SyntheticService,
    get_synthetic_service,
)
from src.llm.client import LLMResponse


class TestSyntheticService:
    """Tests for SyntheticService."""

    def test_init_with_default_params(self):
        """Service initializes with default parameters."""
        with patch("src.services.synthetic_service.get_llm_client") as mock_client:
            mock_client.return_value = MagicMock()
            service = SyntheticService()

            assert service.llm_client is not None
            assert service.deflection_chance == 0.2

    def test_init_with_custom_params(self):
        """Service accepts custom parameters."""
        mock_llm = MagicMock()
        service = SyntheticService(
            llm_client=mock_llm,
            deflection_chance=0.5,
        )

        assert service.llm_client == mock_llm
        assert service.deflection_chance == 0.5

    @pytest.mark.asyncio
    async def test_generate_response_success(self):
        """generate_response returns synthetic response."""
        mock_llm = AsyncMock()
        mock_llm.complete.return_value = LLMResponse(
            content="I really like the creamy texture because it feels satisfying.",
            model="claude-sonnet-4-20250514",
            usage={"input_tokens": 100, "output_tokens": 20},
            latency_ms=150.0,
        )

        service = SyntheticService(llm_client=mock_llm)

        result = await service.generate_response(
            question="Why is creamy texture important to you?",
            session_id="test-session",
            persona="health_conscious",
        )

        assert (
            result["response"]
            == "I really like the creamy texture because it feels satisfying."
        )
        assert result["persona"] == "health_conscious"
        assert "Health-Conscious" in result["persona_name"]
        assert result["question"] == "Why is creamy texture important to you?"
        assert result["latency_ms"] == 150.0

    @pytest.mark.asyncio
    async def test_generate_response_with_graph_state(self):
        """generate_response uses graph state for context."""
        mock_llm = AsyncMock()
        mock_llm.complete.return_value = LLMResponse(
            content="Yes, that's important to me.",
            model="claude-sonnet-4-20250514",
            usage={"input_tokens": 80, "output_tokens": 10},
            latency_ms=100.0,
        )

        service = SyntheticService(llm_client=mock_llm)

        # Mock graph state with recent concepts
        graph_state = MagicMock()
        graph_state.recent_nodes = [
            MagicMock(label="creamy texture"),
            MagicMock(label="plant-based"),
        ]

        result = await service.generate_response(
            question="Does sustainability matter?",
            session_id="test-session",
            persona="sustainability_minded",
            graph_state=graph_state,
        )

        # Verify prompt included previous concepts
        call_args = mock_llm.complete.call_args
        prompt = call_args.kwargs["prompt"]
        assert "creamy texture" in prompt
        assert result["response"] == "Yes, that's important to me."

    @pytest.mark.asyncio
    async def test_generate_response_invalid_persona_raises(self):
        """generate_response raises for invalid persona."""
        mock_llm = AsyncMock()
        service = SyntheticService(llm_client=mock_llm)

        with pytest.raises(ValueError, match="Unknown persona"):
            await service.generate_response(
                question="Test question?",
                session_id="test-session",
                persona="invalid_persona",
            )

    @pytest.mark.asyncio
    async def test_generate_response_with_interview_context(self):
        """generate_response includes interview context."""
        mock_llm = AsyncMock()
        mock_llm.complete.return_value = LLMResponse(
            content="I think it's great.",
            model="claude-sonnet-4-20250514",
            usage={"input_tokens": 90, "output_tokens": 15},
            latency_ms=120.0,
        )

        service = SyntheticService(llm_client=mock_llm)

        await service.generate_response(
            question="What do you think?",
            session_id="test-session",
            interview_context={
                "product_name": "Oat Milk",
                "turn_number": 5,
                "coverage_achieved": 0.6,
            },
        )

        # Verify context was included
        call_args = mock_llm.complete.call_args
        prompt = call_args.kwargs["prompt"]
        assert "Oat Milk" in prompt
        assert "turn 5" in prompt

    @pytest.mark.asyncio
    async def test_generate_multi_response(self):
        """generate_multi_response creates responses for multiple personas."""
        mock_llm = AsyncMock()
        mock_llm.complete.return_value = LLMResponse(
            content="It's important because...",
            model="claude-sonnet-4-20250514",
            usage={"input_tokens": 100, "output_tokens": 20},
            latency_ms=150.0,
        )

        service = SyntheticService(llm_client=mock_llm)

        responses = await service.generate_multi_response(
            question="Why does quality matter?",
            session_id="test-session",
            personas=["health_conscious", "price_sensitive"],
        )

        assert len(responses) == 2
        assert responses[0]["persona"] == "health_conscious"
        assert responses[1]["persona"] == "price_sensitive"

    @pytest.mark.asyncio
    async def test_generate_interview_sequence(self):
        """generate_interview_sequence creates full interview."""
        mock_llm = AsyncMock()
        mock_llm.complete.return_value = LLMResponse(
            content="That's a good question.",
            model="claude-sonnet-4-20250514",
            usage={"input_tokens": 100, "output_tokens": 20},
            latency_ms=150.0,
        )

        service = SyntheticService(llm_client=mock_llm)

        questions = [
            "What comes to mind?",
            "Why is that important?",
            "What else matters?",
        ]

        responses = await service.generate_interview_sequence(
            session_id="test-session",
            questions=questions,
            persona="quality_focused",
            product_name="Oat Milk",
        )

        assert len(responses) == 3
        assert responses[0]["question"] == questions[0]
        assert responses[1]["question"] == questions[1]
        assert responses[2]["question"] == questions[2]
        assert all(r["persona"] == "quality_focused" for r in responses)

    def test_extract_previous_concepts_from_graph_state(self):
        """_extract_previous_concepts extracts labels from nodes."""
        service = SyntheticService()

        graph_state = MagicMock()
        graph_state.recent_nodes = [
            MagicMock(label="creamy texture"),
            MagicMock(label="plant-based"),
            MagicMock(label="satisfying"),
        ]

        concepts = service._extract_previous_concepts(graph_state)

        assert concepts == ["creamy texture", "plant-based", "satisfying"]

    def test_extract_previous_concepts_none(self):
        """_extract_previous_concepts returns empty list for None."""
        service = SyntheticService()

        concepts = service._extract_previous_concepts(None)

        assert concepts == []


class TestGetSyntheticService:
    """Tests for get_synthetic_service factory."""

    def test_returns_synthetic_service(self):
        """Factory returns SyntheticService instance."""
        with patch("src.services.synthetic_service.get_llm_client"):
            service = get_synthetic_service()

            assert isinstance(service, SyntheticService)

    def test_passes_llm_client(self):
        """Factory passes LLM client to service."""
        mock_llm = MagicMock()

        with patch("src.services.synthetic_service.get_llm_client"):
            service = get_synthetic_service(llm_client=mock_llm)

            assert service.llm_client == mock_llm
