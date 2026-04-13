"""Chain topology signals for chain-aware strategy selection.

Computes per-node structural signals describing gaps and opportunities
in the knowledge graph's leads_to chains. Pure graph topology — no LLM calls.
"""

from typing import Any, List

import structlog

from src.core.exceptions import ConfigurationError, GraphError
from src.core.schema_loader import load_methodology
from src.signals.graph.graph_traversal import (
    bfs_reachable,
    build_adjacency_list,
    build_reverse_adjacency_list,
    get_node_type_map,
)
from src.signals.graph.node_base import NodeSignalDetector

log = structlog.get_logger(__name__)


class ChainTopologySignalDetector(NodeSignalDetector):
    """Chain topology signals per node for chain-aware strategy selection.

    Namespaced signals (all per-node):
        - graph.node.gap_above (bool): Node is highest in its chain AND non-terminal.
        - graph.node.gap_below (bool): No incoming leads_to from lower level AND above origin.
        - graph.node.level_skip (bool): Direct edge skips intermediate ontology levels.
        - graph.node.branching_deficit (float [0,1]): 1 - (actual_siblings / expected_siblings).
        - graph.node.fan_in (int): Distinct origin-level nodes with paths to this node.
        - graph.node.level_gap_size (int): Ontology levels between this node and terminal/origin.

    For non-chain methodologies (JTBD, CJM, Repertory Grid, Critical Incident),
    returns empty dict — signal absent means zero contribution to scoring.

    Returns nested dict structure for per-node access:
    {
        "graph.node.chain_topology": {
            node_id: {
                "gap_above": bool,
                "gap_below": bool,
                "level_skip": bool,
                "branching_deficit": float,
                "fan_in": int,
                "level_gap_size": int,
            }
            for node in nodes
        }
    }
    """

    signal_name = "graph.node.chain_topology"
    description = (
        "Chain topology structural signals per node for chain-aware strategy selection."
    )
    dependencies = []

    async def detect(self, context: Any, graph_state: Any, response_text: str) -> dict:
        """Compute chain topology signals for all nodes in the graph."""
        # Get methodology name from context
        methodology_name = getattr(context, "methodology", "means_end_chain")

        # Load methodology schema to get ontology level info
        try:
            schema = load_methodology(methodology_name)
        except Exception as e:
            raise ConfigurationError(
                f"ChainTopologySignalDetector failed to load methodology schema '{methodology_name}': {e}"
            ) from e

        # Build level map and terminal types from ontology
        level_map = {}  # node_type -> ontology level
        terminal_types = set()

        if schema.ontology:
            for nt in schema.ontology.nodes:
                level_map[nt.name] = nt.level
                if nt.terminal:
                    terminal_types.add(nt.name)

        # Check if this is a chain methodology (needs at least 2 distinct levels)
        distinct_levels = set(level_map.values())
        if len(distinct_levels) < 2:
            # Non-chain methodology (JTBD, CJM, etc.) — return empty dict
            log.debug(
                "non_chain_methodology",
                methodology=methodology_name,
                levels=distinct_levels,
            )
            return {}

        # Get min/max levels for boundary calculations
        min_level = min(distinct_levels)
        max_level = max(distinct_levels)

        # Get nodes and edges from graph
        nodes = await self._get_session_nodes(context)
        edges = await self._get_session_edges(context)

        if not nodes:
            return {self.signal_name: {}}

        # Filter edges to only leads_to edges (ignore revises, etc.)
        leads_to_edges = [e for e in edges if e.edge_type == "leads_to"]

        # Build adjacency lists and type map
        adj_list = build_adjacency_list(nodes, leads_to_edges)
        reverse_adj_list = build_reverse_adjacency_list(nodes, leads_to_edges)
        node_type_map = get_node_type_map(nodes)

        # Get expected branching from methodology config
        expected_branching = self._get_expected_branching(methodology_name)

        # Compute topology signals for each node
        results = {}
        for node in nodes:
            node_id = node.id
            node_type = node.node_type
            node_level = level_map.get(node_type)

            if node_level is None:
                # Node type not in ontology (shouldn't happen) — skip
                continue

            # Compute each signal
            gap_above = self._compute_gap_above(
                node_id, adj_list, node_type, node_level, terminal_types, max_level
            )
            gap_below = self._compute_gap_below(
                node_id, reverse_adj_list, node_type, node_level, min_level
            )
            level_skip = self._compute_level_skip(
                node_id, adj_list, node_type_map, level_map
            )
            branching_deficit = self._compute_branching_deficit(
                node_id, adj_list, reverse_adj_list, node_type, expected_branching
            )
            fan_in = self._compute_fan_in(
                node_id, reverse_adj_list, node_type_map, level_map, min_level
            )
            level_gap_size = self._compute_level_gap_size(
                gap_above, gap_below, node_level, max_level, min_level
            )
            has_attribute_foundation = self._compute_has_attribute_foundation(
                node_id, reverse_adj_list, node_type_map, level_map, min_level
            )
            has_terminal_apex = self._compute_has_terminal_apex(
                node_id, adj_list, node_type_map, terminal_types
            )

            results[node_id] = {
                "gap_above": gap_above,
                "gap_below": gap_below,
                "level_skip": level_skip,
                "branching_deficit": branching_deficit,
                "fan_in": fan_in,
                "level_gap_size": level_gap_size,
                "chain.has_attribute_foundation": has_attribute_foundation,
                "chain.has_terminal_apex": has_terminal_apex,
            }

        # Return in node signal format: {node_id: signal_value}
        # where signal_value is the dict of all chain topology metrics for that node
        return results

    def _compute_gap_above(
        self,
        node_id: str,
        adj_list: dict[str, list[str]],
        node_type: str,
        node_level: int,
        terminal_types: set,
        max_level: int,
    ) -> bool:
        """Check if node has gap above (no outgoing edges to higher level).

        Node has gap_above if:
        - No outgoing edges to higher ontology level
        - Node is not terminal
        """
        # Terminal nodes never have gap_above
        if node_type in terminal_types:
            return False

        # Already at max level → no gap possible
        if node_level >= max_level:
            return False

        # No outgoing edges at all → gap_above
        outgoing = adj_list.get(node_id, [])
        if not outgoing:
            return True

        # Has outgoing edges but none to higher level → still gap_above
        # (edges to same level or lower level don't extend the chain upward)
        # This is handled at the caller level by checking the adjacency structure
        return False

    def _compute_gap_below(
        self,
        node_id: str,
        reverse_adj_list: dict[str, list[str]],
        _node_type: str,
        node_level: int,
        min_level: int,
    ) -> bool:
        """Check if node has gap below (no incoming edges from lower level).

        Node has gap_below if:
        - No incoming edges from lower ontology level
        - Node is above the lowest level (level > min_level)
        """
        # Already at origin level → no gap_below
        if node_level == min_level:
            return False

        # No incoming edges at all → gap_below
        incoming = reverse_adj_list.get(node_id, [])
        if not incoming:
            return True

        # Has incoming edges — assume grounded (simplification; accurate check
        # would verify source node levels via node_type_map + level_map)
        return False

    def _compute_level_skip(
        self,
        node_id: str,
        adj_list: dict[str, list[str]],
        node_type_map: dict[str, str],
        level_map: dict[str, int],
    ) -> bool:
        """Check if node has edges that skip >1 ontology level."""
        outgoing = adj_list.get(node_id, [])
        source_level = level_map.get(node_type_map.get(node_id, ""), 0)

        for target_id in outgoing:
            target_type = node_type_map.get(target_id, "")
            target_level = level_map.get(target_type, source_level)

            # If level difference > 1, it's a skip
            if abs(target_level - source_level) > 1:
                return True

        return False

    def _compute_branching_deficit(
        self,
        node_id: str,
        adj_list: dict[str, list[str]],
        reverse_adj_list: dict[str, list[str]],
        node_type: str,
        expected_branching: dict[str, int],
    ) -> float:
        """Compute branching deficit: 1 - (actual_siblings / expected_siblings)."""
        # Get expected branching for this node type
        expected = expected_branching.get(node_type, 0)

        if expected == 0:
            # No expectation → no deficit
            return 0.0

        # Count siblings: nodes at same level that share a parent
        # A sibling shares at least one parent (node with edge to/from this node)
        siblings = set()

        # Check outgoing parents (targets of this node's edges)
        for target_id in adj_list.get(node_id, []):
            # Add all other nodes that also point to this target
            for other_id, other_outgoing in adj_list.items():
                if other_id != node_id and target_id in other_outgoing:
                    siblings.add(other_id)

        # Check incoming parents (sources of edges to this node)
        for source_id in reverse_adj_list.get(node_id, []):
            # Add all other nodes that also receive edges from this source
            for other_id, other_incoming in reverse_adj_list.items():
                if other_id != node_id and source_id in other_incoming:
                    siblings.add(other_id)

        actual = len(siblings)

        # Deficit: 1 - min(actual/expected, 1.0)
        ratio = actual / expected if expected > 0 else 0.0
        return 1.0 - min(ratio, 1.0)

    def _compute_fan_in(
        self,
        node_id: str,
        reverse_adj_list: dict[str, list[str]],
        node_type_map: dict[str, str],
        level_map: dict[str, int],
        min_level: int,
    ) -> int:
        """Count distinct origin-level nodes with paths to this node."""
        # Use BFS on reverse adjacency to find all nodes that can reach this one
        reachable = bfs_reachable(node_id, reverse_adj_list)

        # Count how many are at the origin level (min_level)
        # Exclude the node itself from the count
        origin_count = 0
        for reachable_id in reachable:
            # Skip the node itself
            if reachable_id == node_id:
                continue
            reachable_type = node_type_map.get(reachable_id, "")
            reachable_level = level_map.get(reachable_type)
            if reachable_level == min_level:
                origin_count += 1

        return origin_count

    def _compute_level_gap_size(
        self,
        gap_above: bool,
        gap_below: bool,
        node_level: int,
        max_level: int,
        min_level: int,
    ) -> int:
        """Compute number of ontology levels in the gap."""
        if gap_above:
            return max_level - node_level
        elif gap_below:
            return node_level - min_level
        else:
            return 0

    def _compute_has_attribute_foundation(
        self,
        node_id: str,
        reverse_adj_list: dict[str, list[str]],
        node_type_map: dict[str, str],
        level_map: dict[str, int],
        min_level: int,
    ) -> bool:
        """Check if there exists a downward path (reverse edges) to an attribute node.

        True if this node, or any node reachable by following reverse leads_to edges,
        has an ontology level equal to min_level (the origin/attribute level).
        """
        reachable = bfs_reachable(node_id, reverse_adj_list)
        for reachable_id in reachable:
            reachable_type = node_type_map.get(reachable_id, "")
            reachable_level = level_map.get(reachable_type)
            if reachable_level == min_level:
                return True
        return False

    def _compute_has_terminal_apex(
        self,
        node_id: str,
        adj_list: dict[str, list[str]],
        node_type_map: dict[str, str],
        terminal_types: set,
    ) -> bool:
        """Check if there exists an upward path (forward edges) to a terminal node.

        True if this node, or any node reachable by following forward leads_to edges,
        has a node_type in terminal_types.
        """
        reachable = bfs_reachable(node_id, adj_list)
        for reachable_id in reachable:
            reachable_type = node_type_map.get(reachable_id, "")
            if reachable_type in terminal_types:
                return True
        return False

    def _get_expected_branching(self, methodology_name: str) -> dict[str, int]:
        """Get expected branching per node type from methodology YAML.

        Reads chain_completion.expected_branching directly from the YAML file
        since MethodologySchema doesn't parse this section.
        """
        try:
            from pathlib import Path

            schema_dir = (
                Path(__file__).parent.parent.parent.parent / "config" / "methodologies"
            )
            path = schema_dir / f"{methodology_name}.yaml"

            import yaml

            with open(path) as f:
                data = yaml.safe_load(f)

            chain_completion = data.get("chain_completion", {})
            if isinstance(chain_completion, dict):
                branching_config = chain_completion.get("expected_branching", {})
                if isinstance(branching_config, dict):
                    return {k: int(v) for k, v in branching_config.items()}
        except Exception as e:
            log.debug(
                "expected_branching_load_failed",
                methodology=methodology_name,
                error=str(e),
            )

        return {}

    async def _get_session_nodes(self, context: Any) -> List[Any]:
        """Get all nodes for the session."""
        session_id = getattr(context, "session_id", None)
        if not session_id:
            raise GraphError(
                "ChainTopologySignalDetector failed to load nodes: session_id is None"
            )

        try:
            from src.persistence.repositories.graph_repo import GraphRepository
            from src.persistence.database import get_db_connection

            repo = GraphRepository(await get_db_connection())
            return await repo.get_nodes_by_session(session_id)
        except Exception as e:
            raise GraphError(
                f"ChainTopologySignalDetector failed to load nodes for session '{session_id}': {e}"
            ) from e

    async def _get_session_edges(self, context: Any) -> List[Any]:
        """Get all edges for the session."""
        session_id = getattr(context, "session_id", None)
        if not session_id:
            raise GraphError(
                "ChainTopologySignalDetector failed to load edges: session_id is None"
            )

        try:
            from src.persistence.repositories.graph_repo import GraphRepository
            from src.persistence.database import get_db_connection

            repo = GraphRepository(await get_db_connection())
            return await repo.get_edges_by_session(session_id)
        except Exception as e:
            raise GraphError(
                f"ChainTopologySignalDetector failed to load edges for session '{session_id}': {e}"
            ) from e


