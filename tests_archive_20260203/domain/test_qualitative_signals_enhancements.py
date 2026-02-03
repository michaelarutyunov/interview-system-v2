"""Tests for enhanced QualitativeSignals models (ADR-010 Phase 2).

RED Phase: Write failing tests first.
Tests for new Pydantic models with timestamp and traceability fields.
"""

from datetime import datetime, timezone

from src.domain.models.qualitative_signals import (
    QualitativeSignalSet,
    UncertaintySignal,
    UncertaintyType,
    ReasoningSignal,
    ReasoningQuality,
    EmotionalSignal,
    EmotionalIntensity,
)


class TestQualitativeSignalEnhancements:
    """Tests for QualitativeSignals with new metadata fields."""

    def test_qualitative_signal_set_with_metadata(self):
        """Should create signal set with generation metadata."""
        signal_set = QualitativeSignalSet(
            turn_number=1,
            source_utterance_id="utter_123",
            generated_at=datetime.now(timezone.utc),
            llm_model="moonshot-v1-8k",
            prompt_version="v2.1",
            uncertainty=UncertaintySignal(
                uncertainty_type=UncertaintyType.KNOWLEDGE_GAP,
                confidence=0.9,
                severity=0.7,
                examples=["I don't know much about this"],
                reasoning="Clear knowledge gap expressed",
            ),
        )

        assert signal_set.turn_number == 1
        assert signal_set.source_utterance_id == "utter_123"
        assert signal_set.generated_at is not None
        assert signal_set.llm_model == "moonshot-v1-8k"
        assert signal_set.prompt_version == "v2.1"

    def test_uncertainty_signal_with_confidence(self):
        """Should create uncertainty signal with confidence score."""
        signal = UncertaintySignal(
            uncertainty_type=UncertaintyType.CONFIDENCE_QUALIFICATION,
            confidence=0.85,
            severity=0.3,
            examples=["I think it might be"],
            reasoning="User is qualifying their statement",
        )

        assert signal.confidence == 0.85
        assert 0.0 <= signal.severity <= 1.0

    def test_emotional_signal_with_confidence(self):
        """Should create emotional signal with confidence score."""
        signal = EmotionalSignal(
            intensity=EmotionalIntensity.HIGH_POSITIVE,
            confidence=0.9,
            trajectory="rising",
            markers=["enthusiastic", "excited"],
            reasoning="User shows enthusiasm",
        )

        assert signal.confidence == 0.9
        assert signal.intensity == EmotionalIntensity.HIGH_POSITIVE

    def test_all_signals_include_confidence(self):
        """All signal types should include confidence for standardization."""
        # UncertaintySignal
        uncertainty = UncertaintySignal(
            uncertainty_type=UncertaintyType.EPISTEMIC_HUMILITY,
            confidence=0.8,
            severity=0.2,
            examples=["I could be wrong"],
            reasoning="Honest uncertainty",
        )

        # ReasoningSignal
        reasoning = ReasoningSignal(
            reasoning_quality=ReasoningQuality.CAUSAL,
            confidence=0.75,
            depth_score=0.6,
            has_examples=True,
            has_abstractions=False,
            examples=["Because X leads to Y"],
            reasoning="Clear causal reasoning",
        )

        # EmotionalSignal
        emotional = EmotionalSignal(
            intensity=EmotionalIntensity.NEUTRAL,
            confidence=0.9,
            trajectory="stable",
            markers=[],
            reasoning="Calm, factual response",
        )

        # Verify all have confidence
        assert uncertainty.confidence == 0.8
        assert reasoning.confidence == 0.75
        assert emotional.confidence == 0.9

    def test_signal_set_serialization_with_metadata(self):
        """Should serialize to dict with all new fields."""
        signal_set = QualitativeSignalSet(
            turn_number=1,
            source_utterance_id="utter_123",
            generated_at=datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            llm_model="moonshot-v1-8k",
            prompt_version="v2.1",
            uncertainty=UncertaintySignal(
                uncertainty_type=UncertaintyType.KNOWLEDGE_GAP,
                confidence=0.9,
                severity=0.7,
                examples=[],
                reasoning="",
            ),
        )

        data = signal_set.to_dict()

        # Verify new fields are in dict
        assert data["turn_number"] == 1
        assert data["source_utterance_id"] == "utter_123"
        assert "generated_at" in data
        assert data["llm_model"] == "moonshot-v1-8k"
        assert data["prompt_version"] == "v2.1"
