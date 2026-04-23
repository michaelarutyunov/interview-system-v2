"""Per-methodology metric computation for the eval harness.

Loads a session's knowledge graph from SQLite and computes:
- Universal metrics: node_count, orphan_ratio, canonical_slot_coverage, total_turns
- Methodology-specific: structural_completeness, ontology_breadth, exploration_depth

The "structural completeness" concept is methodology-specific but universal in meaning:
how many root-to-resolution paths exist in the graph, proving the system achieved depth.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import aiosqlite
import yaml


@dataclass
class EvalMetrics:
    """Metrics computed from a single simulation run."""

    # Universal
    node_count: int = 0
    orphan_ratio: float = 0.0
    canonical_slot_coverage: float = 0.0
    total_turns: int = 0

    # Methodology-specific
    structural_completeness: int = 0
    max_chain_depth: int = 0
    ontology_breadth: float = 0.0
    exploration_depth: float = 0.0

    # Optional detail
    error_flag: bool = False


@dataclass
class Node:
    id: str
    node_type: str
    session_id: str


@dataclass
class Edge:
    source_id: str
    target_id: str
    edge_type: str


@dataclass
class Graph:
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    # Adjacency: node_id -> list of outgoing Edge
    adj: dict[str, list[Edge]] = field(default_factory=lambda: defaultdict(list))
    # Reverse adjacency for incoming edges
    radj: dict[str, list[Edge]] = field(default_factory=lambda: defaultdict(list))
    # node_type -> list of node_ids
    by_type: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))


# Per-methodology definitions: which node types are "roots" and "resolutions"
# structural_completeness = count of root nodes that have a path to a resolution node
METHODOLOGY_STRUCTURES = {
    "means_end_chain_v2_strict": {
        "root_types": ["attribute"],
        "resolution_types": ["terminal_value"],
    },
    "means_end_chain_v2_flex": {
        "root_types": ["attribute"],
        "resolution_types": ["terminal_value"],
    },
    "jobs_to_be_done_v2": {
        "root_types": ["job_statement"],
        "resolution_types": ["solution_approach"],
    },
    "critical_incident_v2": {
        "root_types": ["incident"],
        "resolution_types": ["emotion", "attribution", "learning", "behavior_change"],
    },
    "customer_journey_mapping_v2": {
        "root_types": ["stage"],
        "resolution_types": ["friction", "moment_of_truth"],
    },
    "repertory_grid_v2": {
        "root_types": ["construct_pole"],
        "resolution_types": ["laddered_construct"],
    },
}


def load_methodology_ontology(methodology_name: str) -> set[str]:
    """Load all node type names from a methodology YAML's ontology section."""
    config_path = Path("config/methodologies") / f"{methodology_name}.yaml"
    if not config_path.exists():
        return set()
    with open(config_path) as f:
        data = yaml.safe_load(f)
    ontology = data.get("ontology", {})
    return {n["name"] for n in ontology.get("nodes", [])}


def load_methodology_level_map(methodology_name: str) -> dict[str, int]:
    """Load {node_type: level} from methodology YAML's ontology section.

    Returns empty dict for flat ontologies (CJM, RG) where no 'level' key exists.
    """
    config_path = Path("config/methodologies") / f"{methodology_name}.yaml"
    if not config_path.exists():
        return {}
    with open(config_path) as f:
        data = yaml.safe_load(f)
    ontology = data.get("ontology", {})
    level_map: dict[str, int] = {}
    for node in ontology.get("nodes", []):
        if "level" in node:
            level_map[node["name"]] = node["level"]
    return level_map


def compute_max_chain_depth(graph: Graph, methodology_name: str) -> int:
    """Compute deepest ontology level reached from any root node.

    For hierarchical ontologies (MEC, JTBD, CIT), BFS from each root node
    and track the maximum ontology level encountered. Normalized to 1-based
    depth (e.g., MEC level 4 -> depth 4).

    Returns 0 for flat ontologies (CJM, RG) where no hierarchy is defined.
    """
    level_map = load_methodology_level_map(methodology_name)
    if not level_map:
        return 0  # Flat ontology — no hierarchy defined

    levels = sorted(set(level_map.values()))
    if not levels:
        return 0

    min_level = min(levels)
    root_types = {t for t, lvl in level_map.items() if lvl == min_level}

    max_reached_level = min_level

    for root_type in root_types:
        for node_id in graph.by_type.get(root_type, []):
            visited: set[str] = set()
            queue = [node_id]
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                node = graph.nodes.get(current)
                if node:
                    node_level = level_map.get(node.node_type, min_level)
                    if node_level > max_reached_level:
                        max_reached_level = node_level
                for nbr in _neighbors(graph, current):
                    if nbr not in visited:
                        queue.append(nbr)

    # Normalize to 1-based depth
    level_to_depth = {lvl: i + 1 for i, lvl in enumerate(levels)}
    return level_to_depth.get(max_reached_level, 0)


def _neighbors(graph: Graph, node_id: str) -> set[str]:
    """Get all neighbors of a node (undirected — follows both outgoing and incoming edges)."""
    nbrs = {edge.target_id for edge in graph.adj.get(node_id, [])}
    nbrs.update(edge.source_id for edge in graph.radj.get(node_id, []))
    return nbrs


def _has_path(graph: Graph, start: str, target_types: set[str]) -> bool:
    """Undirected BFS from start node, return True if any target_types node is reachable."""
    visited = set()
    queue = [start]
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        if graph.nodes[current].node_type in target_types:
            return True
        for nbr in _neighbors(graph, current):
            if nbr not in visited:
                queue.append(nbr)
    return False


