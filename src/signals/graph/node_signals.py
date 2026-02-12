"""Node-level signals - exhaustion, engagement, relationships.

Consolidated from: node_exhaustion.py, node_engagement.py, node_relationships.py

These signals are derived from NodeStateTracker and computed per node,
enabling joint strategy-node scoring. All require NodeStateTracker.
"""

from src.signals.graph.node_base import NodeSignalDetector


# =============================================================================
# Exhaustion Signals (from node_exhaustion.py)
# =============================================================================

class NodeExhaustedSignal(NodeSignalDetector):
    """Primary exhaustion flag for nodes.

    A node is considered exhausted when:
    - It has been focused on at least once
    - No yield for 3+ turns
    - Current focus streak is 2+ (persistent focus without yield)
    - 2/3 of recent responses are shallow

    Namespaced signal: graph.node.exhausted
    """

    signal_name = "graph.node.exhausted"
    description = "Binary exhaustion indicator. 'true' if node is exhausted (no yield, shallow responses, persistent focus), 'false' otherwise."

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
    """

    signal_name = "graph.node.exhaustion_score"
    description = "Continuous exhaustion score 0.0-1.0. Higher values indicate the node has been explored thoroughly without yielding new information."

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
    """

    signal_name = "graph.node.yield_stagnation"
    description = "Whether node has yield stagnation (no yield for 3+ consecutive turns). 'true' if stagnated, 'false' otherwise."

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


# =============================================================================
# Engagement Signals (from node_engagement.py)
# =============================================================================

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
    """

    signal_name = "graph.node.focus_streak"
    description = "Current focus streak category: none (0), low (1), medium (2-3), high (4+). Indicates persistent focus on a node."

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
    """

    signal_name = "graph.node.is_current_focus"
    description = "Whether this node is the current focus. 'true' for focused node, 'false' for others."

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
    """

    signal_name = "graph.node.recency_score"
    description = "Recency score 0.0-1.0. Higher values indicate the node was focused more recently. Decays over 20 turns."

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


# =============================================================================
# Relationship Signals (from node_relationships.py)
# =============================================================================

class NodeIsOrphanSignal(NodeSignalDetector):
    """Whether a node is an orphan (no edges).

    An orphan node has no incoming or outgoing edges, meaning
    it's not connected to any other nodes in the graph.

    Namespaced signal: graph.node.is_orphan
    """

    signal_name = "graph.node.is_orphan"
    description = "Whether node is an orphan (no edges). 'true' if isolated, 'false' if connected."

    async def detect(self, context, graph_state, response_text):
        """Detect orphan status for all nodes.

        Returns:
            Dict mapping node_id -> "true" or "false"
        """
        results = {}

        for node_id, state in self._get_all_node_states().items():
            is_orphan = state.is_orphan
            results[node_id] = "true" if is_orphan else "false"

        return results


class NodeEdgeCountSignal(NodeSignalDetector):
    """Total number of edges connected to a node.

    Returns the sum of incoming and outgoing edges for each node.

    Namespaced signal: graph.node.edge_count
    """

    signal_name = "graph.node.edge_count"
    description = "Total number of edges (incoming + outgoing) connected to this node. Higher values indicate more connected concepts."

    async def detect(self, context, graph_state, response_text):
        """Detect edge count for all nodes.

        Returns:
            Dict mapping node_id -> int (total edge count)
        """
        results = {}

        for node_id, state in self._get_all_node_states().items():
            total_edges = state.edge_count_incoming + state.edge_count_outgoing
            results[node_id] = total_edges

        return results


class NodeHasOutgoingSignal(NodeSignalDetector):
    """Whether a node has outgoing edges.

    Returns "true" if the node has at least one outgoing edge,
    "false" otherwise. This indicates the node has been
    explored and has connections to other nodes.

    Namespaced signal: graph.node.has_outgoing
    """

    signal_name = "graph.node.has_outgoing"
    description = "Whether node has outgoing edges. 'true' if node has been explored and has connections, 'false' otherwise."

    async def detect(self, context, graph_state, response_text):
        """Detect outgoing edges for all nodes.

        Returns:
            Dict mapping node_id -> "true" or "false"
        """
        results = {}

        for node_id, state in self._get_all_node_states().items():
            has_outgoing = state.edge_count_outgoing > 0
            results[node_id] = "true" if has_outgoing else "false"

        return results


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Exhaustion
    "NodeExhaustedSignal",
    "NodeExhaustionScoreSignal",
    "NodeYieldStagnationSignal",
    # Engagement
    "NodeFocusStreakSignal",
    "NodeIsCurrentFocusSignal",
    "NodeRecencyScoreSignal",
    # Relationships
    "NodeIsOrphanSignal",
    "NodeEdgeCountSignal",
    "NodeHasOutgoingSignal",
]
