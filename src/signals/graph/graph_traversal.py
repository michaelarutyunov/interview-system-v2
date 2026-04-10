"""Shared graph traversal utilities for signal detectors.

Extracted from ChainCompletionSignal for reuse by ChainTopologySignalDetector
and other graph-walking signal detectors.

All functions are synchronous — they operate on in-memory node/edge lists
already loaded from the database by the calling signal detector.
"""

from collections import deque
from typing import Any, Dict, List, Set


def build_adjacency_list(nodes: List[Any], edges: List[Any]) -> Dict[str, List[str]]:
    """Build forward adjacency list from edges (source -> targets).

    Args:
        nodes: List of node objects with `.id` attribute.
        edges: List of edge objects with `.source_node_id` and `.target_node_id`.

    Returns:
        Dict mapping source_node_id -> list of target_node_ids.
    """
    adj_list: Dict[str, List[str]] = {node.id: [] for node in nodes}
    for edge in edges:
        if edge.source_node_id in adj_list:
            adj_list[edge.source_node_id].append(edge.target_node_id)
    return adj_list


def build_reverse_adjacency_list(
    nodes: List[Any], edges: List[Any]
) -> Dict[str, List[str]]:
    """Build reverse adjacency list (target -> sources / incoming edges).

    Args:
        nodes: List of node objects with `.id` attribute.
        edges: List of edge objects with `.source_node_id` and `.target_node_id`.

    Returns:
        Dict mapping target_node_id -> list of source_node_ids.
    """
    adj_list: Dict[str, List[str]] = {node.id: [] for node in nodes}
    for edge in edges:
        if edge.target_node_id in adj_list:
            adj_list[edge.target_node_id].append(edge.source_node_id)
    return adj_list


def get_node_type_map(nodes: List[Any]) -> Dict[str, str]:
    """Build node_id -> node_type mapping.

    Args:
        nodes: List of node objects with `.id` and `.node_type` attributes.

    Returns:
        Dict mapping node_id -> node_type string.
    """
    return {node.id: node.node_type for node in nodes}


def bfs_to_target(
    start_node_id: str,
    adj_list: Dict[str, List[str]],
    target_types: Set[str],
    node_type_map: Dict[str, str],
) -> bool:
    """BFS from start node to check if path to any target type exists.

    Args:
        start_node_id: Starting node ID.
        adj_list: Forward adjacency list (from build_adjacency_list).
        target_types: Set of node_type strings that count as targets.
        node_type_map: node_id -> node_type mapping (from get_node_type_map).

    Returns:
        True if a path exists from start to any node whose type is in target_types.
    """
    visited: Set[str] = set()
    queue = deque([start_node_id])
    visited.add(start_node_id)

    while queue:
        current_id = queue.popleft()

        current_type = node_type_map.get(current_id)
        if current_type in target_types:
            return True

        for neighbor_id in adj_list.get(current_id, []):
            if neighbor_id not in visited:
                visited.add(neighbor_id)
                queue.append(neighbor_id)

    return False


def bfs_reachable(
    start_node_id: str,
    adj_list: Dict[str, List[str]],
) -> Dict[str, int]:
    """BFS from start node, returning shortest path distance to all reachable nodes.

    Args:
        start_node_id: Starting node ID.
        adj_list: Adjacency list (forward or reverse).

    Returns:
        Dict mapping reachable_node_id -> distance in edges from start.
        Start node is included with distance 0.
    """
    distances: Dict[str, int] = {start_node_id: 0}
    queue = deque([start_node_id])

    while queue:
        current_id = queue.popleft()
        current_dist = distances[current_id]
        for neighbor_id in adj_list.get(current_id, []):
            if neighbor_id not in distances:
                distances[neighbor_id] = current_dist + 1
                queue.append(neighbor_id)

    return distances
