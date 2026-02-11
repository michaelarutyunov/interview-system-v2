"""Base classes for signal detection."""

from abc import ABC, abstractmethod
from typing import Any


class SignalDetector(ABC):
    """Base class for signal detectors.

    A signal detector analyzes context, graph state, and response text
    to extract structured signals for strategy selection.

    Attributes:
        signal_name: Namespaced signal name (e.g., "graph.node_count")

    Example:
        class GraphNodeCountSignal(SignalDetector):
            signal_name = "graph.node_count"

            async def detect(self, context, graph_state, response_text):
                return {self.signal_name: graph_state.node_count}
    """

    signal_name: str

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
