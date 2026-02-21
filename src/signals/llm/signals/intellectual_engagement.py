"""Intellectual engagement signal — analytical investment and motivational reasoning depth.

Measures whether the respondent's response reveals reasoning chains, expressed
values, tradeoffs, or causal motivations — orthogonal to emotional warmth.
High scores indicate that the respondent is surfacing *why* they care, which
makes them ready for motivational laddering (dig_motivation strategy).
"""

from src.signals.llm.decorator import llm_signal
from src.signals.llm.llm_signal_base import BaseLLMSignal


@llm_signal(  # type: ignore[type-var]
    signal_name="llm.intellectual_engagement",
    rubric_key="intellectual_engagement",
    description=(
        "Assesses reasoning and motivational depth. "
        "1=bare facts only, 5=dense causal/value reasoning revealing why something matters."
    ),
)
class IntellectualEngagementSignal(BaseLLMSignal):
    """Measure analytical investment via expressed reasoning and motivational structure.

    Detects whether the respondent surfaces reasons, values, tradeoffs, or
    goal-oriented language — independent of emotional engagement or response
    length. A terse but value-dense answer scores high; a lengthy but purely
    descriptive answer scores low.

    Distinguishes from existing signals:
    - `llm.engagement`: willingness to participate (participatory quality)
    - `llm.response_depth`: elaboration quantity (number of propositions)
    - `llm.specificity`: concreteness of language (facts, names, quantities)
    - `llm.intellectual_engagement`: motivational structure (reasoning, values, WHY)

    High scores indicate the respondent is revealing motivation architecture,
    making them ready for dig_motivation (why-laddering) strategy. This is
    particularly useful for analytical personas who express deep investment
    through logical reasoning rather than emotional enthusiasm.

    Namespaced signal: llm.intellectual_engagement
    Cost: high (requires LLM analysis)
    Refresh: per_response (always computed fresh)
    """

    pass
