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
    description = "Depth of the longest causal chain. Low values (0-1) indicate surface-level exploration, moderate (2-3) indicate reaching consequences or values, high (4+) indicate deep value exploration."
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
    description = "Average depth across all chains. Indicates overall depth of exploration. Values below 2 suggest surface-focused conversation, 2-3 indicate balanced depth, above 3 indicate consistently deep exploration."
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
    description = "Depth of each specific element/node. Used to identify which concepts are at surface vs deep levels. Helps select focus concepts for deepening or broadening."
    cost_tier = SignalCostTier.FREE
    refresh_trigger = RefreshTrigger.PER_TURN

    async def detect(self, context, graph_state, response_text):
        """Return depth by element from depth metrics."""
        # depth_by_element is Dict[str, int] - element_id → depth
        return {self.signal_name: graph_state.depth_metrics.depth_by_element}
