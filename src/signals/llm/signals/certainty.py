"""Certainty signal — global response-level epistemic confidence (1-5)."""

from src.signals.llm.decorator import llm_global_signal
from src.signals.llm.llm_signal_base import BaseLLMSignal


@llm_global_signal(  # type: ignore[type-var]
    signal_name="response.semantic.llm.certainty",
    description="Respondent's expressed confidence in their claims (1-5).",
)
class CertaintySignal(BaseLLMSignal):
    """Global certainty — confidence in claims, not objective truth."""

    RUBRIC: str = """\
How confident does the respondent appear in their claims?

1 = Highly uncertain. Explicit "I don't know", "maybe", genuine hedges throughout.
2 = Tentative. Multiple qualifications. "I guess", "kind of", "sort of" as genuine modifiers.
3 = Moderate. Some qualifications but committed on the core position.
4 = Confident with minor caveats. Assertive with occasional softeners that don't undermine.
5 = Fully committed. Unqualified assertions, no hedging.

Score expressed confidence, not objective truth.

Distinguish genuine hedges from social softeners:
- Genuine hedges (reduce score): "mostly", "kind of", "I guess", "maybe"
- Social softeners (do NOT reduce score): "I think", "I feel" as sentence openers in otherwise assertive statements

Self-discovery is not uncertainty. "I'm realizing this as I say it" or "I never thought about it this way" indicates elaboration, not low certainty. Score certainty on commitment to the claims being made.
"""
