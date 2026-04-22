"""Charge signal — per-concept emotional tone toward concept (1-5).

Replaces the retired global `valence` signal with a per-concept dimension.
"""

from src.signals.llm.decorator import llm_per_concept_signal
from src.signals.llm.llm_signal_base import BaseLLMSignal


@llm_per_concept_signal(  # type: ignore[type-var]
    signal_name="response.semantic.llm.charge",
    description="Emotional tone directed at a specific concept (1-5).",
)
class ChargeSignal(BaseLLMSignal):
    """Per-concept charge — emotion directed at THIS concept specifically."""

    RUBRIC: str = """\
What emotional tone is directed at THIS concept? Score the emotion toward the concept, not the factual content.

1 = Strongly negative. Frustration, anger, distress directed at this concept.
2 = Mildly negative. Concern, unease, mild complaint.
3 = Neutral OR mixed. Either (a) factual/descriptive with no emotional charge, OR (b) both positive and negative present. If mixed, note "mixed" in rationale.
4 = Mildly positive. Satisfaction, appreciation, contentment.
5 = Strongly positive. Excitement, delight, pride, strong advocacy.

Score the emotion directed at this concept specifically:
- Calm description of a negative event -> 3 (neutral reporting)
- Frustrated description of a positive outcome -> 2 (emotion toward the concept is negative)
- Curious, intellectually interested, no affect -> 3 (neutral)
- Ambivalent ("I love it but also hate it") -> 3 with rationale "mixed"

If tone shifts while discussing the concept, score the dominant tone.
"""
