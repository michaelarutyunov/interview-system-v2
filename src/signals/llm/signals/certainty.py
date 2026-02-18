"""Certainty signal — assesses epistemic confidence on 1-5 scale.

Measures how confident the respondent appears in their knowledge
expressions. Certainty indicates knowledge stability and can
guide question probing strategies.
"""

from src.signals.llm.decorator import llm_signal
from src.signals.llm.llm_signal_base import BaseLLMSignal


@llm_signal(  # type: ignore[type-var]
    signal_name="llm.certainty",
    rubric_key="certainty",
    description="Assesses epistemic certainty — how confident respondent appears in their knowledge. 1=very uncertain, 5=fully confident.",
)
class CertaintySignal(BaseLLMSignal):
    """Measure epistemic certainty for knowledge confidence assessment.

    Assesses how confident the respondent appears in their knowledge
    expressions based on linguistic markers of doubt, hedging,
    and declarative certainty.

    Certainty categories (1-5 rubric):
    1 - Very uncertain: Explicit doubt ("I don't know", "maybe", "not sure")
    2 - Uncertain: Frequent hedging and qualifiers
    3 - Mixed: Some confident statements mixed with uncertain ones
    4 - Confident: Generally declarative with occasional qualifications
    5 - Fully confident: Declarative statements without qualifications

    Lower certainty may indicate areas for deeper probing or knowledge
    gaps. Higher certainty suggests stable, well-established knowledge.

    Namespaced signal: llm.certainty
    Cost: high (requires LLM analysis or heuristic pattern matching)
    Refresh: per_response (always computed fresh)
    """

    pass
