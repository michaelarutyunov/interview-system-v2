"""Service for selecting what to focus on next.

Centralizes focus selection logic that was previously scattered
across individual strategies.

DEPRECATION NOTICE (Phase 3):
This service is deprecated in favor of joint strategy-node scoring.
The MethodologyStrategyService.select_strategy_and_focus() method
now handles both strategy and focus selection together using
node-level signals and the NodeStateTracker.

This service is kept for backward compatibility but should not be
used in new code.
"""

import warnings
from typing import TYPE_CHECKING, Optional

from dataclasses import dataclass

if TYPE_CHECKING:
    from src.domain.models.knowledge_graph import GraphState, KGNode
else:
    GraphState = object  # type: ignore
    KGNode = object  # type: ignore


@dataclass
class FocusSelectionInput:
    """Input for focus selection."""

    strategy: str
    graph_state: GraphState
    recent_nodes: list[KGNode]
    signals: dict


class FocusSelectionService:
    """Service for selecting what to focus on next.

    Replaces scattered focus selection logic across strategies.
    Each strategy has a defined focus_preference that maps to
    specific selection logic.

    Focus preferences:
    - shallow: Prefer nodes with low depth (for laddering)
    - recent: Prefer most recently added nodes (for elaboration)
    - related: Prefer nodes with relationships (for probing)
    - deep: Prefer nodes with high depth (for validation)

    DEPRECATED (Phase 3):
    This service is deprecated in favor of joint strategy-node scoring.
    Use MethodologyStrategyService.select_strategy_and_focus() instead.
    """

    async def select(self, input_data: FocusSelectionInput) -> Optional[str]:
        """Select focus based on strategy requirements.

        Args:
            input_data: FocusSelectionInput with strategy, graph state, recent nodes, signals

        Returns:
            Selected focus (node label) or None if no focus available

        DEPRECATED: Use MethodologyStrategyService.select_strategy_and_focus() instead.
        """
        warnings.warn(
            "FocusSelectionService is deprecated. "
            "Use MethodologyStrategyService.select_strategy_and_focus() "
            "for joint strategy-node scoring.",
            DeprecationWarning,
            stacklevel=2,
        )
        """Select focus based on strategy requirements.

        Args:
            input_data: FocusSelectionInput with strategy, graph state, recent nodes, signals

        Returns:
            Selected focus (node label) or None if no focus available
        """
        strategy = input_data.strategy
        graph_state = input_data.graph_state
        recent_nodes = input_data.recent_nodes
        signals = input_data.signals

        # Map strategy to focus preference
        # In production, this would come from YAML config
        focus_preference = self._get_focus_preference(strategy)

        if focus_preference == "shallow":
            return await self._select_shallow(graph_state, recent_nodes, signals)
        elif focus_preference == "recent":
            return await self._select_recent(graph_state, recent_nodes, signals)
        elif focus_preference == "related":
            return await self._select_related(graph_state, recent_nodes, signals)
        elif focus_preference == "deep":
            return await self._select_deep(graph_state, recent_nodes, signals)
        else:
            # Default to most recent
            return self._select_most_recent_node(recent_nodes)

    def _get_focus_preference(self, strategy: str) -> str:
        """Get focus preference for strategy.

        In production, this comes from YAML config.
        For PoC, hardcoded mapping.
        """
        preference_map = {
            # MEC strategies
            "deepen": "shallow",
            "clarify": "related",
            "explore": "recent",
            "reflect": "deep",
            # JTBD strategies
            "explore_situation": "recent",
            "probe_alternatives": "related",
            "dig_motivation": "shallow",
            "validate_outcome": "deep",
            "uncover_obstacles": "related",
        }
        return preference_map.get(strategy, "recent")

    async def _select_shallow(
        self, graph_state, recent_nodes, signals
    ) -> Optional[str]:
        """For deepening, prefer nodes with shallow depth."""
        if not recent_nodes:
            return None

        depth_by_element = signals.get("graph.depth_by_element", {})

        # Find node with lowest depth
        shallow_node = None
        min_depth = float("inf")

        for node in recent_nodes:
            node_id = str(getattr(node, "id", ""))
            depth = depth_by_element.get(node_id, 0)
            if depth < min_depth:
                min_depth = depth
                shallow_node = node

        if shallow_node is None:
            return None
        return shallow_node.label if hasattr(shallow_node, "label") else str(shallow_node)

    async def _select_recent(self, graph_state, recent_nodes, signals) -> Optional[str]:
        """For elaboration, prefer most recent node."""
        return self._select_most_recent_node(recent_nodes)

    async def _select_related(
        self, graph_state, recent_nodes, signals
    ) -> Optional[str]:
        """For probing, prefer nodes with relationships."""
        if not recent_nodes:
            return None

        # For PoC, return first node with edges
        # In production, would check actual graph relationships
        for node in recent_nodes:
            # Simple heuristic: if node has been in graph for a while, it likely has relationships
            return node.label if hasattr(node, "label") else str(node)

        return self._select_most_recent_node(recent_nodes)

    async def _select_deep(self, graph_state, recent_nodes, signals) -> Optional[str]:
        """For validation, prefer nodes with high depth."""
        if not recent_nodes:
            return None

        depth_by_element = signals.get("graph.depth_by_element", {})

        # Find node with highest depth
        deep_node = None
        max_depth = -1

        for node in recent_nodes:
            node_id = str(getattr(node, "id", ""))
            depth = depth_by_element.get(node_id, 0)
            if depth > max_depth:
                max_depth = depth
                deep_node = node

        if deep_node is None:
            return None
        return deep_node.label if hasattr(deep_node, "label") else str(deep_node)

    def _select_most_recent_node(self, recent_nodes) -> Optional[str]:
        """Select the most recent node (fallback)."""
        if not recent_nodes:
            return None

        node = recent_nodes[0]
        return node.label if hasattr(node, "label") else str(node)
