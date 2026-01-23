"""Graph analysis utilities for Tier-2 scorers.

These functions provide O(1) or O(log n) lookups for cluster-level metrics.
Clusters are computed via Louvain algorithm and cached per turn.

Reference: ADR-006 - Enhanced Scoring and Strategy Architecture
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

    Results are cached per turn. Cache invalidates on turn change.

    Args:
        graph: NetworkX graph representing the knowledge graph
        turn_number: Current interview turn (for cache key)

    Returns:
        Dictionary mapping node_id to cluster_id
    """
    if turn_number in _cluster_cache:
        logger.debug(f"Using cached clusters for turn {turn_number}")
        return _cluster_cache[turn_number]

    try:
        import python_louvain
        partition = python_louvain.best_partition(graph)
        _cluster_cache[turn_number] = partition
        logger.info(f"Computed {len(set(partition.values()))} clusters for turn {turn_number}")
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


def get_cluster_nodes(
    focus_node: str,
    clusters: Dict[str, int]
) -> set:
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
    focus_node: str,
    graph: nx.Graph,
    clusters: Optional[Dict[str, int]] = None
) -> float:
    """Density of the cluster containing focus_node.

    Calculates: 2 * |E| / (|V| * (|V| - 1))

    Args:
        focus_node: Node ID to calculate density for
        graph: NetworkX graph
        clusters: Optional cluster assignments (computed if None)

    Returns:
        Density value between 0.0 (no edges) and 1.0 (complete graph)
        Returns 0.0 for single-node clusters
    """
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


def cluster_size(
    focus_node: str,
    clusters: Dict[str, int]
) -> int:
    """Number of nodes in the cluster containing focus_node.

    Args:
        focus_node: Node ID to get cluster size for
        clusters: Cluster assignment dictionary

    Returns:
        Number of nodes in the cluster
    """
    return len(get_cluster_nodes(focus_node, clusters))


def largest_cluster_ratio(
    graph: nx.Graph,
    clusters: Dict[str, int]
) -> float:
    """Size of largest cluster / total nodes.

    Args:
        graph: NetworkX graph
        clusters: Cluster assignment dictionary

    Returns:
        Ratio of largest cluster size to total nodes (0-1)
    """
    if not clusters:
        return 1.0

    cluster_sizes = defaultdict(int)
    for node, cid in clusters.items():
        cluster_sizes[cid] += 1

    max_size = max(cluster_sizes.values()) if cluster_sizes else 0
    return max_size / len(clusters)


