"""Graph coverage signals - breadth, missing terminal values."""

from src.methodologies.signals.common import (
    SignalDetector,
    SignalCostTier,
    RefreshTrigger,
)


class CoverageBreadthSignal(SignalDetector):
    """How well different MEC element types are covered.

    Namespaced signal: graph.coverage_breadth
    Cost: low (O(n) where n is number of element types)
    Refresh: per_turn (cached on graph update)

    For MEC, we track 3 categories: attributes, consequences, values.
    Returns a float between 0-1 indicating coverage breadth.
    """

    signal_name = "graph.coverage_breadth"
    cost_tier = SignalCostTier.LOW
    refresh_trigger = RefreshTrigger.PER_TURN

    async def detect(self, context, graph_state, response_text):
        """Calculate coverage breadth from nodes_by_type."""
        nodes_by_type = graph_state.nodes_by_type

        # For MEC, we track: attributes, consequences, values
        explored_count = 0
        total_categories = 3

        # Check attributes
        if nodes_by_type.get("attribute", 0) > 0:
            explored_count += 1

        # Check consequences (functional + psychosocial)
        consequence_count = nodes_by_type.get(
            "functional_consequence", 0
        ) + nodes_by_type.get("psychosocial_consequence", 0)
        if consequence_count > 0:
            explored_count += 1

        # Check values (instrumental + terminal)
        value_count = nodes_by_type.get("instrumental_value", 0) + nodes_by_type.get(
            "terminal_value", 0
        )
        if value_count > 0:
            explored_count += 1

        breadth = explored_count / total_categories if total_categories > 0 else 0
        return {self.signal_name: breadth}


class MissingTerminalValueSignal(SignalDetector):
    """Whether the graph is missing terminal (end-chain) values.

    Namespaced signal: graph.missing_terminal_value
    Cost: free (O(1) lookup)
    Refresh: per_turn (cached on graph update)

    Returns True if there are chains without terminal values.
    """

    signal_name = "graph.missing_terminal_value"
    cost_tier = SignalCostTier.FREE
    refresh_trigger = RefreshTrigger.PER_TURN

    async def detect(self, context, graph_state, response_text):
        """Check if graph has missing terminal values."""
        nodes_by_type = graph_state.nodes_by_type

        # Check if we have any terminal or instrumental values
        terminal_count = nodes_by_type.get("terminal_value", 0)
        instrumental_count = nodes_by_type.get("instrumental_value", 0)
        has_values = (terminal_count + instrumental_count) > 0

        # Also check depth - if we have nodes but no deep chains, likely missing terminal values
        has_depth = graph_state.depth_metrics.max_depth > 0

        # Missing terminal value if we have depth but no values
        missing = has_depth and not has_values

        return {self.signal_name: missing}
