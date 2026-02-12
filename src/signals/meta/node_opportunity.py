"""Node opportunity meta signal.

This meta signal combines multiple node-level signals to determine
what action should be taken for each node: exhausted, probe_deeper, or fresh.
"""

from typing import TYPE_CHECKING, Dict, Optional

from src.signals.graph.node_base import NodeSignalDetector

if TYPE_CHECKING:
    pass


class NodeOpportunitySignal(NodeSignalDetector):
    """Meta signal: what's the best action for this node?

    Combines multiple signals to determine node opportunity:
    - graph.node.exhausted: Is the node exhausted?
    - graph.node.focus_streak: How long has it been focused?
    - llm.response_depth: How deep was the last response?

    Categories:
    - exhausted: Node is exhausted (no yield, shallow responses, persistent focus)
    - probe_deeper: Deep responses but no yield (extraction opportunity)
    - fresh: Node has opportunity for exploration

    Namespaced signal: meta.node.opportunity

    Note: This signal computes its dependencies directly from node state
    rather than relying on context.signals because node-level signals
    are computed per-node and reading from context.signals would be
    inefficient (would require iterating through all signals).
    """

    signal_name = "meta.node.opportunity"
    description = "Node opportunity category: exhausted (skip), probe_deeper (extraction opportunity), or fresh (explore). Combines exhaustion, focus streak, and response depth."
    # Note: Dependencies are computed inline from node state (node-level pattern)
    dependencies = []

    async def detect(
        self, context, graph_state, response_text: str
    ) -> Dict[str, str]:
        """Detect node opportunity for all tracked nodes.

        Args:
            context: Pipeline context
            graph_state: Current knowledge graph state
            response_text: User's response text

        Returns:
            Dict mapping node_id -> "exhausted" | "probe_deeper" | "fresh"
        """
        # Get response depth from global signals if available
        response_depth = self._get_response_depth(context)

        results = {}

        for node_id, state in self._get_all_node_states().items():
            # Compute dependency signals inline from node state
            is_exhausted = self._is_exhausted(state)
            streak = self._get_focus_streak_category(state)

            # Determine opportunity
            opportunity = self._determine_opportunity(
                is_exhausted, streak, state, response_depth
            )
            results[node_id] = opportunity

        return results

    def _is_exhausted(self, state) -> bool:
        """Check if node is exhausted.

        A node is exhausted when:
        - Has been focused (focus_count > 0)
        - No recent yield (turns_since_last_yield >= 3)
        - High shallow ratio in recent responses (>= 66%)

        Args:
            state: NodeState for the node

        Returns:
            True if exhausted, False otherwise
        """
        if state.focus_count == 0:
            return False

        if state.turns_since_last_yield < 3:
            return False

        shallow_ratio = self._calculate_shallow_ratio(state, recent_count=3)
        return shallow_ratio >= 0.66

    def _get_focus_streak_category(self, state) -> str:
        """Get focus streak category for a node.

        Args:
            state: NodeState for the node

        Returns:
            Focus streak category: "none", "low", "medium", "high"
        """
        streak = state.current_focus_streak
        if streak == 0:
            return "none"
        elif streak <= 2:
            return "low"
        elif streak <= 4:
            return "medium"
        else:
            return "high"

    def _determine_opportunity(
        self,
        is_exhausted: bool,
        streak: str,
        state,
        response_depth: Optional[str],
    ) -> str:
        """Determine opportunity category for a node.

        Args:
            is_exhausted: Whether node is exhausted
            streak: Focus streak category (none/low/medium/high)
            state: NodeState for the node
            response_depth: Current response depth (surface/shallow/moderate/deep)

        Returns:
            Opportunity category: "exhausted" | "probe_deeper" | "fresh"
        """
        if is_exhausted:
            return "exhausted"

        # Check for probe_deeper: high focus streak + deep response
        # This indicates extraction opportunity (deep responses but no yield)
        if streak == "high" and response_depth == "deep":
            return "probe_deeper"

        # Default: fresh opportunity
        return "fresh"

    def _get_response_depth(self, context) -> Optional[str]:
        """Get response depth from context signals.

        Args:
            context: Pipeline context

        Returns:
            Response depth string or None
        """
        # Try to get from context.signals if available
        if hasattr(context, "signals") and context.signals:
            return context.signals.get("llm.response_depth")

        # Try to get from response_text analysis
        # This is a simplified fallback - in production would use LLM
        return None

    def _calculate_shallow_ratio(
        self, state, recent_count: int = 3
    ) -> float:
        """Calculate ratio of shallow responses in recent N responses.

        Args:
            state: NodeState to analyze
            recent_count: Number of recent responses to consider

        Returns:
            Ratio of shallow responses (0.0 - 1.0)
        """
        if not state.all_response_depths:
            return 0.0

        # Get last N responses
        recent_responses = state.all_response_depths[-recent_count:]

        # Count shallow responses (surface or shallow)
        shallow_count = sum(
            1 for depth in recent_responses if depth in ("surface", "shallow")
        )

        return shallow_count / len(recent_responses)
