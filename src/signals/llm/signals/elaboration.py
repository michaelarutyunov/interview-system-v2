"""Elaboration signal — per-concept substantive content (1-5).

Replaces the retired `response_depth`, `specificity`, and `intellectual_engagement`
global signals with a single per-concept dimension.
"""

from src.signals.llm.decorator import llm_per_concept_signal
from src.signals.llm.llm_signal_base import BaseLLMSignal


@llm_per_concept_signal(  # type: ignore[type-var]
    signal_name="response.semantic.llm.elaboration",
    description="Substantive content produced about a specific concept (1-5).",
)
class ElaborationSignal(BaseLLMSignal):
    """Per-concept elaboration — how much was said about THIS concept."""

    RUBRIC: str = """\
How much substantive content did the respondent produce about THIS concept? Score content amount and quality, not word count.

1 = Bare mention. Named without substance. No elaboration, context, or detail.
2 = Brief reference. One attribute, a simple fact, or a single reason. Thin.
3 = Moderate. Specifics provided: a reason, comparison, brief anecdote, or causal link. Enough to understand what the respondent means.
4 = Detailed. Concrete examples, reasoning chains, or situational detail. Explains the what AND the why/how.
5 = Rich. Multiple angles, real-time insight, unexpected connections, or a pivot revealing deeper meaning. Respondent is clearly working the concept through as they speak.

Score substance, not length. A terse answer can score high:
- "I switched because it was cheaper" -> 2 (one reason, no elaboration)
- "I switched because cheaper - and honestly that matters because I'm trying to be more intentional about small daily spending" -> 4 (reason + causal chain + meta-framing in few words)
"""
