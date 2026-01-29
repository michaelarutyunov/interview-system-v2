"""Node opportunity meta signal.

This meta signal combines multiple node-level signals to determine
what action should be taken for each node: exhausted, probe_deeper, or fresh.
"""

from typing import Dict, Optional, TYPE_CHECKING

from src.methodologies.signals.common import (
    SignalCostTier,
    RefreshTrigger,
)
from src.methodologies.signals.graph.node_base import NodeSignalDetector
from src.services.node_state_tracker import NodeStateTracker

if TYPE_CHECKING:
    pass


class NodeOpportunitySignal(NodeSignalDetector):
    """Meta signal: what's the best action for this node?

    Combines multiple signals to determine node opportunity:
    - node.exhausted: Is the node exhausted?
    - node.focus_streak: How long has it been focused?
    - llm.response_depth: How deep was the last response?

    Categories:
    - exhausted: Node is exhausted (no yield, shallow responses, persistent focus)
    - probe_deeper: Deep responses but no yield (extraction opportunity)
    - fresh: Node has opportunity for exploration

    Namespaced signal: meta.node.opportunity
    Cost: medium (depends on node signals)
    Refresh: per_turn (updated after graph changes)
    """

    signal_name = "meta.node.opportunity"
    cost_tier = SignalCostTier.MEDIUM
    refresh_trigger = RefreshTrigger.PER_TURN

    def __init__(self, node_tracker: NodeStateTracker):
        """Initialize the node opportunity signal detector.

        Args:
            node_tracker: NodeStateTracker instance for accessing node states
        """
        super().__init__(node_tracker)

        # Import signal detectors for dependency signals
        # Import here to avoid circular imports
        from src.methodologies.signals.graph.node_exhaustion import (
            NodeExhaustedSignal,
        )
        from src.methodologies.signals.graph.node_engagement import (
            NodeFocusStreakSignal,
        )

        # Create signal detectors for dependency signals
        self.exhausted_signal = NodeExhaustedSignal(node_tracker)
        self.streak_signal = NodeFocusStreakSignal(node_tracker)

    async def detect(self, context, graph_state, response_text: str) -> Dict[str, str]:
        """Detect node opportunity for all tracked nodes.

        Args:
            context: Pipeline context
            graph_state: Current knowledge graph state
            response_text: User's response text

        Returns:
            Dict mapping node_id -> "exhausted" | "probe_deeper" | "fresh"
        """
        # First detect dependency signals
        exhausted_signals = await self.exhausted_signal.detect(
            context, graph_state, response_text
        )
        streak_signals = await self.streak_signal.detect(
            context, graph_state, response_text
        )

        # Get response depth from global signals if available
        response_depth = self._get_response_depth(context)

        results = {}

        for node_id, state in self._get_all_node_states().items():
            # Get dependency signal values
            is_exhausted = exhausted_signals.get(node_id, "false") == "true"
            streak = streak_signals.get(node_id, "none")

            # Determine opportunity
            opportunity = self._determine_opportunity(
                is_exhausted, streak, state, response_depth
            )
            results[node_id] = opportunity

        return results

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
        # Logic from design doc:
        # if is_exhausted:
        #     opportunity = "exhausted"
        # elif streak == "high" and response_depth == "deep":
        #     opportunity = "probe_deeper"  # Deep responses but no yield
        # else:
        #     opportunity = "fresh"

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
