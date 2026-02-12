"""Specificity signal — assesses concreteness of language (1-5 scale)."""

from src.signals.llm.decorator import llm_signal


@llm_signal(
    signal_name="llm.specificity",
    rubric_key="specificity",
    description="Assesses referential specificity or concreteness on a 1-5 scale. 1=very specific, 5=highly ambiguous.",
)
class SpecificitySignal:
    """Specificity signal: measures how concrete or vague response is.

    Specificity categories:
    1 - Very specific: Concrete, tangible concepts named explicitly
    3 - Mixed: Mix of abstract and concrete elements
    5 - Highly ambiguous: Dominated by vague, non-specific language
    """
    pass
