"""Service for selecting what to focus on next.

Centralizes focus selection logic that was previously scattered
across individual strategies.
"""

from typing import Optional
from dataclasses import dataclass


@dataclass
class FocusSelectionInput:
    """Input for focus selection."""

    strategy: str
    graph_state: any  # GraphState
    recent_nodes: list
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
    """

    async def select(self, input_data: FocusSelectionInput) -> Optional[str]:
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

        return (
            shallow_node.label
            if hasattr(shallow_node, "label")
            else str(shallow_node)
            if shallow_node
            else None
        )

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

        return (
            deep_node.label
            if hasattr(deep_node, "label")
            else str(deep_node)
            if deep_node
            else None
        )

    def _select_most_recent_node(self, recent_nodes) -> Optional[str]:
        """Select the most recent node (fallback)."""
        if not recent_nodes:
            return None

        node = recent_nodes[0]
        return node.label if hasattr(node, "label") else str(node)