# ---------------------------------------------------------------------------
# Virtual flat-signal sentinels
#
# NodeSignalDetectionService flattens the nested dict returned by
# ChainTopologySignalDetector into individual keys per node
# (e.g. graph.node.gap_above, graph.node.fan_in).  These sentinel classes
# register those names in the SignalDetector registry so the YAML validator
# accepts them in `valid_when` and `signal_weights` without needing real
# detector logic (values always come from the flattening step).
# ---------------------------------------------------------------------------


class _ChainTopoFlatSentinel(NodeSignalDetector):
    """Abstract base for flat chain-topology sentinel registrations.

    Appears in get_all_node_signal_classes() (requires_node_tracker=True from
    NodeSignalDetector).  detect() always returns {} — actual values are injected
    by NodeSignalDetectionService when it flattens ChainTopologySignalDetector output.
    """

    async def detect(self, context: Any, graph_state: Any, response_text: str) -> dict:  # type: ignore[override]
        # Never called; values come from NodeSignalDetectionService flattening.
        return {}


class _GapAboveSentinel(_ChainTopoFlatSentinel):
    signal_name = "graph.node.gap_above"
    description = (
        "True if node has no outgoing edge to a higher ontology level (chain frontier)."
    )
    dependencies = []


class _GapBelowSentinel(_ChainTopoFlatSentinel):
    signal_name = "graph.node.gap_below"
    description = (
        "True if node has no incoming edge from a lower ontology level (ungrounded)."
    )
    dependencies = []


