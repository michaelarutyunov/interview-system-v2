"""Global chain topology signals — aggregate counts of chain frontiers and ungrounded nodes."""

from typing import Any, List

import structlog

from src.core.exceptions import ConfigurationError, GraphError
from src.core.schema_loader import load_methodology
from src.signals.graph.graph_traversal import (
    build_adjacency_list,
    build_reverse_adjacency_list,
)
from src.signals.signal_base import SignalDetector

log = structlog.get_logger(__name__)


class GlobalChainTopologySignal(SignalDetector):
    """Global chain topology aggregates for observability and threshold checks.

    Namespaced signals:
        - convgraph.chain.structure.frontier_count (int): Nodes with gap_above=True (chain frontiers).
        - convgraph.chain.structure.ungrounded_count (int): Nodes with gap_below=True (ungrounded nodes).

    Returns empty dict for non-chain methodologies (fewer than 2 distinct ontology levels).
    """

    signal_name = "convgraph.chain.structure"
    description = (
        "Global chain topology aggregates. "
        "convgraph.chain.structure.frontier_count = chain frontiers (gap_above nodes). "
        "convgraph.chain.structure.ungrounded_count = ungrounded nodes (gap_below nodes)."
    )
    dependencies = []

    async def detect(self, context: Any, graph_state: Any, response_text: str) -> dict:
        """Count frontiers and ungrounded nodes across the graph."""
        methodology_name = getattr(context, "methodology", "means_end_chain")

        try:
            schema = load_methodology(methodology_name)
        except Exception as e:
            raise ConfigurationError(
                f"GlobalChainTopologySignal failed to load methodology '{methodology_name}': {e}"
            ) from e

        # Build level map and terminal types
        level_map: dict[str, int] = {}
        terminal_types: set[str] = set()
        if schema.ontology:
            for nt in schema.ontology.nodes:
                if nt.level is not None:
                    level_map[nt.name] = nt.level
                if nt.terminal:
                    terminal_types.add(nt.name)

        # Non-chain methodology — return empty
        distinct_levels = set(level_map.values())
        if len(distinct_levels) < 2:
            return {}

        min_level = min(distinct_levels)

        # Load graph data
        nodes = await self._get_session_nodes(context)
        edges = await self._get_session_edges(context)

        if not nodes:
            return {
                "convgraph.chain.structure.frontier_count": 0,
                "convgraph.chain.structure.ungrounded_count": 0,
            }

        # Filter to leads_to edges only
        leads_to_edges = [e for e in edges if e.edge_type == "leads_to"]
        adj_list = build_adjacency_list(nodes, leads_to_edges)
        reverse_adj_list = build_reverse_adjacency_list(nodes, leads_to_edges)

        frontier_count = 0
        ungrounded_count = 0

        for node in nodes:
            node_type = node.node_type
            node_level = level_map.get(node_type)
            if node_level is None:
                continue

            # gap_above: no outgoing edges AND not terminal
            if node_type not in terminal_types and not adj_list.get(node.id):
                frontier_count += 1

            # gap_below: no incoming edges AND above origin level
            if node_level > min_level and not reverse_adj_list.get(node.id):
                ungrounded_count += 1

        return {
            "convgraph.chain.structure.frontier_count": frontier_count,
            "convgraph.chain.structure.ungrounded_count": ungrounded_count,
        }

    async def _get_session_nodes(self, context: Any) -> List[Any]:
        """Get all nodes for the session."""
        session_id = getattr(context, "session_id", None)
        if not session_id:
            raise GraphError("GlobalChainTopologySignal: session_id is None")
        from src.persistence.database import get_db_connection
        from src.persistence.repositories.graph_repo import GraphRepository

        repo = GraphRepository(await get_db_connection())
        return await repo.get_nodes_by_session(session_id)

    async def _get_session_edges(self, context: Any) -> List[Any]:
        """Get all edges for the session."""
        session_id = getattr(context, "session_id", None)
        if not session_id:
            raise GraphError("GlobalChainTopologySignal: session_id is None")
        from src.persistence.database import get_db_connection
        from src.persistence.repositories.graph_repo import GraphRepository

        repo = GraphRepository(await get_db_connection())
        return await repo.get_edges_by_session(session_id)


__all__ = ["GlobalChainTopologySignal"]
