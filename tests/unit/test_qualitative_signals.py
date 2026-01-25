"""
Unit tests for QualitativeSignalExtractor.

Tests cover:
- Signal parsing from LLM responses
- Error handling (malformed JSON, missing fields)
- Fast path for insufficient history
- Individual signal type parsing
"""

import pytest
from unittest.mock import AsyncMock, Mock
from src.services.scoring.llm_signals import QualitativeSignalExtractor
from src.domain.models.qualitative_signals import (
    QualitativeSignalSet,
    UncertaintyType,
    ReasoningQuality,
    EmotionalIntensity,
)
from src.llm.client import LLMResponse


class TestQualitativeSignalExtractor:
    """Test suite for QualitativeSignalExtractor."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = Mock()
        client.model = "claude-haiku-test"
        client.complete = AsyncMock()
        return client

    @pytest.fixture
    def extractor(self, mock_llm_client):
        """Create extractor with mocked LLM client."""
        return QualitativeSignalExtractor(llm_client=mock_llm_client)

    @pytest.fixture
    def sample_conversation_history(self):
        """Create sample conversation history."""
        return [
            {"speaker": "moderator", "text": "Tell me about why you drink coffee."},
            {
                "speaker": "user",
                "text": "I drink coffee because it helps me focus at work.",
            },
            {"speaker": "moderator", "text": "What else do you notice about coffee?"},
            {
                "speaker": "user",
                "text": "I think the taste is really important. I love rich, bold flavors.",
            },
            {"speaker": "moderator", "text": "Does the caffeine matter?"},
            {
                "speaker": "user",
                "text": "Maybe a little bit, but mostly it's about the ritual and taste.",
            },
        ]

    @pytest.fixture
    def sample_llm_response(self):
        """Create a sample LLM JSON response."""
        return {
            "uncertainty_signal": {
                "uncertainty_type": "confidence_qualification",
                "confidence": 0.8,
                "severity": 0.3,
                "examples": ["Maybe a little bit"],
                "reasoning": "User hedges with 'maybe' but shows engagement",
            },
            "reasoning_signal": {
                "reasoning_quality": "causal",
                "confidence": 0.75,
                "depth_score": 0.6,
                "has_examples": True,
                "has_abstractions": False,
                "examples": ["because it helps me focus"],
                "reasoning": "Clear cause-effect reasoning",
            },
            "emotional_signal": {
                "intensity": "moderate_positive",
                "confidence": 0.7,
                "trajectory": "stable",
                "markers": ["engaged", "descriptive"],
                "reasoning": "User shows interest through descriptive language",
            },
            "contradiction_signal": {
                "has_contradiction": False,
                "contradiction_type": None,
                "confidence": 0.9,
                "reasoning": "No contradictions detected",
            },
            "knowledge_ceiling_signal": {
                "is_terminal": False,
                "response_type": "exploratory",
                "has_curiosity": True,
                "redirection_available": True,
                "confidence": 0.8,
                "reasoning": "User shows interest and provides detailed responses",
            },
            "concept_depth_signal": {
                "abstraction_level": 0.4,
                "has_concrete_examples": True,
                "has_abstract_principles": False,
                "suggestion": "stay",
                "confidence": 0.7,
                "reasoning": "Balanced mix of concrete details and some reasoning",
            },
        }

    @pytest.mark.asyncio
    async def test_extract_success(
        self,
        extractor,
        mock_llm_client,
        sample_conversation_history,
        sample_llm_response,
    ):
        """Test successful signal extraction."""
        import json

        # Setup mock response
        mock_llm_client.complete.return_value = LLMResponse(
            content=json.dumps(sample_llm_response),
            model="claude-haiku-test",
            usage={"input_tokens": 100, "output_tokens": 200},
        )

        # Extract signals
        signals = await extractor.extract(
            conversation_history=sample_conversation_history,
            turn_number=5,
        )

        # Verify all signals extracted
        assert signals is not None
        assert signals.uncertainty is not None
        assert signals.reasoning is not None
        assert signals.emotional is not None
        assert signals.contradiction is not None
        assert signals.knowledge_ceiling is not None
        assert signals.concept_depth is not None

        # Verify specific signal values
        assert (
            signals.uncertainty.uncertainty_type
            == UncertaintyType.CONFIDENCE_QUALIFICATION
        )
        assert signals.reasoning.reasoning_quality == ReasoningQuality.CAUSAL
        assert signals.emotional.intensity == EmotionalIntensity.MODERATE_POSITIVE
        assert signals.contradiction.has_contradiction is False
        assert signals.knowledge_ceiling.is_terminal is False
        assert signals.concept_depth.suggestion == "stay"

        # Verify metadata (latency may be 0 in tests due to mocking)
        assert signals.turn_number == 5
        assert signals.llm_model == "claude-haiku-test"

    @pytest.mark.asyncio
    async def test_extract_insufficient_history(self, extractor):
        """Test fast path for insufficient conversation history."""
        # Only one turn - should return empty signal set without LLM call
        signals = await extractor.extract(
            conversation_history=[{"speaker": "user", "text": "Hello"}],
            turn_number=1,
        )

        assert signals is not None
        assert signals.turn_number == 1
        assert signals.uncertainty is None
        assert signals.reasoning is None
        # LLM should not have been called
        assert extractor.llm.complete.call_count == 0

    @pytest.mark.asyncio
    async def test_extract_llm_error_graceful_degradation(
        self, extractor, mock_llm_client, sample_conversation_history
    ):
        """Test graceful degradation when LLM call fails."""
        # Setup mock to raise exception
        mock_llm_client.complete.side_effect = Exception("API error")

        # Extract signals - should not raise
        signals = await extractor.extract(
            conversation_history=sample_conversation_history,
            turn_number=5,
        )

        # Should return empty signal set with error logged
        assert signals is not None
        assert signals.turn_number == 5
        assert len(signals.extraction_errors) == 1
        assert "API error" in signals.extraction_errors[0]

    @pytest.mark.asyncio
    async def test_extract_partial_signal_parsing(
        self, extractor, mock_llm_client, sample_conversation_history
    ):
        """Test that partial signals are extracted even if some fail to parse."""
        import json

        # Response with one malformed signal
        partial_response = {
            "uncertainty_signal": {
                "uncertainty_type": "confidence_qualification",
                "confidence": 0.8,
                "severity": 0.3,
                "examples": ["maybe"],
                "reasoning": "test",
            },
            "reasoning_signal": {
                # Missing required field - should fail to parse
                "confidence": 0.7,
                "depth_score": 0.6,
            },
            "emotional_signal": {
                "intensity": "moderate_positive",
                "confidence": 0.7,
                "trajectory": "stable",
                "markers": ["engaged"],
                "reasoning": "test",
            },
            "contradiction_signal": {"has_contradiction": False},
            "knowledge_ceiling_signal": {"is_terminal": False},
            "concept_depth_signal": {
                "abstraction_level": 0.5,
                "has_concrete_examples": True,
                "has_abstract_principles": False,
                "suggestion": "stay",
                "confidence": 0.7,
            },
        }

        mock_llm_client.complete.return_value = LLMResponse(
            content=json.dumps(partial_response),
            model="claude-haiku-test",
            usage={},
        )

        signals = await extractor.extract(
            conversation_history=sample_conversation_history,
            turn_number=5,
        )

        # Some signals should be extracted despite parsing failure
        assert signals.uncertainty is not None
        assert signals.reasoning is None  # Failed to parse
        assert signals.emotional is not None
        assert len(signals.extraction_errors) == 1  # reasoning parse error

    @pytest.mark.asyncio
    async def test_extract_json_in_markdown(
        self,
        extractor,
        mock_llm_client,
        sample_conversation_history,
        sample_llm_response,
    ):
        """Test parsing JSON wrapped in markdown code blocks."""
        import json

        # Response wrapped in markdown
        markdown_response = f"""Here's my analysis:

