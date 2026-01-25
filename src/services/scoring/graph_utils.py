"""Graph analysis utilities for Tier-2 scorers.

These functions provide O(1) or O(log n) lookups for cluster-level metrics.
Clusters are computed via Louvain algorithm and cached per turn.

Reference: ADR-006 - Enhanced Scoring and Strategy Architecture

DEPRECATION NOTICE:
The NetworkX-based functions below (get_clusters, local_cluster_density,
has_opposite_stance_node, etc.) are NOT currently used by any Tier-2 scorers.
They were part of an earlier design phase but the implementation took a different
path using simple heuristic functions that don't require full NetworkX graph
reconstruction.

Use the "simple" helper functions instead:
- get_simple_local_density() instead of local_cluster_density()
- has_opposite_stance_simple() instead of has_opposite_stance_node()
- count_peripheral_nodes_simple() instead of has_peripheral_candidates()
- calculate_mec_chain_depth() for MEC depth metrics (this one IS used)

These deprecated functions are retained for potential future use but are not
called in production code as of 2025-01-25.
"""

from typing import Dict, Optional, Tuple
import networkx as nx
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

# Cache for cluster assignments: turn_number -> {node_id -> cluster_id}
_cluster_cache: Dict[int, Dict[str, int]] = {}


def get_clusters(graph: nx.Graph, turn_number: int) -> Dict[str, int]:
    """Get Louvain cluster assignments for all nodes.

    .. DEPRECATED::
        This function is NOT currently used by any Tier-2 scorers.
        Use simple helper functions instead (get_simple_local_density, etc.).

    Results are cached per turn. Cache invalidates on turn change.

    Args:
        graph: NetworkX graph representing the knowledge graph
        turn_number: Current interview turn (for cache key)

    Returns:
        Dictionary mapping node_id to cluster_id
    """
    import warnings
    warnings.warn(
        "get_clusters() is deprecated and not used in production. "
        "Use get_simple_local_density() or other simple helpers instead.",
        DeprecationWarning,
        stacklevel=2
    )
    if turn_number in _cluster_cache:
        logger.debug(f"Using cached clusters for turn {turn_number}")
        return _cluster_cache[turn_number]

    try:
        import community  # python-louvain package

        partition = community.best_partition(graph)
        _cluster_cache[turn_number] = partition
        logger.info(
            f"Computed {len(set(partition.values()))} clusters for turn {turn_number}"
        )
        return partition
    except ImportError:
        logger.warning("python-louvain not available, using connected components")
        # Fallback: use connected components
        partition = {}
        for i, component in enumerate(nx.connected_components(graph)):
            for node in component:
                partition[node] = i
        _cluster_cache[turn_number] = partition
        return partition


def clear_cluster_cache():
    """Clear the cluster cache (call at start of new turn).

    This should be called when the graph structure changes or at the
    beginning of a new turn to ensure fresh cluster calculations.
    """
    _cluster_cache.clear()
    logger.debug("Cluster cache cleared")


def get_cluster_nodes(focus_node: str, clusters: Dict[str, int]) -> set:
    """Get all nodes in the same cluster as focus_node.

    Args:
        focus_node: Node ID to get cluster for
        clusters: Cluster assignment dictionary from get_clusters()

    Returns:
        Set of node IDs in the same cluster
    """
    focus_cluster = clusters.get(focus_node)
    if focus_cluster is None:
        return {focus_node}
    return {node for node, cid in clusters.items() if cid == focus_cluster}


