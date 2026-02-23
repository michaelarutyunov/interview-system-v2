"""Node opportunity meta signal for joint strategy-node scoring.

Combines multiple node-level signals to categorize each node's potential:
- exhausted: Node has been explored thoroughly without yield (skip)
- probe_deeper: Deep responses but no new yield (extraction opportunity)
- fresh: Node has opportunity for exploration (default)

This meta signal enables sophisticated strategy-node pairing by identifying
which nodes deserve further attention and which should be deprioritized.
"""

from typing import TYPE_CHECKING, Dict, Optional

import structlog

from src.signals.graph.node_base import NodeSignalDetector

if TYPE_CHECKING:
    pass

log = structlog.get_logger(__name__)


class NodeOpportunitySignal(NodeSignalDetector):
    """Categorize node exploration potential for joint strategy-node scoring.

    Combines exhaustion, focus streak, and response depth signals to
    determine the best action for each node. This enables sophisticated
    strategy-node pairing where exhausted nodes are deprioritized and
    probe-worthy nodes are highlighted.

    Opportunity categories:
    - exhausted: Node is exhausted (no yield, shallow responses, persistent focus)
    - probe_deeper: Deep responses but no yield (extraction opportunity)
    - fresh: Node has opportunity for exploration (default)

    Exhaustion criteria (all must be true):
    - Has been focused (focus_count > 0)
    - No recent yield (turns_since_last_yield >= 3)
    - High shallow ratio (>= 66% of recent 3 responses are shallow)

    Probe_deeper criteria:
    - High focus streak (4+ consecutive turns)
    - Current response is deep

    Namespaced signal: meta.node.opportunity
    Cost: low (reads from NodeStateTracker state, computes dependencies inline)
    Refresh: per_turn (recomputed each turn after state updates)
    """

    signal_name = "meta.node.opportunity"
    description = "Node opportunity category: exhausted (skip), probe_deeper (extraction opportunity), or fresh (explore). Combines exhaustion, focus streak, and response depth."
    # Note: Dependencies are computed inline from node state (node-level pattern)
    dependencies = []

    async def detect(
        self,
        context,
        graph_state,
        response_text: str,  # noqa: ARG001, ARG002, ARG003
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
            opportunity = self._determine_opportunity(is_exhausted, streak, state, response_depth)

            # Detect and log state transitions
            prev_opportunity = self._get_previous_opportunity(context, node_id)
            if prev_opportunity is not None and prev_opportunity != opportunity:
                log.info(
                    "node_opportunity_transition",
                    node_id=node_id,
                    node_label=state.label,
                    old_opportunity=prev_opportunity,
                    new_opportunity=opportunity,
                    focus_count=state.focus_count,
                    turns_since_last_yield=state.turns_since_last_yield,
                    current_focus_streak=state.current_focus_streak,
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

        Bins aligned with NodeFocusStreakSignal._categorize_streak():
        - none: 0 consecutive turns
        - low: 1 consecutive turn
        - medium: 2-3 consecutive turns
        - high: 4+ consecutive turns

        Args:
            state: NodeState for the node

        Returns:
            Focus streak category: "none", "low", "medium", "high"
        """
        streak = state.current_focus_streak
        if streak == 0:
            return "none"
        elif streak == 1:
            return "low"
        elif streak <= 3:
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

    def _get_previous_opportunity(self, context, node_id: str) -> Optional[str]:
        """Get the previous turn's opportunity value for a node from context signals.

        Context signals come from the previous turn's strategy_selection_output,
        so this reliably reflects the state before the current turn's computation.

        Args:
            context: Pipeline context (holds previous turn's strategy_selection_output)
            node_id: Node identifier

        Returns:
            Previous opportunity string or None if unavailable
        """
        if not hasattr(context, "signals") or not context.signals:
            return None
        prev_opportunities = context.signals.get("meta.node.opportunity", {})
        if not isinstance(prev_opportunities, dict):
            return None
        return prev_opportunities.get(node_id)

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

    def _calculate_shallow_ratio(self, state, recent_count: int = 3) -> float:
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
        shallow_count = sum(1 for depth in recent_responses if depth in ("surface", "shallow"))

        return shallow_count / len(recent_responses)
