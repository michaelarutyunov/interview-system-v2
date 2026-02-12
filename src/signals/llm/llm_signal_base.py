"""Base class for LLM-based signals."""

from src.signals.signal_base import SignalDetector


class BaseLLMSignal(SignalDetector):
    """Base for LLM signals with fresh computation.

    LLM signals are ALWAYS computed fresh per response.
    No cross-response caching - we want current signal state.

    Cost tier is always HIGH (LLM calls are expensive).
    Refresh trigger is always PER_RESPONSE.

    Subclasses must implement _analyze_with_llm() method.
    """

    async def detect(self, context, graph_state, response_text):
        """Detect signal by analyzing response with LLM.

        This method ensures fresh computation every time.
        """
        return await self._analyze_with_llm(response_text)

    async def _analyze_with_llm(self, response_text: str) -> dict:
        """Analyze response text with LLM.

        Subclasses implement this to perform specific analysis.
        For proof-of-concept, use simple heuristics.
        In production, this would call an LLM API.
        """
        raise NotImplementedError("Subclasses must implement _analyze_with_llm")
