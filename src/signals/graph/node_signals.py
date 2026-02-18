"""Node-level signals - exhaustion, engagement, relationships.

Consolidated from: node_exhaustion.py, node_engagement.py, node_relationships.py

These signals are derived from NodeStateTracker and computed per node,
enabling joint strategy-node scoring. All require NodeStateTracker.
"""

from src.signals.graph.node_base import NodeSignalDetector


# =============================================================================
# Exhaustion Signals
# =============================================================================


class NodeExhaustedSignal(NodeSignalDetector):
    """Binary exhaustion flag for node-level strategy selection.

    Detects when nodes are exhausted based on yield history, focus streak,
    and response depth. Exhausted nodes are deprioritized in joint strategy-node
    scoring to avoid questioning spent concepts.

    A node is considered exhausted when:
    - It has been focused on at least once (focus_count > 0)
    - No yield for 3+ turns (turns_since_last_yield >= 3)
    - Current focus streak is 2+ (persistent focus without yield)
    - 2/3 of recent responses are shallow (shallow_ratio >= 0.66)

    Namespaced signal: graph.node.exhausted
    Cost: low (reads from NodeStateTracker state)
    Refresh: per_turn (recomputed each turn after state updates)
    """

    signal_name = "graph.node.exhausted"
    description = "Binary exhaustion indicator. True if node is exhausted (no yield, shallow responses, persistent focus), False otherwise."

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Detect exhausted nodes for joint strategy-node scoring.

        Iterates through all tracked node states and applies exhaustion criteria
        to determine which nodes have been fully explored without yielding
        new information.

        Args:
            context: Pipeline context with conversation state
            graph_state: Current knowledge graph state
            response_text: User's response text (not directly used)

        Returns:
            Dict mapping node_id -> True if exhausted, False otherwise
        """
        results = {}

        for node_id, state in self._get_all_node_states().items():
            is_exhausted = self._is_exhausted(state)
            results[node_id] = is_exhausted

        return results

    def _is_exhausted(self, state) -> bool:
        """Check if a node state indicates exhaustion using multi-factor criteria.

        Applies four exhaustion filters in sequence:
        1. Must have been focused (focus_count > 0)
        2. No recent yield (turns_since_last_yield >= 3)
        3. Persistent focus streak (current_focus_streak >= 2)
        4. High shallow ratio in recent responses (>= 66%)

        Args:
            state: NodeState to check for exhaustion indicators

        Returns:
            True if node meets all exhaustion criteria, False otherwise
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
    """Continuous exhaustion score for fine-grained node ranking.

    Provides a 0.0-1.0 exhaustion metric for each node, enabling nuanced
    strategy-node scoring where partially exhausted nodes can be weighted
    differently from fresh or fully exhausted nodes.

    Scoring factors (weighted sum):
    - Turns since last yield (40% weight, max at 10 turns)
    - Current focus streak (30% weight, max at 5 consecutive)
    - Shallow response ratio (30% weight, 0.0-1.0 range)

    Namespaced signal: graph.node.exhaustion_score
    Cost: low (reads from NodeStateTracker state)
    Refresh: per_turn (recomputed each turn after state updates)
    """

    signal_name = "graph.node.exhaustion_score"
    description = "Continuous exhaustion score 0.0-1.0. Higher values indicate the node has been explored thoroughly without yielding new information."

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Calculate continuous exhaustion scores for all tracked nodes.

        Generates fine-grained exhaustion metrics by combining turn-based
        and response-quality factors into a weighted score.

        Args:
            context: Pipeline context with conversation state (unused, required by base signature)
            graph_state: Current knowledge graph state (unused, required by base signature)
            response_text: User's response text (unused, required by base signature)

        Returns:
            Dict mapping node_id -> float (0.0 = fresh, 1.0 = fully exhausted)
        """
        results = {}

        for node_id, state in self._get_all_node_states().items():
            score = self._calculate_exhaustion_score(state)
            results[node_id] = score

        return results

    def _calculate_exhaustion_score(self, state) -> float:
        """Calculate exhaustion score using weighted multi-factor formula.

        Combines three exhaustion indicators:
        1. Turns since last yield (0.0 - 0.4, max contribution at 10 turns)
        2. Focus streak (0.0 - 0.3, max contribution at 5 consecutive)
        3. Shallow response ratio (0.0 - 0.3, direct multiplier)

        Args:
            state: NodeState to score for exhaustion

        Returns:
            Exhaustion score from 0.0 (fresh, never focused) to 1.0 (fully exhausted)
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
    """Detect nodes experiencing yield stagnation during persistent focus.

    Yield stagnation occurs when a node continues to be focused on
    without producing new extracted relationships (no yield events).
    This signals that the node may be exhausted or that a different
    questioning approach is needed.

    Stagnation criteria:
    - Node has been focused on at least once (focus_count > 0)
    - No yield for 3+ consecutive turns (turns_since_last_yield >= 3)

    Namespaced signal: graph.node.yield_stagnation
    Cost: low (reads from NodeStateTracker state)
    Refresh: per_turn (recomputed each turn after state updates)
    """

    signal_name = "graph.node.yield_stagnation"
    description = "Whether node has yield stagnation (no yield for 3+ consecutive turns). True if stagnated, False otherwise."

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Detect yield stagnation for all tracked nodes.

        Identifies nodes that have been persistently focused without
        yielding new relationships, indicating potential exhaustion
        or need for strategy change.

        Args:
            context: Pipeline context with conversation state (unused, required by base signature)
            graph_state: Current knowledge graph state (unused, required by base signature)
            response_text: User's response text (unused, required by base signature)
            response_text: User's response text (not directly used)

        Returns:
            Dict mapping node_id -> True if stagnated, False otherwise
        """
        results = {}

        for node_id, state in self._get_all_node_states().items():
            has_stagnation = self._has_yield_stagnation(state)
            results[node_id] = has_stagnation

        return results

    def _has_yield_stagnation(self, state) -> bool:
        """Check if a node has yield stagnation based on focus history.

        Stagnation is detected when a previously focused node has gone
        multiple consecutive turns without producing new relationships.

        Args:
            state: NodeState to check for stagnation indicators

        Returns:
            True if node has yield stagnation (no yield for 3+ turns), False otherwise
        """
        # Must have been focused on at least once
        if state.focus_count == 0:
            return False

        # No yield for 3+ turns
        return state.turns_since_last_yield >= 3


# =============================================================================
# Engagement Signals
# =============================================================================


class NodeFocusStreakSignal(NodeSignalDetector):
    """Categorize consecutive turns each node has been in focus.

    Tracks the current focus streak for each node, which resets when
    focus changes or when the node yields. High focus streaks indicate
    persistent questioning on a single concept without yield.

    Categories:
    - none: 0 consecutive turns (not currently focused)
    - low: 1 consecutive turn (initial focus)
    - medium: 2-3 consecutive turns (moderate persistence)
    - high: 4+ consecutive turns (strong persistence, may need strategy change)

    Namespaced signal: graph.node.focus_streak
    Cost: low (reads from NodeStateTracker state)
    Refresh: per_turn (recomputed each turn after state updates)
    """

    signal_name = "graph.node.focus_streak"
    description = "Current focus streak category: none (0), low (1), medium (2-3), high (4+). Indicates persistent focus on a node."

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Detect and categorize focus streak for all tracked nodes.

        Converts numeric focus streak counts into categorical levels
        for use in strategy selection rules and YAML configuration.

        Args:
            context: Pipeline context with conversation state
            graph_state: Current knowledge graph state
            response_text: User's response text (not directly used)

        Returns:
            Dict mapping node_id -> "none" | "low" | "medium" | "high"
        """
        results = {}

        for node_id, state in self._get_all_node_states().items():
            streak_category = self._categorize_streak(state.current_focus_streak)
            results[node_id] = streak_category

        return results

    def _categorize_streak(self, streak: int) -> str:
        """Categorize numeric focus streak into ordinal levels.

        Maps continuous streak values to discrete categories for use in
        strategy selection rules and YAML-based scoring configuration.

        Args:
            streak: Current focus streak count (consecutive turns focused)

        Returns:
            Category string: "none" (0), "low" (1), "medium" (2-3), or "high" (4+)
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
    """Identify which node is currently the system focus.

    Returns a boolean flag indicating whether each node is the current
    focus node. Exactly one node returns True (the previous turn's
    focus), all others return False. Used for strategy selection
    rules that need to know the active focus.

    Namespaced signal: graph.node.is_current_focus
    Cost: low (reads from NodeStateTracker.previous_focus)
    Refresh: per_turn (recomputed each turn after state updates)
    """

    signal_name = "graph.node.is_current_focus"
    description = "Whether this node is the current focus. True for focused node, False for others."

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Detect which node is the current focus for all tracked nodes.

        Compares each node_id against the tracker's previous_focus
        value to determine which node is currently active.

        Args:
            context: Pipeline context with conversation state
            graph_state: Current knowledge graph state
            response_text: User's response text (not directly used)

        Returns:
            Dict mapping node_id -> True if current focus, False otherwise
        """
        results = {}
        current_focus = self.node_tracker.previous_focus

        for node_id in self._get_all_node_states().keys():
            is_current = node_id == current_focus
            results[node_id] = is_current

        return results