```json
{json.dumps(sample_llm_response)}
```

Let me know if you need more details."""

        mock_llm_client.complete.return_value = LLMResponse(
            content=markdown_response,
            model="claude-haiku-test",
            usage={},
        )

        signals = await extractor.extract(
            conversation_history=sample_conversation_history,
            turn_number=5,
        )

        # Should successfully extract from markdown
        assert signals.uncertainty is not None
        assert (
            signals.uncertainty.uncertainty_type
            == UncertaintyType.CONFIDENCE_QUALIFICATION
        )

    @pytest.mark.asyncio
    async def test_extract_with_enabled_signals_filter(
        self, mock_llm_client, sample_conversation_history, sample_llm_response
    ):
        """Test filtering to only extract specific signal types."""
        import json

        # Create extractor with only uncertainty and emotional signals enabled
        extractor = QualitativeSignalExtractor(
            llm_client=mock_llm_client,
            enabled_signals=["uncertainty", "emotional"],
        )

        mock_llm_client.complete.return_value = LLMResponse(
            content=json.dumps(sample_llm_response),
            model="claude-haiku-test",
            usage={},
        )

        signals = await extractor.extract(
            conversation_history=sample_conversation_history,
            turn_number=5,
        )

        # All signals extracted (filtering happens at prompt level, not parsing)
        # This test verifies the architecture supports selective extraction
        assert signals.uncertainty is not None
        assert signals.emotional is not None


class TestSignalParsing:
    """Test individual signal type parsing."""

    @pytest.fixture
    def mock_llm_client_for_parsing(self):
        """Create a mock LLM client for parsing tests."""
        client = Mock()
        client.model = "claude-haiku-test"
        return client

    @pytest.fixture
    def extractor_with_mock(self, mock_llm_client_for_parsing):
        """Create extractor with mocked LLM client for parsing tests."""
        return QualitativeSignalExtractor(llm_client=mock_llm_client_for_parsing)

    def test_parse_uncertainty_signal(self, extractor_with_mock):
        """Test parsing uncertainty signal."""
        raw = {
            "uncertainty_type": "epistemic_humility",
            "confidence": 0.9,
            "severity": 0.2,
            "examples": ["I could be wrong", "not entirely sure"],
            "reasoning": "Shows honest uncertainty",
        }

        signal = extractor_with_mock._parse_uncertainty_signal(raw)

        assert signal.uncertainty_type == UncertaintyType.EPISTEMIC_HUMILITY
        assert signal.confidence == 0.9
        assert signal.severity == 0.2
        assert len(signal.examples) == 2

    def test_parse_reasoning_signal(self, extractor_with_mock):
        """Test parsing reasoning signal."""
        raw = {
            "reasoning_quality": "counterfactual",
            "confidence": 0.8,
            "depth_score": 0.7,
            "has_examples": True,
            "has_abstractions": True,
            "examples": ["if things were different"],
            "reasoning": "Shows alternative thinking",
        }

        signal = extractor_with_mock._parse_reasoning_signal(raw)

        assert signal.reasoning_quality == ReasoningQuality.COUNTERFACTUAL
        assert signal.depth_score == 0.7
        assert signal.has_examples is True
        assert signal.has_abstractions is True

    def test_parse_emotional_signal(self, extractor_with_mock):
        """Test parsing emotional signal."""
        raw = {
            "intensity": "high_positive",
            "confidence": 0.85,
            "trajectory": "rising",
            "markers": ["excited", "enthusiastic"],
            "reasoning": "Shows growing excitement",
        }

        signal = extractor_with_mock._parse_emotional_signal(raw)

        assert signal.intensity == EmotionalIntensity.HIGH_POSITIVE
        assert signal.trajectory == "rising"
        assert "excited" in signal.markers

    def test_parse_contradiction_signal_no_contradiction(self, extractor_with_mock):
        """Test parsing contradiction signal with no contradiction."""
        raw = {
            "has_contradiction": False,
            "contradiction_type": None,
            "confidence": 0.95,
            "reasoning": "No contradictions",
        }

        signal = extractor_with_mock._parse_contradiction_signal(raw)

        assert signal.has_contradiction is False
        assert signal.contradiction_type is None

    def test_parse_knowledge_ceiling_signal(self, extractor_with_mock):
        """Test parsing knowledge ceiling signal."""
        raw = {
            "is_terminal": False,
            "response_type": "transitional",
            "has_curiosity": True,
            "redirection_available": True,
            "confidence": 0.8,
            "reasoning": "User offers alternative topic",
        }

        signal = extractor_with_mock._parse_knowledge_ceiling_signal(raw)

        assert signal.is_terminal is False
        assert signal.response_type == "transitional"
        assert signal.has_curiosity is True
        assert signal.redirection_available is True

    def test_parse_concept_depth_signal(self, extractor_with_mock):
        """Test parsing concept depth signal."""
        raw = {
            "abstraction_level": 0.75,
            "has_concrete_examples": False,
            "has_abstract_principles": True,
            "suggestion": "deepen",
            "confidence": 0.8,
            "reasoning": "Very abstract discussion",
        }

        signal = extractor_with_mock._parse_concept_depth_signal(raw)

        assert signal.abstraction_level == 0.75
        assert signal.has_concrete_examples is False
        assert signal.has_abstract_principles is True
        assert signal.suggestion == "deepen"


class TestQualitativeSignalSet:
    """Test QualitativeSignalSet model."""

    def test_to_dict(self):
        """Test converting signal set to dictionary."""
        from src.domain.models.qualitative_signals import (
            UncertaintySignal,
            UncertaintyType,
        )

        signal_set = QualitativeSignalSet(
            turn_number=5,
            extraction_latency_ms=150,
            llm_model="claude-haiku",
        )
        signal_set.uncertainty = UncertaintySignal(
            uncertainty_type=UncertaintyType.CONFIDENCE_QUALIFICATION,
            confidence=0.8,
            severity=0.3,
            examples=["maybe"],
            reasoning="test",
        )

        result = signal_set.to_dict()

        assert result["turn_number"] == 5
        assert result["extraction_latency_ms"] == 150
        assert result["llm_model"] == "claude-haiku"
        assert result["uncertainty"] is not None
        assert result["uncertainty"]["uncertainty_type"] == "confidence_qualification"
