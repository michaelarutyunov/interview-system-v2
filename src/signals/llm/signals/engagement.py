"""Engagement signal — global response-level willingness to participate (1-5)."""

from src.signals.llm.decorator import llm_global_signal
from src.signals.llm.llm_signal_base import BaseLLMSignal


@llm_global_signal(  # type: ignore[type-var]
    signal_name="response.semantic.llm.engagement",
    description="Respondent's willingness to participate in the interview (1-5).",
)
class EngagementSignal(BaseLLMSignal):
    """Global engagement — willingness, not articulateness."""

    RUBRIC: str = """\
How willing is the respondent to participate?

1 = Minimal effort. Single words, "I don't know", deflection, restating the question.
2 = Compliant but passive. Answers the literal question; no voluntary extension.
3 = Adequate. Answers fully; does not volunteer additional information.
4 = Active. Extends beyond the question, offers unsolicited detail or examples.
5 = High. Enthusiastic elaboration, introduces related points, signals wanting to say more.

Score willingness, not articulateness. A poorly worded but effortful answer is 4-5. A polished but minimal answer is 2.

Do not score real-time self-reflection here. Real-time insight belongs in per-concept elaboration, not engagement.
"""
