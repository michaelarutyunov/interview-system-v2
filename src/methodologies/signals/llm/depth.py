"""Response depth signals - how deep the response is."""

from src.methodologies.signals.llm.common import BaseLLMSignal
from src.methodologies.signals.common import SignalCostTier


class ResponseDepthSignal(BaseLLMSignal):
    """Analyzes response depth: surface | moderate | deep.

    Namespaced signal: llm.response_depth
    Cost: high (LLM analysis)
    Refresh: per_response (ALWAYS fresh)

    Depth categories:
    - surface: Brief, superficial responses (< 10 words)
    - moderate: Medium length with some detail (10-30 words)
    - deep: Detailed, thoughtful responses (> 30 words)
    """

    signal_name = "llm.response_depth"
    description = "LLM assessment of response depth. 'surface' means brief/superficial, 'moderate' means some detail, 'deep' means detailed and thoughtful. Used to gauge engagement and depth of exploration."
    cost_tier = SignalCostTier.HIGH

    async def _analyze_with_llm(self, response_text: str) -> dict:
        """Analyze response depth (simplified for PoC).

        Production: Use LLM to analyze semantic depth.
        Proof-of-concept: Use word count heuristic.
        """
        word_count = len(response_text.split())

        if word_count < 10:
            depth = "surface"
        elif word_count < 30:
            depth = "moderate"
        else:
            depth = "deep"

        # Return both category and numeric score
        return {self.signal_name: depth}
