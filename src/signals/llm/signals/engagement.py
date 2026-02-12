"""Engagement signal — assesses willingness to engage with topic (1-5 scale)."""

from src.signals.llm.decorator import llm_signal


@llm_signal(
    signal_name="llm.engagement",
    rubric_key="engagement",
    description="Assesses respondent's willingness to engage. 1=minimal effort, 5=high engagement.",
)
class EngagementSignal:
    """Engagement signal: measures respondent's willingness to engage.

    Engagement categories:
    1 - Minimal effort: Single words, "I don't know", deflection
    3 - Adequate: Answers fully but doesn't volunteer additional information
    5 - High engagement: Enthusiastic elaboration, introduces new related points
    """
    pass
