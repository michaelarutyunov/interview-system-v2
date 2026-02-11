"""Graph chain completion signal - counts complete causal chains from level 1 to terminal."""

from collections import deque
from typing import Any, Dict, List, Set

from src.core.exceptions import ConfigurationError, GraphError
from src.core.schema_loader import load_methodology
from src.methodologies.signals.signal_base import SignalDetector


class ChainCompletionSignal(SignalDetector):
    """Count complete causal chains from level 1 nodes to terminal nodes.

    Namespaced signal: graph.chain_completion
    Cost: medium (O(V+E) BFS traversal)
    Refresh: per_turn (cached on graph update)

    Uses BFS to find paths from level 1 nodes to terminal nodes.
    Returns dict with:
        - complete_chain_count: Number of level 1 nodes that reach terminal
        - has_complete_chain: Boolean indicating if any complete chain exists
        - level_1_node_count: Total number of level 1 nodes

    Example:
        Level 1 nodes: [A, B, C]
        Terminal nodes: [X, Y, Z]
        Chains: A→...→X, B→...→Y (C doesn't reach terminal)
        Result: {
            "complete_chain_count": 2,
            "has_complete_chain": True,
            "level_1_node_count": 3
        }
    """

    signal_name = "graph.chain_completion"
    description = "Whether complete causal chains exist from level 1 to terminal nodes. has_complete_chain=true means at least one chain reaches values, false means we're still mid-chain. complete_chain_count shows how many level-1 chains are complete."

    async def detect(self, context: Any, graph_state: Any, response_text: str):
        """Count complete chains from level 1 to terminal nodes."""
        # Get methodology name from context
        methodology_name = getattr(context, "methodology", "means_end_chain")

        # Load methodology schema to get terminal node types and level info
        try:
            schema = load_methodology(methodology_name)
        except Exception as e:
            raise ConfigurationError(
                f"ChainCompletionSignal failed to load methodology schema "
                f"'{methodology_name}': {e}"
            ) from e

        # Get terminal node types from schema
        terminal_types = set(schema.get_terminal_node_types())

        # Get level 1 node types (nodes with level=1 in ontology)
        level_1_types = set()
        if schema.ontology:
            for nt in schema.ontology.nodes:
                if nt.level == 1:
                    level_1_types.add(nt.name)

        # If no terminal or level 1 types defined, return zeros
        if not terminal_types or not level_1_types:
            return {
                self.signal_name: {
                    "complete_chain_count": 0,
                    "has_complete_chain": False,
                    "level_1_node_count": 0,
                }
            }

        # Get nodes and edges from graph
        # We need to access the actual graph nodes and edges
        # The graph_state doesn't contain the full graph, so we need to load it
        nodes = await self._get_session_nodes(context)
        edges = await self._get_session_edges(context)

        if not nodes or not edges:
            return {
                self.signal_name: {
                    "complete_chain_count": 0,
                    "has_complete_chain": False,
                    "level_1_node_count": 0,
                }
            }

        # Build adjacency list for BFS
        adj_list = self._build_adjacency_list(nodes, edges)

        # Filter level 1 nodes
        level_1_nodes = [n for n in nodes if n.node_type in level_1_types]
        level_1_node_count = len(level_1_nodes)

        # Count chains that reach terminal nodes
        complete_chain_count = 0
        for start_node in level_1_nodes:
            if self._bfs_to_terminal(start_node.id, adj_list, terminal_types, nodes):
                complete_chain_count += 1

        has_complete_chain = complete_chain_count > 0

        return {
            self.signal_name: {
                "complete_chain_count": complete_chain_count,
                "has_complete_chain": has_complete_chain,
                "level_1_node_count": level_1_node_count,
            }
        }

    async def _get_session_nodes(self, context: Any) -> List[Any]:
        """Get all nodes for the session."""
        # Try to get nodes from context properties
        session_id = getattr(context, "session_id", None)
        if not session_id:
            raise GraphError(
                "ChainCompletionSignal failed to load nodes: session_id is None"
            )

        # Access the graph repository directly
        try:
            from src.persistence.repositories.graph_repo import GraphRepository
            from src.persistence.database import get_db_connection

            repo = GraphRepository(await get_db_connection())
            return await repo.get_nodes_by_session(session_id)
        except Exception as e:
            raise GraphError(
                f"ChainCompletionSignal failed to load nodes for session "
                f"'{session_id}': {e}"
            ) from e

    async def _get_session_edges(self, context: Any) -> List[Any]:
        """Get all edges for the session."""
        session_id = getattr(context, "session_id", None)
        if not session_id:
            raise GraphError(
                "ChainCompletionSignal failed to load edges: session_id is None"
            )

        # Access the graph repository directly
        try:
            from src.persistence.repositories.graph_repo import GraphRepository
            from src.persistence.database import get_db_connection

            repo = GraphRepository(await get_db_connection())
            return await repo.get_edges_by_session(session_id)
        except Exception as e:
            raise GraphError(
                f"ChainCompletionSignal failed to load edges for session "
                f"'{session_id}': {e}"
            ) from e

    def _build_adjacency_list(
        self, nodes: List[Any], edges: List[Any]
    ) -> Dict[str, List[str]]:
        """Build adjacency list from nodes and edges.

        Args:
            nodes: List of KGNode objects
            edges: List of KGEdge objects

        Returns:
            Dict mapping node_id to list of neighbor node_ids
        """
        adj_list = {node.id: [] for node in nodes}

        for edge in edges:
            if edge.source_node_id in adj_list:
                adj_list[edge.source_node_id].append(edge.target_node_id)

        return adj_list

    def _bfs_to_terminal(
        self,
        start_node_id: str,
        adj_list: Dict[str, List[str]],
        terminal_types: Set[str],
        nodes: List[Any],
    ) -> bool:
        """BFS from start node to check if path to terminal exists.

        Args:
            start_node_id: Starting node ID
            adj_list: Adjacency list of the graph
            terminal_types: Set of terminal node type names
            nodes: List of all nodes (to look up node types)

        Returns:
            True if path from start to terminal node exists
        """
        # Create node_id -> node_type mapping
        node_type_map = {node.id: node.node_type for node in nodes}

        # BFS
        visited = set()
        queue = deque([start_node_id])
        visited.add(start_node_id)

        while queue:
            current_id = queue.popleft()

            # Check if current node is terminal
            current_type = node_type_map.get(current_id)
            if current_type in terminal_types:
                return True

            # Add neighbors to queue
            for neighbor_id in adj_list.get(current_id, []):
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append(neighbor_id)

        return False
