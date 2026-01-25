"""Depth calculator for element coverage via chain validation.

For each element, this module calculates depth by finding the longest connected
chain of node types among nodes linked to that element. This implements the
"chain validation" approach from the enhancement plan.

Algorithm:
1. Get all nodes linked to element (via element linking)
2. Get edges connecting these nodes (treat as undirected)
3. Build adjacency graph
4. Find longest connected path (any direction)
5. depth_score = longest_chain_length / methodology_ladder_length
"""

from typing import Dict, List, Set, Any, Optional
import structlog

from src.domain.models.knowledge_graph import KGNode, KGEdge

log = structlog.get_logger(__name__)


class DepthCalculator:
    """
    Calculates element depth via chain validation.

    For each element, finds the longest connected chain of node types
    among linked nodes, using undirected edges.
    """

    def __init__(self, methodology_ladder: Optional[List[str]] = None):
        """
        Initialize depth calculator.

        Args:
            methodology_ladder: Ordered list of node types in the methodology
                (e.g., ["attribute", "functional_consequence", ...])
                If None, uses default MEC ladder.
        """
        # Default MEC ladder if not provided
        self.methodology_ladder = methodology_ladder or [
            "attribute",
            "functional_consequence",
            "psychosocial_consequence",
            "instrumental_value",
            "terminal_value",
        ]
        self.ladder_length = len(self.methodology_ladder)

        log.info(
            "DepthCalculator initialized",
            ladder_length=self.ladder_length,
            methodology_ladder=self.methodology_ladder,
        )

    def calculate_element_depth(
        self,
        element_id: int,
        linked_nodes: List[KGNode],
        edges: List[KGEdge],
    ) -> float:
        """
        Calculate depth score for a single element via chain validation.

        Depth score = longest_connected_chain_length / methodology_ladder_length

        Example:
            linked_nodes: [node_A (attribute), node_B (psychosocial)]
            edges: [] (no connection between them)
            Result: max_chain_length = 1 (each is isolated)
            depth_score = 1/5 = 0.2

            If they WERE connected:
            edges: [A→C (functional), C→B]
            Result: max_chain_length = 3 (A→C→B)
            depth_score = 3/5 = 0.6

        Args:
            element_id: Element ID (int)
            linked_nodes: All nodes linked to this element
            edges: All edges in the graph (will filter to those connecting linked nodes)

        Returns:
            Depth score from 0.0 to 1.0
        """
        if not linked_nodes:
            return 0.0

        # If only one node, depth is 1/ladder_length
        if len(linked_nodes) == 1:
            return 1.0 / self.ladder_length

        # Build adjacency graph (undirected)
        node_ids = {node.id for node in linked_nodes}
        adjacency = self._build_undirected_adjacency(node_ids, edges)

        # Find longest connected path using DFS
        longest_chain = self._find_longest_path(adjacency)

        # Depth score = longest chain / ladder length
        depth_score = longest_chain / self.ladder_length

        log.debug(
            "element_depth_calculated",
            element_id=element_id,
            linked_nodes_count=len(linked_nodes),
            longest_chain=longest_chain,
            depth_score=depth_score,
        )

        return depth_score

    def calculate_all_elements(
        self,
        element_node_mapping: Dict[int, List[KGNode]],
        edges: List[KGEdge],
    ) -> Dict[int, Dict[str, Any]]:
        """
        Calculate depth for all elements.

        Args:
            element_node_mapping: Dict mapping element_id -> list of linked nodes
            edges: All edges in the graph

        Returns:
            Dict mapping element_id -> {
                "depth_score": float,
                "linked_node_ids": List[str],
                "types_found": List[str],
                "covered": bool
            }
        """
        results = {}

        for element_id, linked_nodes in element_node_mapping.items():
            if not linked_nodes:
                # Element not covered at all
                results[element_id] = {
                    "covered": False,
                    "linked_node_ids": [],
                    "types_found": [],
                    "depth_score": 0.0,
                }
                continue

            # Calculate depth
            depth_score = self.calculate_element_depth(element_id, linked_nodes, edges)

            # Extract metadata
            linked_node_ids = [node.id for node in linked_nodes]
            types_found = list({node.node_type for node in linked_nodes})

            results[element_id] = {
                "covered": True,
                "linked_node_ids": linked_node_ids,
                "types_found": types_found,
                "depth_score": depth_score,
            }

        return results

    def _build_undirected_adjacency(
        self,
        node_ids: Set[str],
        edges: List[KGEdge],
    ) -> Dict[str, Set[str]]:
        """
        Build undirected adjacency graph from edges.

        Only includes edges that connect nodes in the node_ids set.
        Treats all edges as undirected (adds both directions).

        Args:
            node_ids: Set of node IDs to include
            edges: All edges

        Returns:
            Dict mapping node_id -> set of adjacent node IDs
        """
        adjacency = {node_id: set() for node_id in node_ids}

        for edge in edges:
            source = edge.source_node_id
            target = edge.target_node_id

            # Only include edges where both endpoints are in our set
            if source in node_ids and target in node_ids:
                # Add undirected connection
                adjacency[source].add(target)
                adjacency[target].add(source)

        return adjacency

    def _find_longest_path(self, adjacency: Dict[str, Set[str]]) -> int:
        """
        Find longest simple path in undirected graph using DFS.

        For each node, finds the longest path starting from that node,
        tracking visited nodes to avoid cycles.

        Args:
            adjacency: Undirected adjacency dict

        Returns:
            Length of longest path (number of nodes)
        """
        if not adjacency:
            return 0

        longest = 1  # At minimum, a single node

        # Try DFS from each node as starting point
        for start_node in adjacency:
            visited = set()
            path_length = self._dfs_longest_path(start_node, adjacency, visited)
            longest = max(longest, path_length)

        return longest

    def _dfs_longest_path(
        self,
        node: str,
        adjacency: Dict[str, Set[str]],
        visited: Set[str],
    ) -> int:
        """
        DFS to find longest path starting from node.

        Args:
            node: Current node
            adjacency: Adjacency dict
            visited: Set of visited nodes (to avoid cycles)

        Returns:
            Length of longest path from this node
        """
        visited.add(node)
        max_length = 1  # Count this node

        for neighbor in adjacency[node]:
            if neighbor not in visited:
                # Recursively find longest path from neighbor
                path_length = self._dfs_longest_path(neighbor, adjacency, visited)
                max_length = max(max_length, 1 + path_length)

        # Backtrack: remove from visited so other paths can use this node
        visited.remove(node)

        return max_length

    def get_overall_depth(self, element_depths: Dict[int, Dict[str, Any]]) -> float:
        """
        Calculate overall depth across all elements.

        Overall depth = average depth_score across all elements.

        Args:
            element_depths: Dict from calculate_all_elements()

        Returns:
            Average depth score (0.0 to 1.0)
        """
        if not element_depths:
            return 0.0

        total_depth = sum(data["depth_score"] for data in element_depths.values())
        return total_depth / len(element_depths)
