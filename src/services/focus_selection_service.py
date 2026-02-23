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
        graph_state: Optional[GraphState] = None,  # noqa: ARG002
        focus_mode: str = "recent_node",
    ) -> str:
        """Resolve focus from strategy selection output.

        This is the primary entry point after StrategySelectionStage.

        Args:
            focus_dict: Focus dict from StrategySelectionOutput (may contain
                       focus_node_id or focus_description)
            recent_nodes: Recent nodes for fallback resolution
            strategy: Selected strategy (for logging only)
            graph_state: Current graph state (reserved for future use)
            focus_mode: Focus mode from StrategyConfig YAML

        Returns:
            Focus concept label (human-readable string for prompts)

        Resolution order:
        1. If focus_dict has focus_node_id, resolve to node label
        2. If focus_dict has focus_description, use it
        3. Fall back to focus_mode-based selection
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

        # Fall back to focus_mode-based selection
        return self._select_by_focus_mode(
            recent_nodes=recent_nodes,
            strategy=strategy,
            focus_mode=focus_mode,
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

    def _select_by_focus_mode(
        self,
        recent_nodes: List[KGNode],
        strategy: str,
        focus_mode: str = "recent_node",
    ) -> str:
        """Select focus concept using focus_mode from strategy config.

        Args:
            recent_nodes: Recently added nodes
            strategy: Strategy name (for logging only)
            focus_mode: Focus mode from StrategyConfig YAML

        Returns:
            Focus concept label
        """
        log.debug(
            "focus_selecting_by_mode",
            strategy=strategy,
            focus_mode=focus_mode,
            recent_node_count=len(recent_nodes),
        )

        if not recent_nodes:
            return "the topic"

        if focus_mode == "summary":
            return "what we've discussed"

        if focus_mode == "topic":
            return "the topic"

        # Default: recent_node
        return recent_nodes[0].label
