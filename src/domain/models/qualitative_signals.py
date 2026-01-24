"""
Qualitative signal models for LLM-based signal extraction.

These models represent semantic signals extracted from conversation history
that provide deeper insight into respondent engagement, reasoning quality,
and knowledge state than rule-based heuristics alone.

ADR-006: Two-tier scoring - Layer 3 of signal architecture.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


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


@dataclass
class UncertaintySignal:
    """Signal capturing type and depth of uncertainty in recent responses.

    Distinguishes between productive uncertainty (curiosity, conceptual clarity)
    and terminal uncertainty (knowledge gaps, apathy).
    """

    uncertainty_type: UncertaintyType
    confidence: float  # 0-1, how confident in this classification
    severity: float  # 0-1, how severe the uncertainty is
    examples: List[str] = field(default_factory=list)  # Quotes that led to this
    reasoning: str = ""  # LLM's reasoning for this classification


@dataclass
class ReasoningSignal:
    """Signal capturing the quality of reasoning in recent responses.

    Helps assess whether the respondent is engaging in deep causal reasoning
    or providing surface-level associations.
    """

    reasoning_quality: ReasoningQuality
    confidence: float  # 0-1
    depth_score: float  # 0-1, how deep the reasoning goes
    has_examples: bool  # Uses concrete examples
    has_abstractions: bool  # Uses abstract principles
    examples: List[str] = field(default_factory=list)
    reasoning: str = ""


@dataclass
class EmotionalSignal:
    """Signal capturing emotional engagement and intensity.

    Helps distinguish between genuine interest and polite participation.
    """

    intensity: EmotionalIntensity
    confidence: float  # 0-1
    trajectory: str  # "rising", "falling", "stable", "volatile"
    markers: List[str] = field(default_factory=list)  # "excited", "hesitant"
    reasoning: str = ""


@dataclass
class ContradictionSignal:
    """Signal detecting contradictions or stance shifts.

    Identifies when current responses contradict earlier statements,
    which may indicate: exploring new perspectives, genuine confusion,
    or interview fatigue.
    """

    has_contradiction: bool
    contradiction_type: Optional[str]  # "stance reversal", "inconsistent detail", etc.
    earlier_statement: str = ""  # The contradicted statement
    current_statement: str = ""  # The contradicting statement
    confidence: float = 0.0
    reasoning: str = ""


@dataclass
class KnowledgeCeilingSignal:
    """Signal distinguishing types of "don't know" responses.

    Terminal: "I don't know and don't have more to say"
    Exploratory: "I don't know, but I'm curious about..."
    Transitional: "I don't know about X, but I do know about Y"
    """

    is_terminal: bool  # True if this is a hard stop
    response_type: str  # "terminal", "exploratory", "transitional"
    has_curiosity: bool  # Shows interest despite knowledge gap
    redirection_available: bool  # Can pivot to related topic
    confidence: float = 0.0
    reasoning: str = ""


@dataclass
class ConceptDepthSignal:
    """Signal assessing abstraction level of concepts discussed.

    Helps determine whether to deepen (more abstract) or broaden
    (more concrete) exploration.
    """

    abstraction_level: float  # 0-1, 0=very concrete, 1=very abstract
    has_concrete_examples: bool
    has_abstract_principles: bool
    suggestion: str  # "deepen", "broaden", "stay"
    confidence: float = 0.0
    reasoning: str = ""


@dataclass
class QualitativeSignalSet:
    """Complete set of qualitative signals for a conversation turn.

    Extracted via LLM analysis of recent conversation history.
    Designed to be consumed by Tier 1/Tier 2 scorers for more nuanced
    decision-making than rule-based heuristics alone.
    """

    uncertainty: Optional[UncertaintySignal] = None
    reasoning: Optional[ReasoningSignal] = None
    emotional: Optional[EmotionalSignal] = None
    contradiction: Optional[ContradictionSignal] = None
    knowledge_ceiling: Optional[KnowledgeCeilingSignal] = None
    concept_depth: Optional[ConceptDepthSignal] = None

    # Metadata
    turn_number: int = 0
    extraction_latency_ms: int = 0
    llm_model: str = ""
    extraction_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/debugging."""
        return {
            "uncertainty": self.uncertainty.__dict__ if self.uncertainty else None,
            "reasoning": self.reasoning.__dict__ if self.reasoning else None,
            "emotional": self.emotional.__dict__ if self.emotional else None,
            "contradiction": self.contradiction.__dict__
            if self.contradiction
            else None,
            "knowledge_ceiling": (
                self.knowledge_ceiling.__dict__ if self.knowledge_ceiling else None
            ),
            "concept_depth": self.concept_depth.__dict__
            if self.concept_depth
            else None,
            "turn_number": self.turn_number,
            "extraction_latency_ms": self.extraction_latency_ms,
            "llm_model": self.llm_model,
            "extraction_errors": self.extraction_errors,
        }
