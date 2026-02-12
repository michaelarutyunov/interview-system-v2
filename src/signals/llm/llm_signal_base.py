"""Base class for LLM-based response analysis signals.

Provides the foundation for signals that analyze user response text
using LLM-based rubric scoring. All LLM signals are computed
fresh per response (no cross-response caching) to capture current
conversation state.
"""

from src.signals.signal_base import SignalDetector


class BaseLLMSignal(SignalDetector):
    """Abstract base for LLM-based response analysis signals.

    LLM signals analyze user response text using qualitative rubrics
    (depth, certainty, engagement, specificity, valence). Unlike graph
    and temporal signals, LLM signals are ALWAYS computed fresh per
    response to capture the current conversation state.

    Key characteristics:
    - No cross-response caching (each response is analyzed independently)
    - High cost tier (requires LLM API call or heuristic analysis)
    - Per-response refresh (recomputed on every user response)

    Subclasses must implement the _analyze_with_llm() method with
    specific rubric-based scoring logic.

    Namespaced signals: llm.* (llm.response_depth, llm.certainty, etc.)
    Cost: high (requires LLM analysis or heuristic computation)
    Refresh: per_response (always computed fresh)
    """

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001, ARG002, ARG003
        """Detect signal by analyzing response text with LLM rubric.

        Ensures fresh computation on every call by delegating to
        the subclass-specific _analyze_with_llm() implementation.

        Args:
            context: Pipeline context (unused, LLM signals analyze text directly)
            graph_state: Current knowledge graph state (unused, response-focused)
            response_text: User's response text to analyze

        Returns:
            Dict with signal_name -> rubric score (typically 1-5 scale or category)
        """
        return await self._analyze_with_llm(response_text)

    async def _analyze_with_llm(self, response_text: str) -> dict:
        """Analyze response text using LLM-based rubric scoring.

        Subclasses implement this method to perform specific qualitative
        analysis on response text. For proof-of-concept, simple
        heuristics may be used. In production, this would call an
        LLM API with rubric-based prompts.

        Args:
            response_text: User's response text to analyze

        Returns:
            Dict mapping signal_name to detected value (rubric score or category)

        Raises:
            NotImplementedError: If subclass does not implement
        """
        raise NotImplementedError("Subclasses must implement _analyze_with_llm")
