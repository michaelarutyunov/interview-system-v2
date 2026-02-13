"""Response depth signal — assesses elaboration quantity on 1-5 scale.

Measures how much detail and elaboration the respondent provides
in their answer. Depth indicates information richness and extraction
potential for knowledge graph construction.
"""

from src.signals.llm.decorator import llm_signal
from src.signals.llm.llm_signal_base import BaseLLMSignal


@llm_signal(  # type: ignore[type-var]
    signal_name="llm.response_depth",
    rubric_key="response_depth",
    description="Assesses quantity of elaboration on a 1-5 scale. 1=surface/minimal, 3=moderate, 5=deep/extensive.",
)
class ResponseDepthSignal(BaseLLMSignal):
    """Measure elaboration quantity for extraction potential assessment.

    Assesses how much detail the respondent provides, indicating
    information richness and opportunities for knowledge graph extraction.

    Depth categories (1-5 rubric):
    1 - Surface: Minimal response, single phrase, no elaboration
    2 - Shallow: Brief statement with limited detail
    3 - Moderate: Some elaboration with explanation or context
    4 - Substantial: Good detail with reasoning or examples
    5 - Deep: Extensive elaboration with multiple facets, reasoning, examples

    Higher depth scores indicate greater extraction potential and
    respondent engagement.

    Namespaced signal: llm.response_depth
    Cost: high (requires LLM analysis or heuristic text processing)
    Refresh: per_response (always computed fresh)
    """
    pass
