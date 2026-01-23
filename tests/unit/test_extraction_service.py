"""Tests for extraction service."""

import pytest
from unittest.mock import AsyncMock

from src.services.extraction_service import ExtractionService
from src.domain.models.extraction import ExtractionResult
from src.llm.client import LLMResponse


@pytest.fixture
def mock_llm():
    """Create mock LLM client."""
    mock = AsyncMock()
    return mock


@pytest.fixture
def service(mock_llm):
    """Create extraction service with mock LLM."""
    return ExtractionService(llm_client=mock_llm)


class TestExtractionService:
    """Tests for ExtractionService."""

    def test_fast_extractability_too_short(self, service):
        """Short text is not extractable."""
        is_extractable, reason = service._fast_extractability_check("Hi")

        assert not is_extractable
        assert "short" in reason.lower()

    def test_fast_extractability_yes_no(self, service):
        """Yes/no responses are not extractable."""
        for response in ["yes", "no", "yeah", "okay"]:
            is_extractable, reason = service._fast_extractability_check(response)
            assert not is_extractable

    def test_fast_extractability_valid(self, service):
        """Substantive text is extractable."""
        text = "I really like the creamy texture because it's satisfying"
        is_extractable, reason = service._fast_extractability_check(text)

        assert is_extractable
        assert reason is None

    @pytest.mark.asyncio
    async def test_extract_returns_result(self, service, mock_llm):
        """extract() returns ExtractionResult."""
        mock_llm.complete.return_value = LLMResponse(
            content='{"concepts": [], "relationships": [], "discourse_markers": []}',
            model="test",
        )

        result = await service.extract("I like the taste")

        assert isinstance(result, ExtractionResult)
        assert result.is_extractable

    @pytest.mark.asyncio
    async def test_extract_parses_concepts(self, service, mock_llm):
        """extract() parses concepts from LLM response."""
        mock_llm.complete.return_value = LLMResponse(
            content="""{
                "concepts": [
                    {"text": "creamy texture", "node_type": "attribute", "confidence": 0.9}
                ],
                "relationships": [],
                "discourse_markers": []
            }""",
            model="test",
        )

        result = await service.extract("I love the creamy texture")

        assert len(result.concepts) == 1
        assert result.concepts[0].text == "creamy texture"
        assert result.concepts[0].node_type == "attribute"

    @pytest.mark.asyncio
    async def test_extract_parses_relationships(self, service, mock_llm):
        """extract() parses relationships from LLM response."""
        mock_llm.complete.return_value = LLMResponse(
            content="""{
                "concepts": [
                    {"text": "creamy", "node_type": "attribute"},
                    {"text": "satisfying", "node_type": "functional_consequence"}
                ],
                "relationships": [
                    {"source_text": "creamy", "target_text": "satisfying", "relationship_type": "leads_to"}
                ],
                "discourse_markers": ["because"]
            }""",
            model="test",
        )

        result = await service.extract("The creamy texture is satisfying")

        assert len(result.relationships) == 1
        assert result.relationships[0].source_text == "creamy"
        assert result.relationships[0].relationship_type == "leads_to"
        assert "because" in result.discourse_markers

    @pytest.mark.asyncio
    async def test_extract_skips_non_extractable(self, service, mock_llm):
        """extract() skips non-extractable text."""
        result = await service.extract("yes")

        assert not result.is_extractable
        assert result.concepts == []
        mock_llm.complete.assert_not_called()  # LLM not called

    @pytest.mark.asyncio
    async def test_extract_handles_llm_error(self, service, mock_llm):
        """extract() returns empty result on LLM error."""
        mock_llm.complete.side_effect = Exception("API error")

        result = await service.extract("I like the product a lot")

        assert result.is_extractable  # Still marked extractable
        assert result.concepts == []
        assert "LLM error" in result.extractability_reason

    @pytest.mark.asyncio
    async def test_extract_records_latency(self, service, mock_llm):
        """extract() records latency in milliseconds."""
        mock_llm.complete.return_value = LLMResponse(
            content='{"concepts": [], "relationships": [], "discourse_markers": []}',
            model="test",
        )

        result = await service.extract("I like the taste")

        assert result.latency_ms >= 0

    def test_parse_concepts_handles_invalid(self, service):
        """_parse_concepts handles invalid data gracefully."""
        raw = [
            {"text": "valid", "node_type": "attribute"},
            {"invalid": "data"},  # Missing required fields
            {"text": "", "node_type": "attribute"},  # Empty text
        ]

        concepts = service._parse_concepts(raw)

        assert len(concepts) == 1
        assert concepts[0].text == "valid"

    def test_parse_relationships_handles_invalid(self, service):
        """_parse_relationships handles invalid data gracefully."""
        raw = [
            {"source_text": "a", "target_text": "b", "relationship_type": "leads_to"},
            {"source_text": "", "target_text": "b"},  # Empty source
            {"source_text": "a", "target_text": ""},  # Empty target
        ]

        # Provide concept_types map
        concept_types = {"a": "attribute", "b": "functional_consequence"}

        relationships = service._parse_relationships(raw, concept_types)

        assert len(relationships) == 1
        assert relationships[0].source_text == "a"
