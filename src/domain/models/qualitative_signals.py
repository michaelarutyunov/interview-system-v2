"""
Qualitative signal models for LLM-based signal extraction.

These models represent semantic signals extracted from conversation history
that provide deeper insight into respondent engagement, reasoning quality,
and knowledge state than rule-based heuristics alone.

ADR-006: Two-tier scoring - Layer 3 of signal architecture.
ADR-010 Phase 2: Converted to Pydantic for type safety and added metadata fields.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class UncertaintyType(str, Enum):
    """Types of uncertainty expressed in responses."""

    KNOWLEDGE_GAP = "knowledge_gap"  # "I don't know enough about this"
    CONCEPTUAL_CLARITY = "conceptual_clarity"  # "I'm not sure what you mean"
    CONFIDENCE_QUALIFICATION = "confidence_qualification"  # "I think", "probably"
    EPISTEMIC_HUMILITY = "epistemic_humility"  # "I could be wrong", honest uncertainty
    APATHY = "apathy"  # "I don't know/care", disengagement


class ReasoningQuality(str, Enum):
    """Quality of reasoning exhibited in responses."""

    CAUSAL = "causal"  # Clear cause-effect reasoning
    COUNTERFACTUAL = "counterfactual"  # "What if" thinking, alternatives
    ASSOCIATIVE = "associative"  # Loose connections, word associations
    REACTIVE = "reactive"  # Simple responses to questions
    METACOGNITIVE = "metacognitive"  # Thinking about thinking


class EmotionalIntensity(str, Enum):
    """Emotional intensity levels."""

    HIGH_POSITIVE = "high_positive"  # Enthusiasm, excitement, "love", "amazing"
    MODERATE_POSITIVE = "moderate_positive"  # Interest, engagement
    NEUTRAL = "neutral"  # Factual, calm
    MODERATE_NEGATIVE = "moderate_negative"  # Hesitation, discomfort
    HIGH_NEGATIVE = "high_negative"  # Frustration, hostility


class UncertaintySignal(BaseModel):
    """Signal capturing type and depth of uncertainty in recent responses.

    Distinguishes between productive uncertainty (curiosity, conceptual clarity)
    and terminal uncertainty (knowledge gaps, apathy).

    ADR-010 Phase 2: Added confidence field for standardization.
    """

    uncertainty_type: UncertaintyType
    confidence: float = Field(
        ge=0.0, le=1.0, description="LLM confidence in this detection"
    )
    severity: float = Field(ge=0.0, le=1.0, description="0-1 impact score")
    examples: List[str] = Field(
        default_factory=list, description="Quotes that led to this"
    )
    reasoning: str = Field(
        default="", description="LLM's reasoning for this classification"
    )


class ReasoningSignal(BaseModel):
    """Signal capturing the quality of reasoning in recent responses.

    Helps assess whether the respondent is engaging in deep causal reasoning
    or providing surface-level associations.

    ADR-010 Phase 2: Added confidence field for standardization.
    """

    reasoning_quality: ReasoningQuality
    confidence: float = Field(ge=0.0, le=1.0, description="LLM confidence score")
    depth_score: float = Field(
        ge=0.0, le=1.0, description="0-1, how deep the reasoning goes"
    )
    has_examples: bool = Field(description="Uses concrete examples")
    has_abstractions: bool = Field(description="Uses abstract principles")
    examples: List[str] = Field(default_factory=list, description="Example quotes")
    reasoning: str = Field(default="", description="LLM's reasoning")


class EmotionalSignal(BaseModel):
    """Signal capturing emotional engagement and intensity.

    Helps distinguish between genuine interest and polite participation.

    ADR-010 Phase 2: Added confidence field for standardization.
    """

    intensity: EmotionalIntensity
    confidence: float = Field(ge=0.0, le=1.0, description="LLM confidence score")
    trajectory: str = Field(
        description="emotional trajectory: rising, falling, stable, volatile"
    )
    markers: List[str] = Field(
        default_factory=list, description="Emotional markers detected"
    )
    reasoning: str = Field(default="", description="LLM's reasoning")


class ContradictionSignal(BaseModel):
    """Signal detecting contradictions or stance shifts.

    Identifies when current responses contradict earlier statements,
    which may indicate: exploring new perspectives, genuine confusion,
    or interview fatigue.
    """

    has_contradiction: bool
    contradiction_type: Optional[str] = Field(
        default=None,
        description="Type of contradiction: stance reversal, inconsistent detail, etc.",
    )
    earlier_statement: str = Field(default="", description="The contradicted statement")
    current_statement: str = Field(
        default="", description="The contradicting statement"
    )
    confidence: float = Field(ge=0.0, le=1.0, default=0.0, description="LLM confidence")
    reasoning: str = Field(default="", description="LLM's reasoning")


class KnowledgeCeilingSignal(BaseModel):
    """Signal distinguishing types of "don't know" responses.

    Terminal: "I don't know and don't have more to say"
    Exploratory: "I don't know, but I'm curious about..."
    Transitional: "I don't know about X, but I do know about Y"
    """

    is_terminal: bool = Field(description="True if this is a hard stop")
    response_type: str = Field(description='"terminal", "exploratory", "transitional"')
    has_curiosity: bool = Field(description="Shows interest despite knowledge gap")
    redirection_available: bool = Field(description="Can pivot to related topic")
    confidence: float = Field(ge=0.0, le=1.0, default=0.0, description="LLM confidence")
    reasoning: str = Field(default="", description="LLM's reasoning")


class ConceptDepthSignal(BaseModel):
    """Signal assessing abstraction level of concepts discussed.

    Helps determine whether to deepen (more abstract) or broaden
    (more concrete) exploration.
    """

    abstraction_level: float = Field(
        ge=0.0, le=1.0, description="0=concrete, 1=abstract"
    )
    has_concrete_examples: bool = Field(description="Uses concrete examples")
    has_abstract_principles: bool = Field(description="Uses abstract principles")
    suggestion: str = Field(description="Strategy suggestion: deepen, broaden, stay")
    confidence: float = Field(ge=0.0, le=1.0, default=0.0, description="LLM confidence")
    reasoning: str = Field(default="", description="LLM's reasoning")


class QualitativeSignalSet(BaseModel):
    """Complete set of qualitative signals for a conversation turn.

    Extracted via LLM analysis of recent conversation history.
    Designed to be consumed by Tier 1/Tier 2 scorers for more nuanced
    decision-making than rule-based heuristics alone.

    ADR-010 Phase 2: Converted to Pydantic and added metadata fields for
    traceability and signal provenance tracking.
    """

    # Required signals
    uncertainty: Optional[UncertaintySignal] = None
    reasoning: Optional[ReasoningSignal] = None
    emotional: Optional[EmotionalSignal] = None
    contradiction: Optional[ContradictionSignal] = None
    knowledge_ceiling: Optional[KnowledgeCeilingSignal] = None
    concept_depth: Optional[ConceptDepthSignal] = None

    # Metadata (ADR-010 Phase 2: Enhanced for traceability)
    turn_number: int = Field(
        default=0, description="Turn number when signals were extracted"
    )
    source_utterance_id: str = Field(
        default="unknown",
        description="Source utterance ID for traceability (ADR-010 Phase 2)",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When signals were generated (ADR-010 Phase 2)",
    )
    llm_model: str = Field(
        default="unknown", description="LLM model used (e.g., moonshot-v1-8k)"
    )
    prompt_version: str = Field(
        default="unknown", description="Prompt version used (e.g., v2.1)"
    )
    extraction_latency_ms: int = Field(
        default=0, description="Signal extraction latency in ms"
    )
    extraction_errors: List[str] = Field(
        default_factory=list, description="Any errors during extraction"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/debugging."""
        return {
            "uncertainty": self.uncertainty.model_dump() if self.uncertainty else None,
            "reasoning": self.reasoning.model_dump() if self.reasoning else None,
            "emotional": self.emotional.model_dump() if self.emotional else None,
            "contradiction": self.contradiction.model_dump()
            if self.contradiction
            else None,
            "knowledge_ceiling": (
                self.knowledge_ceiling.model_dump() if self.knowledge_ceiling else None
            ),
            "concept_depth": self.concept_depth.model_dump()
            if self.concept_depth
            else None,
            # Metadata
            "turn_number": self.turn_number,
            "source_utterance_id": self.source_utterance_id,
            "generated_at": self.generated_at.isoformat(),
            "llm_model": self.llm_model,
            "prompt_version": self.prompt_version,
            "extraction_latency_ms": self.extraction_latency_ms,
            "extraction_errors": self.extraction_errors,
        }