def _shortest_path_length(
    graph: Graph, start: str, target_types: set[str]
) -> Optional[int]:
    """Undirected BFS shortest path from start to any node in target_types. None if unreachable."""
    visited = {start}
    queue = [(start, 0)]
    while queue:
        current, dist = queue.pop(0)
        if graph.nodes[current].node_type in target_types:
            return dist
        for nbr in _neighbors(graph, current):
            if nbr not in visited:
                visited.add(nbr)
                queue.append((nbr, dist + 1))
    return None


async def load_session_graph(db_path: str, session_id: str) -> Graph:
    """Load all nodes and edges for a session into an in-memory Graph."""
    graph = Graph()
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, node_type, session_id FROM kg_nodes WHERE session_id = ? AND superseded_by IS NULL",
            (session_id,),
        ) as cur:
            async for row in cur:
                node = Node(
                    id=row["id"],
                    node_type=row["node_type"],
                    session_id=row["session_id"],
                )
                graph.nodes[node.id] = node
                graph.by_type[node.node_type].append(node.id)

        async with db.execute(
            "SELECT source_node_id, target_node_id, edge_type FROM kg_edges WHERE session_id = ?",
            (session_id,),
        ) as cur:
            async for row in cur:
                src, tgt = row["source_node_id"], row["target_node_id"]
                if src in graph.nodes and tgt in graph.nodes:
                    edge = Edge(
                        source_id=src, target_id=tgt, edge_type=row["edge_type"]
                    )
                    graph.edges.append(edge)
                    graph.adj[src].append(edge)
                    graph.radj[tgt].append(edge)

    return graph


async def load_session_info(db_path: str, session_id: str) -> dict:
    """Load session metadata."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, methodology, concept_id, turn_count, status FROM sessions WHERE id = ?",
            (session_id,),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else {}


async def load_canonical_slot_coverage(
    db_path: str, session_id: str, methodology_name: str
) -> float:
    """Compute canonical slot coverage: active slots / total ontology node types."""
    ontology_types = load_methodology_ontology(methodology_name)
    if not ontology_types:
        return 0.0

    active_count = 0
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT COUNT(DISTINCT node_type) FROM canonical_slots WHERE session_id = ? AND status = 'active'",
            (session_id,),
        ) as cur:
            row = await cur.fetchone()
            active_count = row[0] if row else 0

    return active_count / len(ontology_types) if ontology_types else 0.0


def compute_graph_metrics(graph: Graph, methodology_name: str) -> dict:
    """Compute universal and methodology-specific graph metrics."""
    node_count = len(graph.nodes)
    if node_count == 0:
        return {
            "node_count": 0,
            "orphan_ratio": 0.0,
            "structural_completeness": 0,
            "ontology_breadth": 0.0,
            "exploration_depth": 0.0,
        }

    # Nodes with no edges (neither source nor target)
    connected = set()
    for edge in graph.edges:
        connected.add(edge.source_id)
        connected.add(edge.target_id)
    orphan_ratio = 1.0 - (len(connected) / node_count)

    # Ontology breadth: how many distinct node types appeared
    observed_types = set(graph.by_type.keys())
    ontology_types = load_methodology_ontology(methodology_name)
    ontology_breadth = (
        len(observed_types & ontology_types) / len(ontology_types)
        if ontology_types
        else 0.0
    )

    # Structural completeness + exploration depth
    struct_def = METHODOLOGY_STRUCTURES.get(methodology_name, {})
    root_types = set(struct_def.get("root_types", []))
    resolution_types = set(struct_def.get("resolution_types", []))

    structural_completeness = 0
    path_lengths = []

    if root_types and resolution_types:
        for root_type in root_types:
            for node_id in graph.by_type.get(root_type, []):
                if _has_path(graph, node_id, resolution_types):
                    structural_completeness += 1
                    pl = _shortest_path_length(graph, node_id, resolution_types)
                    if pl is not None:
                        path_lengths.append(pl)

    exploration_depth = sum(path_lengths) / len(path_lengths) if path_lengths else 0.0

    max_chain_depth = compute_max_chain_depth(graph, methodology_name)

    return {
        "node_count": node_count,
        "orphan_ratio": round(orphan_ratio, 4),
        "structural_completeness": structural_completeness,
        "max_chain_depth": max_chain_depth,
        "ontology_breadth": round(ontology_breadth, 4),
        "exploration_depth": round(exploration_depth, 2),
    }


async def compute_metrics(db_path: str, session_id: str) -> EvalMetrics:
    """Compute all metrics for a single simulation run."""
    metrics = EvalMetrics()

    session_info = await load_session_info(db_path, session_id)
    if not session_info:
        metrics.error_flag = True
        return metrics

    methodology = session_info.get("methodology", "")
    metrics.total_turns = session_info.get("turn_count", 0) or 0

    graph = await load_session_graph(db_path, session_id)
    graph_metrics = compute_graph_metrics(graph, methodology)

    metrics.node_count = graph_metrics["node_count"]
    metrics.orphan_ratio = graph_metrics["orphan_ratio"]
    metrics.structural_completeness = graph_metrics["structural_completeness"]
    metrics.max_chain_depth = graph_metrics["max_chain_depth"]
    metrics.ontology_breadth = graph_metrics["ontology_breadth"]
    metrics.exploration_depth = graph_metrics["exploration_depth"]
    metrics.canonical_slot_coverage = await load_canonical_slot_coverage(
        db_path, session_id, methodology
    )

    return metrics
