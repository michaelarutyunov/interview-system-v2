"""Interview phase detection signal.

Detects the current interview phase based on graph state:
- early: Initial exploration, building graph structure
- mid: Building depth and connections
- late: Validation and verification
"""

from src.methodologies.signals.common import (
    SignalDetector,
    SignalCostTier,
    RefreshTrigger,
)


class InterviewPhaseSignal(SignalDetector):
    """Detect interview phase based on graph state.

    Uses graph state metrics to determine interview phase:
    - node_count: Total number of nodes in graph
    - max_depth: Maximum depth of the graph
    - orphan_count: Number of orphan nodes (no connections)

    Phase logic:
    - early: node_count < 5 (initial exploration)
    - mid: node_count < 15 or orphan_count > 3 (building depth/connections)
    - late: node_count >= 15 (validation and verification)

    Namespaced signal: meta.interview.phase
    Cost: free (O(1) lookup from graph_state)
    Refresh: per_turn (updated after graph changes)
    """

    signal_name = "meta.interview.phase"
    cost_tier = SignalCostTier.FREE
    refresh_trigger = RefreshTrigger.PER_TURN

    async def detect(self, context, graph_state, response_text):
        """Detect interview phase from graph state.

        Args:
            context: Pipeline context
            graph_state: Current knowledge graph state
            response_text: User's response text (not used)

        Returns:
            Dict with single key: {self.signal_name: "early" | "mid" | "late"}
        """
        # Extract graph state metrics
        node_count = getattr(graph_state, "node_count", 0)
        max_depth = getattr(graph_state, "max_depth", 0)
        orphan_count = self._get_orphan_count(graph_state)

        # Determine phase
        phase = self._determine_phase(node_count, max_depth, orphan_count)

        return {self.signal_name: phase}

    def _determine_phase(
        self, node_count: int, max_depth: int, orphan_count: int
    ) -> str:
        """Determine interview phase from graph metrics.

        Args:
            node_count: Total number of nodes
            max_depth: Maximum graph depth
            orphan_count: Number of orphan nodes

        Returns:
            Phase: "early" | "mid" | "late"
        """
        # Phase logic from design doc:
        # if node_count < 5:
        #     return "early"
        # elif node_count < 15 or orphan_count > 3:
        #     return "mid"
        # else:
        #     return "late"

        if node_count < 5:
            return "early"
        elif node_count < 15 or orphan_count > 3:
            return "mid"
        else:
            return "late"

    def _get_orphan_count(self, graph_state) -> int:
        """Get orphan count from graph state.

        Args:
            graph_state: Current knowledge graph state

        Returns:
            Number of orphan nodes (nodes with no connections)
        """
        # Try to get orphan_count from extended_properties first
        if hasattr(graph_state, "extended_properties"):
            orphan_count = graph_state.extended_properties.get("orphan_count")
            if orphan_count is not None:
                return orphan_count

        # Fallback: check if orphan_count exists as attribute
        if hasattr(graph_state, "orphan_count"):
            return graph_state.orphan_count

        # If not available, compute from nodes_by_type
        # This is a simplified calculation - in production would traverse graph
        if hasattr(graph_state, "nodes_by_type"):
            # Orphan nodes are typically attribute nodes with no connections
            # This is a heuristic approximation
            return 0

        return 0
