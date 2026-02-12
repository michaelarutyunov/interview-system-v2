"""Focus selection service for interview node targeting.

Consolidates all focus selection logic into a single service that:
1. Resolves node IDs to labels
2. Applies strategy-based focus preferences
3. Provides fallback selection when needed

This service is the single source of truth for determining what concept
to ask about next in the interview.
"""

from typing import Optional, List, Dict, Any

import structlog

from src.domain.models.knowledge_graph import KGNode, GraphState

log = structlog.get_logger(__name__)


class FocusSelectionService:
    """Centralized service for selecting interview focus targets.

    All focus selection decisions flow through this service to ensure
    consistent behavior across the pipeline.

    Resolution order:
    1. If focus_dict has focus_node_id, resolve to node label
    2. If focus_dict has focus_description, use it directly
    3. Fall back to strategy-based heuristic selection
    """

    def resolve_focus_from_strategy_output(
        self,
        focus_dict: Optional[Dict[str, Any]],
        recent_nodes: List[KGNode],
        strategy: str,
        graph_state: Optional[GraphState] = None,  # noqa: ARG001
    ) -> str:
        """Resolve focus from strategy selection output.

        This is the primary entry point after StrategySelectionStage.

        Args:
            focus_dict: Focus dict from StrategySelectionOutput (may contain
                       focus_node_id or focus_description)
            recent_nodes: Recent nodes for fallback resolution
            strategy: Selected strategy (affects fallback behavior)
            graph_state: Current graph state (for advanced selection)

        Returns:
            Focus concept label (human-readable string for prompts)

        Resolution order:
        1. If focus_dict has focus_node_id, resolve to node label
        2. If focus_dict has focus_description, use it
        3. Fall back to strategy-based heuristic selection
        """
        # Try to resolve from focus_node_id
        if focus_dict and "focus_node_id" in focus_dict:
            node_id = focus_dict["focus_node_id"]
            label = self._resolve_node_id_to_label(node_id, recent_nodes)
            if label:
                log.debug(
                    "focus_resolved_from_node_id",
                    node_id=node_id,
                    label=label,
                )
                return label

        # Try to use focus_description
        if focus_dict and "focus_description" in focus_dict:
            description = focus_dict["focus_description"]
            if description:
                log.debug(
                    "focus_resolved_from_description",
                    description=description,
                )
                return description

        # Fall back to strategy-based selection
        return self._select_by_strategy(
            recent_nodes=recent_nodes,
            strategy=strategy,
            graph_state=graph_state,
        )

    def _resolve_node_id_to_label(
        self,
        node_id: str,
        nodes: List[KGNode],
    ) -> Optional[str]:
        """Find node label by ID.

        Args:
            node_id: Node ID to look up
            nodes: List of nodes to search

        Returns:
            Node label if found, None otherwise
        """
        for node in nodes:
            if str(node.id) == str(node_id):
                return node.label
        return None

    def _select_by_strategy(
        self,
        recent_nodes: List[KGNode],
        strategy: str,
        graph_state: Optional[GraphState] = None,  # noqa: ARG001
    ) -> str:
        """Select focus concept using strategy-based heuristics.

        This is the fallback when no explicit focus is provided.

        Args:
            recent_nodes: Recently added nodes
            strategy: Strategy name
            graph_state: Current graph state

        Returns:
            Focus concept label
        """
        log.debug(
            "focus_selecting_by_strategy",
            strategy=strategy,
            recent_node_count=len(recent_nodes),
        )

        if not recent_nodes:
            return "the topic"

        if strategy == "deepen":
            # Focus on most recent concept to ladder up
            return recent_nodes[0].label

        elif strategy == "broaden":
            # Focus on recent concept but will ask for alternatives
            return recent_nodes[0].label

        elif strategy in ("cover", "cover_element"):
            # Would ideally look at uncovered elements
            # For now, use most recent
            return recent_nodes[0].label

        elif strategy == "close":
            # Summarize what we've learned
            return "what we've discussed"

        elif strategy == "reflect":
            # Reflect on a recent concept
            return recent_nodes[0].label

        # Default: most recent node
        return recent_nodes[0].label