def has_peripheral_candidates(
    focus_node: str,
    graph: nx.Graph,
    clusters: Dict[str, int],
    max_hops: int = 2
) -> Tuple[int, float]:
    """Count unvisited nodes within max_hops of focus_node's cluster.

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
    focus_cluster = clusters.get(focus_node)
    cluster_nodes = get_cluster_nodes(focus_node, clusters)

    # Find nodes at cluster boundary (edges to other clusters)
    candidates = set()
    for node in cluster_nodes:
        for _, neighbor, data in graph.edges(node, data=True):
            neighbor_cluster = clusters.get(neighbor)
            if neighbor_cluster != focus_cluster:
                # Add relevance score if available
                relevance = data.get('relevance', 0.5)
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
    focus_node: str,
    graph: nx.Graph,
    clusters: Optional[Dict[str, int]] = None
) -> bool:
    """Check if any node has opposite stance to focus_node.

    Returns True if exists node where stance == -focus.stance.
    Neutral nodes (stance == 0) are ignored.

    Args:
        focus_node: Node ID to check stance against
        graph: NetworkX graph with stance attribute on nodes
        clusters: Optional cluster assignments (not used, kept for interface consistency)

    Returns:
        True if an opposite-stance node exists, False otherwise
    """
    # Get stance from node data
    if hasattr(graph.nodes[focus_node], 'stance'):
        focus_stance = graph.nodes[focus_node]['stance']
    else:
        # Fallback: check in node data dict
        focus_stance = graph.nodes.get(focus_node, {}).get('stance', 0)

    # Neutral focus has no opposite
    if focus_stance == 0:
        return False

    target_stance = -focus_stance

    # Search for opposite stance
    for node, data in graph.nodes(data=True):
        node_stance = data.get('stance', 0)
        if node_stance == target_stance:
            return True

    return False


def median_cluster_degree(
    focus_node: str,
    graph: nx.Graph,
    clusters: Dict[str, int]
) -> float:
    """Median degree of nodes in focus_node's cluster.

    Args:
        focus_node: Node ID to calculate median degree for
        graph: NetworkX graph
        clusters: Cluster assignment dictionary

    Returns:
        Median degree of nodes in the cluster (float for precision)
    """
    nodes = get_cluster_nodes(focus_node, clusters)

    if not nodes:
        return 0.0

    degrees = [graph.degree(n) for n in nodes]
    degrees.sort()

    n = len(degrees)
    if n % 2 == 0:
        return (degrees[n//2 - 1] + degrees[n//2]) / 2
    else:
        return degrees[n//2]


def turns_since_last_cluster_jump(
    conversation_history: list,
    current_turn: int
) -> int:
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
        strategy = turn.get('strategy', {})
        if strategy.get('id') == 'bridge':
            return i

    # No bridge found, use conversation length as proxy
    return min(current_turn, len(conversation_history))


def median_degree_inside(focus_node: str, graph: nx.Graph) -> float:
    """Median degree of nodes in focus_node's cluster (alias for compatibility).

    This is an alias for median_cluster_degree for use in ClusterSaturationScorer.

    Args:
        focus_node: Node ID to calculate median degree for
        graph: NetworkX graph

    Returns:
        Median degree of nodes in the cluster
    """
    # Need clusters for this - compute on demand
    clusters = get_clusters(graph, -1)
    return median_cluster_degree(focus_node, graph, clusters)


def _local_cluster_density(focus: str, graph_state) -> float:
    """Compatibility wrapper for local_cluster_density.

    This provides a bridge for code expecting the old function signature.

    Args:
        focus: Focus node or strategy dict
        graph_state: GraphState object with graph

    Returns:
        Cluster density value
    """
    # Extract node ID from focus if it's a dict
    if isinstance(focus, dict):
        node_id = focus.get('id', focus.get('node_id'))
    else:
        node_id = focus

    if not node_id:
        return 0.0

    return local_cluster_density(node_id, graph_state.graph)


def _has_opposite_stance_node(focus: str, graph_state) -> bool:
    """Compatibility wrapper for has_opposite_stance_node.

    Args:
        focus: Focus node or strategy dict
        graph_state: GraphState object with graph

    Returns:
        True if opposite stance node exists
    """
    # Extract node ID from focus if it's a dict
    if isinstance(focus, dict):
        node_id = focus.get('id', focus.get('node_id'))
    else:
        node_id = focus

    if not node_id:
        return False

    return has_opposite_stance_node(node_id, graph_state.graph)


def _median_degree_inside(focus: str, graph_state) -> float:
    """Compatibility wrapper for median_degree_inside.

    Args:
        focus: Focus node or strategy dict
        graph_state: GraphState object with graph

    Returns:
        Median degree in focus cluster
    """
    return median_degree_inside(focus, graph_state)


def _cluster_size(focus: str, graph_state) -> int:
    """Compatibility wrapper for cluster_size.

    Args:
        focus: Focus node or strategy dict
        graph_state: GraphState object with graph

    Returns:
        Number of nodes in focus cluster
    """
    # Extract node ID from focus if it's a dict
    if isinstance(focus, dict):
        node_id = focus.get('id', focus.get('node_id'))
    else:
        node_id = focus

    if not node_id:
        return 0

    clusters = get_clusters(graph_state.graph, -1)
    return cluster_size(node_id, clusters)


def _largest_cluster_ratio(graph_state) -> float:
    """Compatibility wrapper for largest_cluster_ratio.

    Args:
        graph_state: GraphState object with graph

    Returns:
        Ratio of largest cluster to total nodes
    """
    clusters = get_clusters(graph_state.graph, -1)
    return largest_cluster_ratio(graph_state.graph, clusters)
