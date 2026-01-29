"""Node engagement signals.

These signals track how engaged the interview has been with each node,
including focus streaks, current focus status, and recency.
"""

from src.methodologies.signals.common import (
    SignalCostTier,
    RefreshTrigger,
)
from src.methodologies.signals.graph.node_base import NodeSignalDetector


class NodeFocusStreakSignal(NodeSignalDetector):
    """Consecutive turns a node has been in focus.

    Tracks the current focus streak for each node, which resets
    when focus changes or when the node yields.

    Categories:
    - none: 0 consecutive turns (not currently focused)
    - low: 1 consecutive turn
    - medium: 2-3 consecutive turns
    - high: 4+ consecutive turns

    Namespaced signal: graph.node.focus_streak
    Cost: free (O(1) lookup from state)
    Refresh: per_turn (updated after focus selection)
    """

    signal_name = "graph.node.focus_streak"
    cost_tier = SignalCostTier.FREE
    refresh_trigger = RefreshTrigger.PER_TURN

    async def detect(self, context, graph_state, response_text):
        """Detect focus streak for all nodes.

        Returns:
            Dict mapping node_id -> "none" | "low" | "medium" | "high"
        """
        results = {}

        for node_id, state in self._get_all_node_states().items():
            streak_category = self._categorize_streak(state.current_focus_streak)
            results[node_id] = streak_category

        return results

    def _categorize_streak(self, streak: int) -> str:
        """Categorize focus streak into levels.

        Args:
            streak: Current focus streak count

        Returns:
            Category: "none", "low", "medium", or "high"
        """
        if streak == 0:
            return "none"
        elif streak == 1:
            return "low"
        elif streak <= 3:
            return "medium"
        else:
            return "high"


class NodeIsCurrentFocusSignal(NodeSignalDetector):
    """Whether a node is the current focus.

    Returns "true" for the node that is currently focused,
    "false" for all other nodes.

    Namespaced signal: graph.node.is_current_focus
    Cost: free (O(1) lookup from tracker)
    Refresh: per_turn (updated after focus selection)
    """

    signal_name = "graph.node.is_current_focus"
    cost_tier = SignalCostTier.FREE
    refresh_trigger = RefreshTrigger.PER_TURN

    async def detect(self, context, graph_state, response_text):
        """Detect current focus for all nodes.

        Returns:
            Dict mapping node_id -> "true" or "false"
        """
        results = {}
        current_focus = self.node_tracker.previous_focus

        for node_id in self._get_all_node_states().keys():
            is_current = node_id == current_focus
            results[node_id] = "true" if is_current else "false"

        return results


class NodeRecencyScoreSignal(NodeSignalDetector):
    """How recently a node was focused.

    Returns a score from 0.0 (not focused recently) to 1.0 (focused this turn).
    The score decays over 20 turns.

    Formula: max(0.0, 1.0 - (turns_since_last_focus / 20.0))

    Namespaced signal: graph.node.recency_score
    Cost: free (O(1) lookup from state)
    Refresh: per_turn (updated after focus selection)
    """

    signal_name = "graph.node.recency_score"
    cost_tier = SignalCostTier.FREE
    refresh_trigger = RefreshTrigger.PER_TURN

    async def detect(self, context, graph_state, response_text):
        """Detect recency score for all nodes.

        Returns:
            Dict mapping node_id -> float (0.0 - 1.0)
        """
        results = {}

        for node_id, state in self._get_all_node_states().items():
            recency_score = self._calculate_recency_score(state)
            results[node_id] = recency_score

        return results

    def _calculate_recency_score(self, state) -> float:
        """Calculate recency score for a node state.

        Args:
            state: NodeState to score

        Returns:
            Recency score from 0.0 (old) to 1.0 (recent)
        """
        # If never focused, score is 0.0
        if state.last_focus_turn is None:
            return 0.0

        # Decay over 20 turns
        turns_since = state.turns_since_last_focus
        return max(0.0, 1.0 - (turns_since / 20.0))