def local_cluster_density(
    focus_node: str, graph: nx.Graph, clusters: Optional[Dict[str, int]] = None
) -> float:
    """Density of the cluster containing focus_node.

    .. DEPRECATED::
        This function is NOT currently used by any Tier-2 scorers.
        Use get_simple_local_density() instead.

    Calculates: 2 * |E| / (|V| * (|V| - 1))

    Args:
        focus_node: Node ID to calculate density for
        graph: NetworkX graph
        clusters: Optional cluster assignments (computed if None)

    Returns:
        Density value between 0.0 (no edges) and 1.0 (complete graph)
        Returns 0.0 for single-node clusters
    """
    import warnings
    warnings.warn(
        "local_cluster_density() is deprecated and not used in production. "
        "Use get_simple_local_density() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    if clusters is None:
        clusters = get_clusters(graph, -1)

    nodes = get_cluster_nodes(focus_node, clusters)
    n = len(nodes)

    if n <= 1:
        return 0.0

    # Count internal edges
    subgraph = graph.subgraph(nodes)
    e = subgraph.number_of_edges()

    return 2 * e / (n * (n - 1))


def cluster_size(focus_node: str, clusters: Dict[str, int]) -> int:
    """Number of nodes in the cluster containing focus_node.

    .. DEPRECATED::
        This function is NOT currently used by any Tier-2 scorers.

    Args:
        focus_node: Node ID to get cluster size for
        clusters: Cluster assignment dictionary

    Returns:
        Number of nodes in the cluster
    """
    import warnings
    warnings.warn(
        "cluster_size() is deprecated and not used in production.",
        DeprecationWarning,
        stacklevel=2
    )
    return len(get_cluster_nodes(focus_node, clusters))


def largest_cluster_ratio(graph: nx.Graph, clusters: Dict[str, int]) -> float:
    """Size of largest cluster / total nodes.

    .. DEPRECATED::
        This function is NOT currently used by any Tier-2 scorers.

    Args:
        graph: NetworkX graph
        clusters: Cluster assignment dictionary

    Returns:
        Ratio of largest cluster size to total nodes (0-1)
    """
    import warnings
    warnings.warn(
        "largest_cluster_ratio() is deprecated and not used in production.",
        DeprecationWarning,
        stacklevel=2
    )
    if not clusters:
        return 1.0

    cluster_sizes = defaultdict(int)
    for node, cid in clusters.items():
        cluster_sizes[cid] += 1

    max_size = max(cluster_sizes.values()) if cluster_sizes else 0
    return max_size / len(clusters)


def has_peripheral_candidates(
    focus_node: str, graph: nx.Graph, clusters: Dict[str, int], max_hops: int = 2
) -> Tuple[int, float]:
    """Count unvisited nodes within max_hops of focus_node's cluster.

    .. DEPRECATED::
        This function is NOT currently used by any Tier-2 scorers.
        Use count_peripheral_nodes_simple() instead.

    A peripheral candidate is a node in a different cluster that has
    an edge connecting to the focus cluster.

    Args:
        focus_node: Node ID to search from
        graph: NetworkX graph
        clusters: Cluster assignment dictionary
        max_hops: Maximum hops to search (default: 2)

    Returns:
        Tuple of (candidate_count, max_relevance) where:
        - candidate_count: Number of peripheral nodes found
        - max_relevance: Highest relevance score among candidates
    """
    import warnings
    warnings.warn(
        "has_peripheral_candidates() is deprecated and not used in production. "
        "Use count_peripheral_nodes_simple() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    focus_cluster = clusters.get(focus_node)
    cluster_nodes = get_cluster_nodes(focus_node, clusters)

    # Find nodes at cluster boundary (edges to other clusters)
    candidates = set()
    for node in cluster_nodes:
        for _, neighbor, data in graph.edges(node, data=True):
            neighbor_cluster = clusters.get(neighbor)
            if neighbor_cluster != focus_cluster:
                # Add relevance score if available
                relevance = data.get("relevance", 0.5)
                candidates.add((neighbor, relevance))

    # Filter by relevance threshold
    min_relevance = 0.3
    valid = [(n, r) for n, r in candidates if r >= min_relevance]

    if valid:
        count = len(valid)
        max_rel = max(r for _, r in valid)
        return count, max_rel

    return 0, 0.0


def has_opposite_stance_node(
    focus_node: str, graph: nx.Graph, clusters: Optional[Dict[str, int]] = None
) -> bool:
    """Check if any node has opposite stance to focus_node.

    .. DEPRECATED::
        This function is NOT currently used by any Tier-2 scorers.
        Use has_opposite_stance_simple() instead.

    Returns True if exists node where stance == -focus.stance.
    Neutral nodes (stance == 0) are ignored.

    Args:
        focus_node: Node ID to check stance against
        graph: NetworkX graph with stance attribute on nodes
        clusters: Optional cluster assignments (not used, kept for interface consistency)

    Returns:
        True if an opposite-stance node exists, False otherwise
    """
    import warnings
    warnings.warn(
        "has_opposite_stance_node() is deprecated and not used in production. "
        "Use has_opposite_stance_simple() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    # Get stance from node data
    if hasattr(graph.nodes[focus_node], "stance"):
        focus_stance = graph.nodes[focus_node]["stance"]
    else:
        # Fallback: check in node data dict
        focus_stance = graph.nodes.get(focus_node, {}).get("stance", 0)

    # Neutral focus has no opposite
    if focus_stance == 0:
        return False

    target_stance = -focus_stance

    # Search for opposite stance
    for node, data in graph.nodes(data=True):
        node_stance = data.get("stance", 0)
        if node_stance == target_stance:
            return True

    return False


def median_cluster_degree(
    focus_node: str, graph: nx.Graph, clusters: Dict[str, int]
) -> float:
    """Median degree of nodes in focus_node's cluster.

    .. DEPRECATED::
        This function is NOT currently used by any Tier-2 scorers.

    Args:
        focus_node: Node ID to calculate median degree for
        graph: NetworkX graph
        clusters: Cluster assignment dictionary

    Returns:
        Median degree of nodes in the cluster (float for precision)
    """
    import warnings
    warnings.warn(
        "median_cluster_degree() is deprecated and not used in production.",
        DeprecationWarning,
        stacklevel=2
    )
    nodes = get_cluster_nodes(focus_node, clusters)

    if not nodes:
        return 0.0

    degrees = [d for _, d in graph.degree(nodes)]  # type: ignore[arg-type]
    degrees.sort()

    n = len(degrees)
    if n % 2 == 0:
        return (degrees[n // 2 - 1] + degrees[n // 2]) / 2
    else:
        return degrees[n // 2]


def turns_since_last_cluster_jump(conversation_history: list, current_turn: int) -> int:
    """Calculate turns since the last cluster jump.

    A cluster jump occurs when the strategy switches from one cluster
    to another. This is a simplified version that counts turns since
    the last 'bridge' strategy was used.

    Args:
        conversation_history: List of turn dictionaries
        current_turn: Current turn number

    Returns:
        Number of turns since last cluster jump (0 if just jumped)
    """
    # Look backwards through history for last bridge strategy
    for i, turn in enumerate(reversed(conversation_history[-10:])):  # Last 10 turns
        strategy = turn.get("strategy", {})
        if strategy.get("id") == "bridge":
            return i

    # No bridge found, use conversation length as proxy
    return min(current_turn, len(conversation_history))


def median_degree_inside(focus_node: str, graph: nx.Graph) -> float:
    """Median degree of nodes in focus_node's cluster (alias for compatibility).

    .. DEPRECATED::
        This function is NOT currently used by any Tier-2 scorers.

    This is an alias for median_cluster_degree for use in ClusterSaturationScorer.

    Args:
        focus_node: Node ID to calculate median degree for
        graph: NetworkX graph

    Returns:
        Median degree of nodes in the cluster
    """
    import warnings
    warnings.warn(
        "median_degree_inside() is deprecated and not used in production.",
        DeprecationWarning,
        stacklevel=2
    )
    # Need clusters for this - compute on demand
    clusters = get_clusters(graph, -1)
    return median_cluster_degree(focus_node, graph, clusters)


def _local_cluster_density(focus: str, graph_state) -> float:
    """Compatibility wrapper for local_cluster_density.

    .. DEPRECATED::
        This function is NOT currently used by any Tier-2 scorers.
        Use get_simple_local_density() instead.

    This provides a bridge for code expecting the old function signature.

    Args:
        focus: Focus node or strategy dict
        graph_state: GraphState object with graph

    Returns:
        Cluster density value
    """
    import warnings
    warnings.warn(
        "_local_cluster_density() is deprecated. Use get_simple_local_density() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    # Extract node ID from focus if it's a dict
    if isinstance(focus, dict):
        node_id = focus.get("id", focus.get("node_id"))
    else:
        node_id = focus

    if not node_id:
        return 0.0

    return local_cluster_density(node_id, graph_state.graph)


def _has_opposite_stance_node(focus: str, graph_state) -> bool:
    """Compatibility wrapper for has_opposite_stance_node.

    .. DEPRECATED::
        This function is NOT currently used by any Tier-2 scorers.
        Use has_opposite_stance_simple() instead.

    Args:
        focus: Focus node or strategy dict
        graph_state: GraphState object with graph

    Returns:
        True if opposite stance node exists
    """
    import warnings
    warnings.warn(
        "_has_opposite_stance_node() is deprecated. Use has_opposite_stance_simple() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    # Extract node ID from focus if it's a dict
    if isinstance(focus, dict):
        node_id = focus.get("id", focus.get("node_id"))
    else:
        node_id = focus

    if not node_id:
        return False

    return has_opposite_stance_node(node_id, graph_state.graph)


def _median_degree_inside(focus: str, graph_state) -> float:
    """Compatibility wrapper for median_degree_inside.

    .. DEPRECATED::
        This function is NOT currently used by any Tier-2 scorers.

    Args:
        focus: Focus node or strategy dict
        graph_state: GraphState object with graph

    Returns:
        Median degree in focus cluster
    """
    import warnings
    warnings.warn(
        "_median_degree_inside() is deprecated and not used in production.",
        DeprecationWarning,
        stacklevel=2
    )
    return median_degree_inside(focus, graph_state)


def _cluster_size(focus: str, graph_state) -> int:
    """Compatibility wrapper for cluster_size.

    .. DEPRECATED::
        This function is NOT currently used by any Tier-2 scorers.

    Args:
        focus: Focus node or strategy dict
        graph_state: GraphState object with graph

    Returns:
        Number of nodes in focus cluster
    """
    import warnings
    warnings.warn(
        "_cluster_size() is deprecated and not used in production.",
        DeprecationWarning,
        stacklevel=2
    )
    # Extract node ID from focus if it's a dict
    if isinstance(focus, dict):
        node_id = focus.get("id", focus.get("node_id"))
    else:
        node_id = focus

    if not node_id:
        return 0

    clusters = get_clusters(graph_state.graph, -1)
    return cluster_size(node_id, clusters)


def _largest_cluster_ratio(graph_state) -> float:
    """Compatibility wrapper for largest_cluster_ratio.

    .. DEPRECATED::
        This function is NOT currently used by any Tier-2 scorers.

    Args:
        graph_state: GraphState object with graph

    Returns:
        Ratio of largest cluster to total nodes
    """
    import warnings
    warnings.warn(
        "_largest_cluster_ratio() is deprecated and not used in production.",
        DeprecationWarning,
        stacklevel=2
    )
    clusters = get_clusters(graph_state.graph, -1)
    return largest_cluster_ratio(graph_state.graph, clusters)


def get_simple_local_density(
    focus_node_id: str, graph_state, recent_nodes: list
) -> float:
    """Get local cluster density approximation without NetworkX graph.

    This is a simplified version that works with the data available
    in graph_state and recent_nodes, without requiring the full NetworkX graph.

    Args:
        focus_node_id: Node ID to calculate density for
        graph_state: GraphState with node/edge counts
        recent_nodes: List of recent node dicts with connected_to info

    Returns:
        Density value between 0.0 and 1.0
    """
    if not focus_node_id or not recent_nodes:
        return 0.0

    # Find the focus node in recent_nodes
    focus_node = None
    for node in recent_nodes:
        if node.get("id") == focus_node_id or node.get("node_id") == focus_node_id:
            focus_node = node
            break

    if not focus_node:
        return 0.0

    # Count connections (using connected_to if available)
    connections = focus_node.get("connected_to", [])
    if not connections and "edges" in focus_node:
        connections = [e.get("target") for e in focus_node.get("edges", [])]

    cluster_size = len(connections) + 1  # +1 for the node itself
    if cluster_size < 2:
        return 0.0

    # Density approximation: edge_count / (n * (n-1))
    # Use graph_state.edge_count as a proxy for cluster edges
    max_edges = cluster_size * (cluster_size - 1)
    actual_edges = min(
        cluster_size,
        graph_state.edge_count // max(1, graph_state.node_count // cluster_size),
    )

    if max_edges > 0:
        return min(1.0, actual_edges / max_edges)
    return 0.0


def has_opposite_stance_simple(focus_node_id: str, recent_nodes: list) -> bool:
    """Check if there's a node with opposite stance without NetworkX graph.

    Args:
        focus_node_id: Node ID to check against
        recent_nodes: List of recent node dicts with stance field

    Returns:
        True if a node with opposite stance exists
    """
    if not focus_node_id or not recent_nodes:
        return False

    # Get stance of focus node
    focus_stance = None
    for node in recent_nodes:
        if node.get("id") == focus_node_id or node.get("node_id") == focus_node_id:
            focus_stance = node.get("stance")
            break

    if focus_stance is None or focus_stance == 0:
        return False

    # Check for opposite stance
    for node in recent_nodes:
        node_stance = node.get("stance")
        if node_stance and node_stance == -focus_stance:
            return True

    return False


def count_peripheral_nodes_simple(
    focus_node_id: str, graph_state, recent_nodes: list
) -> int:
    """Count peripheral nodes without NetworkX graph.

    Peripheral nodes are those with lower connectivity (fewer edges).
    This is a simplified approximation.

    Args:
        focus_node_id: Focus node ID
        graph_state: GraphState with counts
        recent_nodes: List of recent node dicts

    Returns:
        Count of peripheral nodes
    """
    if not recent_nodes:
        return 0

    # Calculate average degree
    degrees = []
    for node in recent_nodes:
        connections = node.get("connected_to", [])
        if not connections and "edges" in node:
            connections = [e.get("target") for e in node.get("edges", [])]
        degrees.append(len(connections))

    if not degrees:
        return 0

    avg_degree = sum(degrees) / len(degrees)

    # Count nodes with degree less than average (peripheral)
    peripheral_count = sum(1 for d in degrees if d < avg_degree and d > 0)

    return peripheral_count


def calculate_mec_chain_depth(
    edges: list, nodes: list, methodology: str = "means_end_chain"
) -> dict:
    """Calculate MEC (Means-End Chain) depth metrics from graph data.

    Performs BFS traversal from root nodes (attributes) to leaf nodes
    (terminal_values) to measure actual chain lengths.

    Per bead tud (P3): Implement actual chain length calculation for depth scoring.
    Replaces edge_count/node_count heuristic in DepthBreadthBalanceScorer.

    Args:
        edges: List of edge dicts with source_node_id, target_node_id
        nodes: List of node dicts with id, node_type fields
        methodology: Methodology name (determines node type hierarchy)

    Returns:
        Dict with:
        - max_chain_length: Longest root-to-leaf path (number of edges)
        - avg_chain_length: Average of all root-to-leaf path lengths
        - chain_count: Number of distinct chains found
        - complete_chains: Number of chains reaching terminal values
    """
    if not edges or not nodes:
        return {
            "max_chain_length": 0.0,
            "avg_chain_length": 0.0,
            "chain_count": 0,
            "complete_chains": 0,
        }

    # Build adjacency list: {node_id: [child_ids...]}
    adj = {}
    reverse_adj = {}  # For finding roots (nodes with no incoming edges)
    node_types = {}

    for edge in edges:
        source = edge.get("source_node_id")
        target = edge.get("target_node_id")
        if source and target:
            adj.setdefault(source, []).append(target)
            reverse_adj.setdefault(target, []).append(source)

    for node in nodes:
        node_id = node.get("id")
        node_type = node.get("node_type", "")
        if node_id:
            node_types[node_id] = node_type
            # Ensure all nodes exist in adj
            adj.setdefault(node_id, [])

    # MEC node type hierarchy (for means_end_chain methodology)
    # attribute → functional_consequence → psychosocial_consequence
    # → instrumental_value → terminal_value
    root_types = {"attribute"}
    leaf_types = {"instrumental_value", "terminal_value"}

    # Find root nodes (no incoming edges or root type)
    roots = []
    for node_id in node_types:
        if node_id not in reverse_adj:  # No incoming edges
            roots.append(node_id)
        elif node_types.get(node_id) in root_types:
            roots.append(node_id)

    # Find leaf nodes (no outgoing edges or leaf type)
    leaves = []
    for node_id in node_types:
        if not adj.get(node_id):  # No outgoing edges
            leaves.append(node_id)
        elif node_types.get(node_id) in leaf_types:
            leaves.append(node_id)

    if not roots or not leaves:
        # No chains found
        return {
            "max_chain_length": 0.0,
            "avg_chain_length": 0.0,
            "chain_count": 0,
            "complete_chains": 0,
        }

    # BFS from each root to find all paths to leaves
    chain_lengths = []
    complete_chain_lengths = []

    for root in roots:
        # BFS to all reachable leaves
        queue = [(root, 0)]  # (node, distance_from_root)
        visited = {root}

        while queue:
            current, dist = queue.pop(0)

            # Check if this is a leaf node
            if current in leaves:
                chain_lengths.append(dist)
                if node_types.get(current) in leaf_types:
                    complete_chain_lengths.append(dist)
                continue

            # Explore neighbors
            for neighbor in adj.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, dist + 1))

    if not chain_lengths:
        return {
            "max_chain_length": 0.0,
            "avg_chain_length": 0.0,
            "chain_count": 0,
            "complete_chains": 0,
        }

    return {
        "max_chain_length": max(chain_lengths),
        "avg_chain_length": sum(chain_lengths) / len(chain_lengths),
        "chain_count": len(chain_lengths),
        "complete_chains": len(complete_chain_lengths),
    }
