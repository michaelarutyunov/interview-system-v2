"""Valence signal — assesses emotional tone (1-5 scale)."""

from src.signals.llm.decorator import llm_signal


@llm_signal(  # type: ignore[type-var]
    signal_name="llm.valence",
    rubric_key="emotional_valence",
    description="Assesses emotional tone of response. 1=strongly negative, 3=neutral, 5=strongly positive.",
)
class ValenceSignal:
    """Valence signal: measures emotional tone of response.

    Valence categories:
    1 - Strongly negative: Frustration, anger, disappointment
    3 - Neutral: Factual, balanced tone
    5 - Strongly positive: Excitement, delight, strong advocacy
    """
    pass
