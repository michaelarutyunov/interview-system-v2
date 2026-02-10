"""Node relationship signals.

These signals analyze the structural relationships of nodes
in the knowledge graph, including orphan detection and edge counts.
"""

from src.methodologies.signals.graph.node_base import NodeSignalDetector


class NodeIsOrphanSignal(NodeSignalDetector):
    """Whether a node is an orphan (no edges).

    An orphan node has no incoming or outgoing edges, meaning
    it's not connected to any other nodes in the graph.

    Namespaced signal: graph.node.is_orphan
    Cost: free (O(1) lookup from state property)
    Refresh: per_turn (updated after graph changes)
    """

    signal_name = "graph.node.is_orphan"

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
    Cost: free (O(1) lookup from state)
    Refresh: per_turn (updated after graph changes)
    """

    signal_name = "graph.node.edge_count"

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
    Cost: free (O(1) lookup from state)
    Refresh: per_turn (updated after graph changes)
    """

    signal_name = "graph.node.has_outgoing"

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
