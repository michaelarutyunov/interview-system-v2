"""Valence signal — assesses emotional tone on 1-5 scale.

Measures the emotional polarity of the respondent's language.
Valence indicates affective state and can signal rapport,
topic sensitivity, or respondent comfort.
"""

from src.signals.llm.decorator import llm_signal
from src.signals.llm.llm_signal_base import BaseLLMSignal


@llm_signal(  # type: ignore[type-var]
    signal_name="llm.valence",
    rubric_key="emotional_valence",
    description="Assesses emotional tone of response. 1=strongly negative, 3=neutral, 5=strongly positive.",
)
class ValenceSignal(BaseLLMSignal):
    """Measure emotional tone for affective state assessment.

        Assesses the emotional polarity of the respondent's language.
    Valence indicates affective reaction to topics and can signal
    rapport issues, topic sensitivity, or respondent comfort.

        Valence categories (1-5 rubric):
        1 - Strongly negative: Frustration, anger, disappointment, resistance
        2 - Negative: Displeasure, skepticism, reluctance
        3 - Neutral: Factual, balanced tone, unemotional
        4 - Positive: Interest, approval, mild enthusiasm
        5 - Strongly positive: Excitement, delight, strong advocacy

        Extreme valence (1 or 5) may require strategy adjustments:
        - Negative (1-2): Consider rapport rebuilding or topic shift
        - Positive (4-5): Good opportunity for deepening on liked topics

        Namespaced signal: llm.valence
        Cost: high (requires LLM analysis or heuristic sentiment detection)
        Refresh: per_response (always computed fresh)
    """

    pass
