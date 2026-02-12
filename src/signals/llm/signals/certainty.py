"""Certainty signal — assesses expressed confidence in knowledge (1-5 scale)."""

from src.signals.llm.decorator import llm_signal


@llm_signal(  # type: ignore[type-var]
    signal_name="llm.certainty",
    rubric_key="certainty",
    description="Assesses epistemic certainty — how confident respondent appears in their knowledge. 1=very uncertain, 5=fully confident.",
)
class CertaintySignal:
    """Certainty signal: measures respondent's expressed confidence.

    Certainty categories:
    1 - Very uncertain: Explicit expressions of doubt ("I don't know", "maybe")
    3 - Mixed: Some confident, some uncertain statements
    5 - Fully confident: Declarative statements without qualifications
    """
    pass
