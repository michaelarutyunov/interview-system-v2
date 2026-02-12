"""Engagement signal — assesses respondent willingness to engage on 1-5 scale.

Measures how actively the respondent participates in the interview
through elaboration effort, volunteered information, and interaction
quality. Engagement indicates interview health and rapport.
"""

from src.signals.llm.decorator import llm_signal


@llm_signal(  # type: ignore[type-var]
    signal_name="llm.engagement",
    rubric_key="engagement",
    description="Assesses respondent's willingness to engage. 1=minimal effort, 5=high engagement.",
)
class EngagementSignal:
    """Measure respondent engagement and willingness to participate.

    Assesses interview participation quality through response elaboration,
    volunteered information, and interaction enthusiasm. Low engagement
    may signal rapport issues or topic disinterest.

    Engagement categories (1-5 rubric):
    1 - Minimal: Single words, "I don't know", deflection, disengagement
    2 - Low: Brief answers, minimal elaboration, reactive only
    3 - Adequate: Answers fully but doesn't volunteer additional information
    4 - Good: Engaged elaboration, some volunteered details
    5 - High: Enthusiastic elaboration, introduces new related points unprompted

    Low engagement may require strategy changes to rebuild rapport or
    shift topics. High engagement indicates good interview flow.

    Namespaced signal: llm.engagement
    Cost: high (requires LLM analysis or heuristic text processing)
    Refresh: per_response (always computed fresh)
    """
    pass
