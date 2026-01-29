"""Node exhaustion signals.

These signals detect when a node is exhausted (no longer yielding
new information) based on yield history and response quality.
"""

from src.methodologies.signals.common import (
    SignalCostTier,
    RefreshTrigger,
)
from src.methodologies.signals.graph.node_base import NodeSignalDetector


class NodeExhaustedSignal(NodeSignalDetector):
    """Primary exhaustion flag for nodes.

    A node is considered exhausted when:
    - It has been focused on at least once
    - No yield for 3+ turns
    - Current focus streak is 2+ (persistent focus without yield)
    - 2/3 of recent responses are shallow

    Namespaced signal: graph.node.exhausted
    Cost: low (O(n) where n = tracked nodes)
    Refresh: per_turn (updated after graph changes)
    """

    signal_name = "graph.node.exhausted"
    cost_tier = SignalCostTier.LOW
    refresh_trigger = RefreshTrigger.PER_TURN

    async def detect(self, context, graph_state, response_text):
        """Detect exhausted nodes.

        Returns:
            Dict mapping node_id -> "true" or "false"
        """
        results = {}

        for node_id, state in self._get_all_node_states().items():
            is_exhausted = self._is_exhausted(state)
            results[node_id] = "true" if is_exhausted else "false"

        return results

    def _is_exhausted(self, state) -> bool:
        """Check if a node state indicates exhaustion.

        Args:
            state: NodeState to check

        Returns:
            True if exhausted, False otherwise
        """
        # Must have been focused on at least once
        if state.focus_count == 0:
            return False

        # No yield for 3+ turns
        if state.turns_since_last_yield < 3:
            return False

        # Current focus streak is 2+ (persistent focus without yield)
        if state.current_focus_streak < 2:
            return False

        # 2/3 of recent responses are shallow
        shallow_ratio = self._calculate_shallow_ratio(state, recent_count=3)
        if shallow_ratio < 0.66:
            return False

        return True


class NodeExhaustionScoreSignal(NodeSignalDetector):
    """Continuous exhaustion score for fine-grained scoring.

    Returns a score from 0.0 (fresh) to 1.0 (fully exhausted)
    based on multiple factors:
    - Turns since last yield (capped at 10 turns)
    - Current focus streak (capped at 5)
    - Shallow response ratio

    Namespaced signal: graph.node.exhaustion_score
    Cost: low (O(n) where n = tracked nodes)
    Refresh: per_turn (updated after graph changes)
    """

    signal_name = "graph.node.exhaustion_score"
    cost_tier = SignalCostTier.LOW
    refresh_trigger = RefreshTrigger.PER_TURN

    async def detect(self, context, graph_state, response_text):
        """Detect exhaustion scores for all nodes.

        Returns:
            Dict mapping node_id -> float (0.0 - 1.0)
        """
        results = {}

        for node_id, state in self._get_all_node_states().items():
            score = self._calculate_exhaustion_score(state)
            results[node_id] = score

        return results

    def _calculate_exhaustion_score(self, state) -> float:
        """Calculate exhaustion score for a node state.

        Args:
            state: NodeState to score

        Returns:
            Exhaustion score from 0.0 (fresh) to 1.0 (exhausted)
        """
        # If never focused, score is 0.0
        if state.focus_count == 0:
            return 0.0

        # Factor 1: Turns since last yield (0.0 - 0.4, max at 10 turns)
        turns_score = min(state.turns_since_last_yield, 10) / 10.0 * 0.4

        # Factor 2: Focus streak (0.0 - 0.3, max at 5 consecutive)
        streak_score = min(state.current_focus_streak, 5) / 5.0 * 0.3

        # Factor 3: Shallow ratio (0.0 - 0.3)
        shallow_ratio = self._calculate_shallow_ratio(state, recent_count=3)
        shallow_score = shallow_ratio * 0.3

        # Total score
        return turns_score + streak_score + shallow_score


class NodeYieldStagnationSignal(NodeSignalDetector):
    """Detect nodes with yield stagnation (no yield for N consecutive focuses).

    A node has yield stagnation when:
    - It has been focused on at least once
    - No yield for 3+ consecutive turns

    Namespaced signal: graph.node.yield_stagnation
    Cost: free (O(1) lookup from state)
    Refresh: per_turn (updated after graph changes)
    """

    signal_name = "graph.node.yield_stagnation"
    cost_tier = SignalCostTier.FREE
    refresh_trigger = RefreshTrigger.PER_TURN

    async def detect(self, context, graph_state, response_text):
        """Detect yield stagnation for all nodes.

        Returns:
            Dict mapping node_id -> "true" or "false"
        """
        results = {}

        for node_id, state in self._get_all_node_states().items():
            has_stagnation = self._has_yield_stagnation(state)
            results[node_id] = "true" if has_stagnation else "false"

        return results

    def _has_yield_stagnation(self, state) -> bool:
        """Check if a node has yield stagnation.

        Args:
            state: NodeState to check

        Returns:
            True if yield stagnation detected, False otherwise
        """
        # Must have been focused on at least once
        if state.focus_count == 0:
            return False

        # No yield for 3+ turns
        return state.turns_since_last_yield >= 3
