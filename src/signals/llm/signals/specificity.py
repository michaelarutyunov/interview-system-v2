"""Specificity signal — assesses referential concreteness on 1-5 scale.

Measures how concrete or vague the respondent's language is.
Specificity indicates clarity of concepts and may signal need
for clarification prompts.
"""

from src.signals.llm.decorator import llm_signal
from src.signals.llm.llm_signal_base import BaseLLMSignal


@llm_signal(  # type: ignore[type-var]
    signal_name="llm.specificity",
    rubric_key="specificity",
    description="Assesses referential specificity or concreteness on a 1-5 scale. 1=very specific, 5=highly ambiguous.",
)
class SpecificitySignal(BaseLLMSignal):
    """Measure referential specificity for concept clarity assessment.

        Assesses how concrete or vague the respondent's language is.
    High specificity indicates clear, tangible concepts. Low specificity
    suggests abstract or ambiguous language that may require clarification.

        Specificity categories (1-5 rubric):
        1 - Very specific: Concrete, tangible concepts named explicitly
        2 - Specific: Mostly concrete with some general terms
        3 - Mixed: Balance of abstract and concrete elements
        4 - Vague: General terms, some ambiguity
        5 - Highly ambiguous: Dominated by vague, non-specific language

        Low specificity (4-5) may trigger clarification strategies to
        improve concept extraction precision. High specificity (1-2) suggests
        clear, actionable concepts for graph construction.

        Namespaced signal: llm.specificity
        Cost: high (requires LLM analysis or heuristic pattern matching)
        Refresh: per_response (always computed fresh)
    """

    pass
