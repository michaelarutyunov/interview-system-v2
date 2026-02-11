"""Global response trend signal - tracks response quality over time.

This signal aggregates response depth across the session to detect:
- deepening: Responses getting more detailed
- stable: Consistent response quality
- shallowing: Responses getting shorter/simpler
- fatigued: User is disengaged (multiple shallow responses)
"""

from typing import Optional, List
from src.methodologies.signals.signal_base import SignalDetector


class GlobalResponseTrendSignal(SignalDetector):
    """Track if responses are getting shallower globally (fatigue?).

    Namespaced signal: llm.global_response_trend
    Cost: low (aggregates existing signals)
    Refresh: per_turn (updates with each response)

    This signal maintains session-scoped history of response depths
    and computes trends to detect user engagement/fatigue.

    Trend categories:
    - deepening: More deep responses over time (user engaged)
    - stable: Consistent response quality
    - shallowing: More shallow responses over time
    - fatigued: 4+ shallow responses in last 5 (user disengaged)
    """

    signal_name = "llm.global_response_trend"
    description = "Trend in response quality over time. 'deepening' = engaged, 'stable' = consistent, 'shallowing' = declining quality, 'fatigued' = disengaged (4+ shallow responses). 'fatigued' suggests need for rapport repair or closing."

    def __init__(self, history_size: int = 10):
        """Initialize signal with response history tracking.

        Args:
            history_size: Maximum number of response depths to track
        """
        self.history_size = history_size
        self.response_history: List[str] = []  # Track response depths across turns

    def clear_history(self) -> None:
        """Clear response history (e.g., for new session)."""
        self.response_history.clear()

    def add_response_depth(self, depth: str) -> None:
        """Add a response depth to history.

        Args:
            depth: Response depth category (surface/shallow/moderate/deep)
        """
        self.response_history.append(depth)

        # Trim to history_size
        if len(self.response_history) > self.history_size:
            self.response_history = self.response_history[-self.history_size :]

    async def detect(
        self,
        context,
        graph_state,
        response_text: str,
        current_depth: Optional[str] = None,
    ) -> dict:
        """Detect global response trend.

        Args:
            context: Pipeline context (unused for this signal)
            graph_state: Current knowledge graph state (unused)
            response_text: User's response text (unused, uses depth history)
            current_depth: Optional current response depth to add to history

        Returns:
            Dictionary with signal_name: trend_value
        """
        # If current_depth provided, add to history
        if current_depth:
            self.add_response_depth(current_depth)

        # Get recent history (last 5 responses)
        recent = self.response_history[-5:]

        if not recent:
            return {self.signal_name: "stable"}

        # Count deep vs shallow responses
        # Map: deep/moderate = "deep", surface/shallow = "shallow"
        deep_count = sum(1 for d in recent if d in ["deep", "moderate"])
        shallow_count = sum(1 for d in recent if d in ["surface", "shallow"])

        # Detect fatigue: 4+ shallow responses
        if shallow_count >= 4:
            return {self.signal_name: "fatigued"}

        # Detect trends
        if shallow_count > deep_count:
            return {self.signal_name: "shallowing"}
        elif deep_count > shallow_count:
            return {self.signal_name: "deepening"}
        else:
            return {self.signal_name: "stable"}