class NodeRecencyScoreSignal(NodeSignalDetector):
    """Calculate recency score based on how recently each node was focused.

    Provides a time-decay metric where 1.0 means focused this turn
    and 0.0 means not focused for 20+ turns. Used for strategy
    selection to prefer fresh nodes or implement spacing effects.

    Scoring formula: max(0.0, 1.0 - (turns_since_last_focus / 20.0))

    Namespaced signal: graph.node.recency_score
    Cost: low (reads from NodeStateTracker state)
    Refresh: per_turn (recomputed each turn after state updates)
    """

    signal_name = "graph.node.recency_score"
    description = "Recency score 0.0-1.0. Higher values indicate the node was focused more recently. Decays over 20 turns."

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Calculate recency scores for all tracked nodes.

        Applies linear time decay to the turns_since_last_focus
        metric, producing a continuous score for strategy selection.

        Args:
            context: Pipeline context with conversation state
            graph_state: Current knowledge graph state
            response_text: User's response text (not directly used)

        Returns:
            Dict mapping node_id -> float (0.0 = old, 1.0 = just focused)
        """
        results = {}

        for node_id, state in self._get_all_node_states().items():
            recency_score = self._calculate_recency_score(state)
            results[node_id] = recency_score

        return results

    def _calculate_recency_score(self, state) -> float:
        """Calculate recency score using linear time decay.

        Applies a 20-turn decay window where nodes focused more
        recently receive higher scores. Never-focused nodes return 0.0.

        Args:
            state: NodeState to score for recency

        Returns:
            Recency score from 0.0 (never focused or 20+ turns ago) to 1.0 (focused this turn)
        """
        # If never focused, score is 0.0
        if state.last_focus_turn is None:
            return 0.0

        # Decay over 20 turns
        turns_since = state.turns_since_last_focus
        return max(0.0, 1.0 - (turns_since / 20.0))


# =============================================================================
# Relationship Signals
# =============================================================================


class NodeIsOrphanSignal(NodeSignalDetector):
    """Identify orphan nodes that have no connections to other nodes.

    An orphan node has zero incoming and zero outgoing edges, meaning
    it was extracted but never connected to other concepts. Orphans
    represent opportunities to clarify relationships or may indicate
    extracted concepts that need contextualization.

    Namespaced signal: graph.node.is_orphan
    Cost: low (reads from NodeStateTracker state)
    Refresh: per_turn (recomputed each turn after state updates)
    """

    signal_name = "graph.node.is_orphan"
    description = (
        "Whether node is an orphan (no edges). True if isolated, False if connected."
    )

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Detect orphan status for all tracked nodes.

        Reads edge counts from node state to determine which
        nodes are disconnected from the graph structure.

        Args:
            context: Pipeline context with conversation state
            graph_state: Current knowledge graph state
            response_text: User's response text (not directly used)

        Returns:
            Dict mapping node_id -> True if orphan (no edges), False if connected
        """
        results = {}

        for node_id, state in self._get_all_node_states().items():
            is_orphan = state.is_orphan
            results[node_id] = is_orphan

        return results


