"""Response depth signal — assesses elaboration quantity (1-5 scale)."""

from src.signals.llm.decorator import llm_signal


@llm_signal(  # type: ignore[type-var]
    signal_name="llm.response_depth",
    rubric_key="response_depth",
    description="Assesses quantity of elaboration on a 1-5 scale. 1=surface/minimal, 3=moderate, 5=deep/extensive.",
)
class ResponseDepthSignal:
    """Response depth signal: measures elaboration quantity.

    Depth categories:
    1 - Minimal/surface: Brief statement without elaboration
    3 - Moderate: Some elaboration with explanation or context
    5 - Extensive/deep: Detailed response with reasoning, examples, multiple facets
    """
    pass
