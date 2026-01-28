"""Utility functions for Means-End Chain methodology."""

from typing import Dict, List


def calculate_mec_chain_depth(
    edges: List[Dict], nodes: List[Dict], methodology: str = "means_end_chain"
) -> Dict:
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