class NodeEdgeCountSignal(NodeSignalDetector):
    """Count total connections for each node in the graph.

    Returns the sum of incoming and outgoing edges, indicating how
    well-connected each concept is. High edge counts suggest
    central, important concepts; low counts indicate peripheral
    or under-explored nodes.

    Namespaced signal: graph.node.edge_count
    Cost: low (reads from NodeStateTracker state)
    Refresh: per_turn (recomputed each turn after state updates)
    """

    signal_name = "graph.node.edge_count"
    description = "Total number of edges (incoming + outgoing) connected to this node. Higher values indicate more connected concepts."

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Calculate total edge counts for all tracked nodes.

        Sums incoming and outgoing edge counts from node state
        to provide a connectivity metric for each concept.

        Args:
            context: Pipeline context with conversation state
            graph_state: Current knowledge graph state
            response_text: User's response text (not directly used)

        Returns:
            Dict mapping node_id -> int (total edge count, 0 if orphan)
        """
        results = {}

        for node_id, state in self._get_all_node_states().items():
            total_edges = state.edge_count_incoming + state.edge_count_outgoing
            results[node_id] = total_edges

        return results


class NodeHasOutgoingSignal(NodeSignalDetector):
    """Detect which nodes have outgoing relationships.

    Returns a boolean indicating whether each node has at least one
    outgoing edge. Nodes with outgoing edges have been explored
    and connected to other concepts; nodes without may be leaf
    concepts that haven't been elaborated on.

    Namespaced signal: graph.node.has_outgoing
    Cost: low (reads from NodeStateTracker state)
    Refresh: per_turn (recomputed each turn after state updates)
    """

    signal_name = "graph.node.has_outgoing"
    description = "Whether node has outgoing edges. True if node has been explored and has connections, False otherwise."

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Detect outgoing edge presence for all tracked nodes.

        Checks edge_count_outgoing for each node to determine
        which nodes have been connected to downstream concepts.

        Args:
            context: Pipeline context with conversation state
            graph_state: Current knowledge graph state
            response_text: User's response text (not directly used)

        Returns:
            Dict mapping node_id -> True if has outgoing edges, False otherwise
        """
        results = {}

        for node_id, state in self._get_all_node_states().items():
            has_outgoing = state.edge_count_outgoing > 0
            results[node_id] = has_outgoing

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
