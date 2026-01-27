"""Tests for ExtractionStage contract integration (ADR-010).

RED Phase: Write failing tests first.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.turn_pipeline.stages.extraction_stage import ExtractionStage
from src.services.turn_pipeline.context import PipelineContext


class TestExtractionStageContract:
    """Tests for ExtractionStage producing valid extraction results."""

    @pytest.fixture
    def context(self):
        """Create a test pipeline context."""
        return PipelineContext(
            session_id="test-session",
            user_input="I like oat milk",
            methodology="means_end_chain",
            concept_id="oat_milk_v2",
            concept_name="Oat Milk v2",
            turn_number=1,
            mode="coverage",
            max_turns=10,
            recent_utterances=[
                {"speaker": "assistant", "text": "What do you think about oat milk?"},
                {"speaker": "user", "text": "I like oat milk"},
            ],
        )

    @pytest.fixture
    def extraction_service(self):
        """Create a mock extraction service."""
        mock_service = MagicMock()

        # Mock extraction result with timestamp
        from datetime import datetime, timezone
        from src.domain.models.extraction import ExtractionResult

        mock_result = ExtractionResult(
            concepts=[],
            relationships=[],
            timestamp=datetime.now(timezone.utc),
        )

        mock_service.extract = AsyncMock(return_value=mock_result)
        mock_service.methodology = "means_end_chain"
        return mock_service

    @pytest.mark.asyncio
    async def test_produces_extraction_with_timestamp(
        self, context, extraction_service
    ):
        """Should produce extraction with timestamp for freshness tracking (ADR-010)."""
        stage = ExtractionStage(extraction_service)

        # Process the context
        result_context = await stage.process(context)

        # Verify extraction was produced
        assert result_context.extraction is not None
        # Verify extraction has timestamp (needed for freshness validation)
        assert hasattr(result_context.extraction, "timestamp")
        assert result_context.extraction.timestamp is not None

    @pytest.mark.asyncio
    async def test_calls_extraction_service(self, context, extraction_service):
        """Should call extraction service with correct parameters."""
        stage = ExtractionStage(extraction_service)

        await stage.process(context)

        # Verify service was called
        extraction_service.extract.assert_called_once()
        call_args = extraction_service.extract.call_args

        # Verify parameters
        assert call_args.kwargs.get("text") == "I like oat milk"
        assert "context" in call_args.kwargs
