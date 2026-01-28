"""Base classes for signal detection."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class SignalCostTier(str, Enum):
    """Computation cost tier for a signal.

    Used for optimization and caching decisions:
    - free: O(1) lookup, no computation (e.g., reading from graph state)
    - low: O(n) where n is small, fast computation (e.g., simple aggregation)
    - medium: O(n) where n is moderate, noticeable computation (e.g., graph traversal)
    - high: LLM call or expensive computation (e.g., sentiment analysis)
    """

    FREE = "free"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RefreshTrigger(str, Enum):
    """When a signal should be refreshed/recomputed.

    - per_response: Recomputed for every response (e.g., LLM-based signals)
    - per_turn: Recomputed once per turn (e.g., graph state after updates)
    - per_session: Computed once per session (rare, mostly static data)
    """

    PER_RESPONSE = "per_response"  # Fresh every response
    PER_TURN = "per_turn"  # Refreshed after graph updates
    PER_SESSION = "per_session"  # Computed once, cached


class SignalDetector(ABC):
    """Base class for signal detectors.

    A signal detector analyzes context, graph state, and response text
    to extract structured signals for strategy selection.

    Attributes:
        signal_name: Namespaced signal name (e.g., "graph.node_count")
        cost_tier: Computation cost tier (for optimization)
        refresh_trigger: When to refresh this signal

    Example:
        class GraphNodeCountSignal(SignalDetector):
            signal_name = "graph.node_count"
            cost_tier = SignalCostTier.FREE
            refresh_trigger = RefreshTrigger.PER_TURN

            async def detect(self, context, graph_state, response_text):
                return {self.signal_name: graph_state.node_count}
    """

    signal_name: str
    cost_tier: SignalCostTier = SignalCostTier.LOW
    refresh_trigger: RefreshTrigger = RefreshTrigger.PER_TURN

    @abstractmethod
    async def detect(
        self,
        context: Any,  # PipelineContext (circular import avoided)
        graph_state: Any,  # GraphState (circular import avoided)
        response_text: str,
    ) -> dict[str, Any]:
        """Detect and return signal value(s).

        Args:
            context: Pipeline context with conversation state
            graph_state: Current knowledge graph state
            response_text: User's response text to analyze

        Returns:
            Dictionary mapping signal names to values.
            Usually single key: {self.signal_name: value}
            May return multiple related signals for efficiency.
        """
        ...


class SignalState:
    """Base class for signal state containers.

    Deprecated: New signal pools return plain dicts instead of state objects.
    Kept for backward compatibility during migration.
    """

    pass