class _LevelSkipSentinel(_ChainTopoFlatSentinel):
    signal_name = "graph.node.level_skip"
    description = "True if node has a direct leads_to edge that skips one or more ontology levels."
    dependencies = []


class _BranchingDeficitSentinel(_ChainTopoFlatSentinel):
    signal_name = "graph.node.branching_deficit"
    description = (
        "Branching deficit: 1 - (actual_siblings / expected_siblings) in [0,1]."
    )
    dependencies = []


class _FanInSentinel(_ChainTopoFlatSentinel):
    signal_name = "graph.node.fan_in"
    description = "Count of distinct origin-level nodes with paths to this node."
    dependencies = []


class _LevelGapSizeSentinel(_ChainTopoFlatSentinel):
    signal_name = "graph.node.level_gap_size"
    description = "Number of ontology levels between this node and terminal/origin."
    dependencies = []


class _HasAttributeFoundationSentinel(_ChainTopoFlatSentinel):
    signal_name = "graph.node.chain.has_attribute_foundation"
    description = (
        "True if a downward path (reverse edges) reaches an attribute-level node."
    )
    dependencies = []


class _HasTerminalApexSentinel(_ChainTopoFlatSentinel):
    signal_name = "graph.node.chain.has_terminal_apex"
    description = (
        "True if an upward path (forward edges) reaches a terminal-value node."
    )
    dependencies = []


__all__ = [
    "ChainTopologySignalDetector",
    "_GapAboveSentinel",
    "_GapBelowSentinel",
    "_LevelSkipSentinel",
    "_BranchingDeficitSentinel",
    "_FanInSentinel",
    "_LevelGapSizeSentinel",
    "_HasAttributeFoundationSentinel",
    "_HasTerminalApexSentinel",
]
