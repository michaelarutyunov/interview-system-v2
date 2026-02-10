"""Graph structure signals - node count, edge count, orphans."""

from src.methodologies.signals.common import SignalDetector


class GraphNodeCountSignal(SignalDetector):
    """Number of nodes in the graph.

    Namespaced signal: graph.node_count
    Cost: free (O(1) lookup)
    Refresh: per_turn (cached on graph update)
    """

    signal_name = "graph.node_count"
    description = "Total number of concepts extracted. Indicates breadth of coverage. Low counts (<5) suggest early exploration, higher counts (>10) indicate substantial coverage."

    async def detect(self, context, graph_state, response_text):
        """Return node count from graph state."""
        return {self.signal_name: graph_state.node_count}


class GraphEdgeCountSignal(SignalDetector):
    """Number of edges in the graph.

    Namespaced signal: graph.edge_count
    Cost: free (O(1) lookup)
    Refresh: per_turn (cached on graph update)
    """

    signal_name = "graph.edge_count"
    description = "Total number of relationships between concepts. Edge density (edges/nodes) indicates how well-connected concepts are. Low density suggests isolated concepts, high density indicates rich relationships."

    async def detect(self, context, graph_state, response_text):
        """Return edge count from graph state."""
        return {self.signal_name: graph_state.edge_count}


class OrphanCountSignal(SignalDetector):
    """Number of orphaned nodes (no relationships).

    Namespaced signal: graph.orphan_count
    Cost: free (O(1) lookup)
    Refresh: per_turn (cached on graph update)
    """

    signal_name = "graph.orphan_count"
    description = "Number of isolated concepts with no connections to other concepts. High counts suggest opportunities to clarify relationships between mentioned concepts."

    async def detect(self, context, graph_state, response_text):
        """Return orphan count from graph state."""
        return {self.signal_name: graph_state.orphan_count}
