"""Global response trend signal - tracks response quality over time.

This signal aggregates response depth across the session to detect:
- deepening: Responses getting more detailed
- stable: Consistent response quality
- shallowing: Responses getting shorter/simpler
- fatigued: User is disengaged (multiple shallow responses)
"""

from typing import Optional, List
from src.signals.signal_base import SignalDetector


class GlobalResponseTrendSignal(SignalDetector):
    """Track if responses are getting shallower globally (fatigue?).

    Namespaced signal: llm.global_response_trend

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

    # Map categorical depth labels to numeric scores for trend arithmetic
    _DEPTH_SCORE: dict = {
        "surface": 1,
        "shallow": 2,
        "moderate": 3,
        "deep": 4,
    }

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

        # Get recent history (last 6 responses)
        recent = self.response_history[-6:]

        if not recent:
            return {self.signal_name: "stable"}

        # Map to numeric scores; unknown labels default to "moderate" (3)
        scores = [self._DEPTH_SCORE.get(d, 3) for d in recent]

        # Detect fatigue: 4+ shallow responses (score <= 2) in recent window
        shallow_count = sum(1 for s in scores if s <= 2)
        if shallow_count >= 4:
            return {self.signal_name: "fatigued"}

        # Require at least 4 turns of history before claiming a trend; default
        # to "stable" while accumulating so the signal does not fire
        # spuriously on the first few turns.
        if len(scores) < 4:
            return {self.signal_name: "stable"}

        # Compare the mean score of the older half vs the newer half.
        # A genuine trend requires a consistent directional shift, not just
        # a high absolute level.
        mid = len(scores) // 2
        older_mean = sum(scores[:mid]) / mid
        newer_mean = sum(scores[mid:]) / (len(scores) - mid)

        delta = newer_mean - older_mean

        # Threshold of 0.5 (half a depth level) to avoid noise
        if delta >= 0.5:
            return {self.signal_name: "deepening"}
        elif delta <= -0.5:
            return {self.signal_name: "shallowing"}
        else:
            return {self.signal_name: "stable"}
