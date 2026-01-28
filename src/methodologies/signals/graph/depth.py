"""Graph depth signals - max depth, average depth, depth by element."""

from src.methodologies.signals.common import (
    SignalDetector,
    SignalCostTier,
    RefreshTrigger,
)


class GraphMaxDepthSignal(SignalDetector):
    """Maximum chain depth in the graph.

    Namespaced signal: graph.max_depth
    Cost: free (O(1) lookup)
    Refresh: per_turn (cached on graph update)

    Example:
        A → B → C has depth 2 (2 edges from root to leaf)
    """

    signal_name = "graph.max_depth"
    cost_tier = SignalCostTier.FREE
    refresh_trigger = RefreshTrigger.PER_TURN

    async def detect(self, context, graph_state, response_text):
        """Return max depth from depth metrics."""
        return {self.signal_name: graph_state.depth_metrics.max_depth}


class GraphAvgDepthSignal(SignalDetector):
    """Average depth of all nodes in the graph.

    Namespaced signal: graph.avg_depth
    Cost: free (O(1) lookup)
    Refresh: per_turn (cached on graph update)
    """

    signal_name = "graph.avg_depth"
    cost_tier = SignalCostTier.FREE
    refresh_trigger = RefreshTrigger.PER_TURN

    async def detect(self, context, graph_state, response_text):
        """Return average depth from depth metrics."""
        return {self.signal_name: graph_state.depth_metrics.avg_depth}


class DepthByElementSignal(SignalDetector):
    """Depth of each element in the graph.

    Namespaced signal: graph.depth_by_element
    Cost: free (O(1) lookup)
    Refresh: per_turn (cached on graph update)

    Returns a dict mapping element_id → depth.
    """

    signal_name = "graph.depth_by_element"
    cost_tier = SignalCostTier.FREE
    refresh_trigger = RefreshTrigger.PER_TURN

    async def detect(self, context, graph_state, response_text):
        """Return depth by element from depth metrics."""
        # depth_by_element is Dict[str, int] - element_id → depth
        return {self.signal_name: graph_state.depth_metrics.depth_by_element}
