"""Qualitative signal domain models for LLM-based semantic analysis.

This module defines Pydantic models for LLM-extracted qualitative signals
that capture semantic patterns beyond rule-based heuristics. These signals
provide deeper insight into respondent engagement, reasoning quality,
emotional state, and knowledge boundaries.

Signal Categories:
    - Uncertainty: Type and depth of uncertainty (knowledge gaps vs curiosity)
    - Reasoning: Quality of cognitive processing (causal, associative, reactive)
    - Emotional: Engagement intensity and trajectory
    - Contradiction: Stance reversals or inconsistent statements
    - Knowledge Ceiling: Terminal vs exploratory "don't know" responses
    - Concept Depth: Abstraction level (concrete vs abstract)

Usage Pattern:
    1. Conversation history analyzed by LLM after each turn
    2. QualitativeSignalSet produced with multiple signal types
    3. Signals consumed by Tier 1/Tier 2 scorers for nuanced decisions
    4. More accurate strategy selection than graph metrics alone

Design Notes:
    - All signals include LLM confidence scores
    - Reasoning field explains LLM's interpretation
    - Examples field provides supporting quotes
    - Metadata (turn_number, source_utterance_id, model) for traceability
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class UncertaintyType(str, Enum):
    """Classification of uncertainty type expressed in user responses.

    Distinguishes between productive uncertainty (leads to exploration)
    and terminal uncertainty (indicates topic exhaustion).

    Values:
        - KNOWLEDGE_GAP: Acknowledged missing information, potential for learning
        - CONCEPTUAL_CLARITY: Confusion about meaning, needs clarification
        - CONFIDENCE_QUALIFICATION: Hedging language ("I think", "probably")
        - EPISTEMIC_HUMILITY: Honest uncertainty about complex topics
        - APATHY: Disengagement, lack of interest (terminal signal)

    Used by:
        - UncertaintySignal for classification
        - Strategy selection to detect knowledge boundaries
    """

    KNOWLEDGE_GAP = "knowledge_gap"  # "I don't know enough about this"
    CONCEPTUAL_CLARITY = "conceptual_clarity"  # "I'm not sure what you mean"
    CONFIDENCE_QUALIFICATION = "confidence_qualification"  # "I think", "probably"
    EPISTEMIC_HUMILITY = "epistemic_humility"  # "I could be wrong", honest uncertainty
    APATHY = "apathy"  # "I don't know/care", disengagement


class ReasoningQuality(str, Enum):
    """Classification of cognitive reasoning quality in responses.

    Categorizes the depth and structure of respondent's
    thought processes as revealed through conversation.

    Values:
        - CAUSAL: Clear cause-effect reasoning chains
        - COUNTERFACTUAL: "What if" thinking, considers alternatives
        - ASSOCIATIVE: Loose connections, word associations (shallow)
        - REACTIVE: Simple responses without elaboration
        - METACOGNITIVE: Thinking about thinking, self-reflection

    Used by:
        - ReasoningSignal for quality assessment
        - Depth detection and strategy selection
    """

    CAUSAL = "causal"  # Clear cause-effect reasoning
    COUNTERFACTUAL = "counterfactual"  # "What if" thinking, alternatives
    ASSOCIATIVE = "associative"  # Loose connections, word associations
    REACTIVE = "reactive"  # Simple responses to questions
    METACOGNITIVE = "metacognitive"  # Thinking about thinking


class EmotionalIntensity(str, Enum):
    """Classification of emotional engagement intensity.

    Tracks respondent's emotional state to distinguish genuine
    interest from polite participation.

    Values:
        - HIGH_POSITIVE: Enthusiasm, excitement ("love", "amazing")
        - MODERATE_POSITIVE: Interest, engagement, affirmation
        - NEUTRAL: Factual, calm, informational
        - MODERATE_NEGATIVE: Hesitation, discomfort, uncertainty
        - HIGH_NEGATIVE: Frustration, hostility, disengagement

    Used by:
        - EmotionalSignal for intensity classification
        - Engagement detection and rapport assessment
    """

    HIGH_POSITIVE = "high_positive"  # Enthusiasm, excitement, "love", "amazing"
    MODERATE_POSITIVE = "moderate_positive"  # Interest, engagement
    NEUTRAL = "neutral"  # Factual, calm
    MODERATE_NEGATIVE = "moderate_negative"  # Hesitation, discomfort
    HIGH_NEGATIVE = "high_negative"  # Frustration, hostility


class UncertaintySignal(BaseModel):
    """LLM-detected uncertainty signal with type and severity classification.

    Distinguishes between productive uncertainty (curiosity, conceptual
    clarity needs) and terminal uncertainty (knowledge gaps, apathy).

    Fields:
        - uncertainty_type: Category from UncertaintyType enum
        - confidence: LLM confidence in classification (0.0-1.0)
        - severity: Impact score for decision-making (0.0-1.0)
        - examples: Supporting quotes from conversation that led to detection
        - reasoning: LLM explanation for classification

    Strategy Implications:
        - APATHY/KNOWLEDGE_GAP: Consider closing or topic switch
        - CONCEPTUAL_CLARITY: Ask clarifying questions
        - EPISTEMIC_HUMILITY: Can deepen with appropriate scaffolding
    """

    uncertainty_type: UncertaintyType
    confidence: float = Field(ge=0.0, le=1.0, description="LLM confidence in this detection")
    severity: float = Field(ge=0.0, le=1.0, description="0-1 impact score")
    examples: List[str] = Field(default_factory=list, description="Quotes that led to this")
    reasoning: str = Field(default="", description="LLM's reasoning for this classification")


class ReasoningSignal(BaseModel):
    """Signal capturing the quality of reasoning in recent responses.

    Helps assess whether the respondent is engaging in deep causal reasoning
    or providing surface-level associations.
    """

    reasoning_quality: ReasoningQuality
    confidence: float = Field(ge=0.0, le=1.0, description="LLM confidence score")
    depth_score: float = Field(ge=0.0, le=1.0, description="0-1, how deep the reasoning goes")
    has_examples: bool = Field(description="Uses concrete examples")
    has_abstractions: bool = Field(description="Uses abstract principles")
    examples: List[str] = Field(default_factory=list, description="Example quotes")
    reasoning: str = Field(default="", description="LLM's reasoning")


class EmotionalSignal(BaseModel):
    """Signal capturing emotional engagement and intensity.

    Helps distinguish between genuine interest and polite participation.
    """

    intensity: EmotionalIntensity
    confidence: float = Field(ge=0.0, le=1.0, description="LLM confidence score")
    trajectory: str = Field(description="emotional trajectory: rising, falling, stable, volatile")
    markers: List[str] = Field(default_factory=list, description="Emotional markers detected")
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
    current_statement: str = Field(default="", description="The contradicting statement")
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

    abstraction_level: float = Field(ge=0.0, le=1.0, description="0=concrete, 1=abstract")
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
    """

    # Required signals
    uncertainty: Optional[UncertaintySignal] = None
    reasoning: Optional[ReasoningSignal] = None
    emotional: Optional[EmotionalSignal] = None
    contradiction: Optional[ContradictionSignal] = None
    knowledge_ceiling: Optional[KnowledgeCeilingSignal] = None
    concept_depth: Optional[ConceptDepthSignal] = None

    # Metadata
    turn_number: int = Field(default=0, description="Turn number when signals were extracted")
    source_utterance_id: str = Field(
        default="unknown",
        description="Source utterance ID for traceability",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When signals were generated",
    )
    llm_model: str = Field(default="unknown", description="LLM model used (e.g., moonshot-v1-8k)")
    prompt_version: str = Field(default="unknown", description="Prompt version used (e.g., v2.1)")
    extraction_latency_ms: int = Field(default=0, description="Signal extraction latency in ms")
    extraction_errors: List[str] = Field(
        default_factory=list, description="Any errors during extraction"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/debugging."""
        return {
            "uncertainty": self.uncertainty.model_dump() if self.uncertainty else None,
            "reasoning": self.reasoning.model_dump() if self.reasoning else None,
            "emotional": self.emotional.model_dump() if self.emotional else None,
            "contradiction": self.contradiction.model_dump() if self.contradiction else None,
            "knowledge_ceiling": (
                self.knowledge_ceiling.model_dump() if self.knowledge_ceiling else None
            ),
            "concept_depth": self.concept_depth.model_dump() if self.concept_depth else None,
            # Metadata
            "turn_number": self.turn_number,
            "source_utterance_id": self.source_utterance_id,
            "generated_at": self.generated_at.isoformat(),
            "llm_model": self.llm_model,
            "prompt_version": self.prompt_version,
            "extraction_latency_ms": self.extraction_latency_ms,
            "extraction_errors": self.extraction_errors,
        }
