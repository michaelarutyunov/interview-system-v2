"""Depth/Breadth Balance scorer (Tier 2).

Measures whether strategy aligns with current depth/breadth needs.
Boosts strategies that maintain balance between exploration and exploitation.
"""

from typing import Any, Dict, List, Optional

import structlog

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.two_tier.base import Tier2Scorer, Tier2Output

logger = structlog.get_logger(__name__)


class DepthBreadthBalanceScorer(Tier2Scorer):
    """
    Scores candidates based on alignment with depth/breadth needs.

    Prevents monotonic behavior (all depth or all breadth) by:
    - Measuring current depth: average chain length from root to terminal nodes
    - Measuring current breadth: percentage of elements mentioned
    - Comparing to target ratio (configurable per methodology)

    Scoring logic:
    - If breadth_needed AND strategy is broaden → boost (1.3-1.5)
    - If depth_needed AND strategy is deepen → boost (1.3-1.5)
    - If misaligned with current need → penalty (0.7-0.9)
    - Neutral when balanced → neutral (1.0)

    Weight: 0.20-0.25 (high - prevents monotonic interviews)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        if "weight" not in self.config:
            self.weight = 0.20

        # Target depth/breadth ratio (0.5 = balanced, 0.7 = depth-favoring)
        self.target_ratio = self.params.get("target_ratio", 0.5)

        # Thresholds for determining needs
        self.low_breadth_threshold = self.params.get("low_breadth_threshold", 0.4)
        self.high_breadth_threshold = self.params.get("high_breadth_threshold", 0.7)
        # NOTE: low_depth_threshold lowered to 0.5 (from 2.0) to match current proxy formula
        # Current formula (edge_count/node_count * 2) gives 0.15-0.30 for sparse graphs
        # Bead: tud - Implement actual chain length calculation (BFS from root to leaf nodes)
        self.low_depth_threshold = self.params.get("low_depth_threshold", 0.5)
        self.high_depth_threshold = self.params.get("high_depth_threshold", 1.5)

        logger.info(
            "DepthBreadthBalanceScorer initialized",
            weight=self.weight,
            target_ratio=self.target_ratio,
        )

    async def score(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
        recent_nodes: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]],
    ) -> Tier2Output:
        """Score based on alignment with depth/breadth balance needs.

        Args:
            strategy: Strategy being evaluated
            focus: Focus target
            graph_state: Current graph state
            recent_nodes: Recent nodes from graph
            conversation_history: Conversation history

        Returns:
            Tier2Output with score based on alignment with needs
        """
        # Calculate current depth and breadth metrics
        breadth_pct = self._calculate_breadth(graph_state)
        depth_avg = self._calculate_depth(graph_state, recent_nodes)

        # Determine current needs
        breadth_needed = breadth_pct < self.low_breadth_threshold
        depth_needed = depth_avg < self.low_depth_threshold

        # Get strategy type
        strategy_type = strategy.get("type_category", "")
        strategy_id = strategy.get("id", "")

        # Score based on alignment
        raw_score = 1.0  # Default: neutral

        # Initialize reasoning for all paths
        reasoning = f"Unknown strategy type '{strategy_type}' (breadth: {breadth_pct:.1%}, depth: {depth_avg:.1f})"

        if breadth_needed:
            if strategy_type in ["breadth", "coverage"]:
                # Breadth strategy when breadth is needed - strong boost
                raw_score = 1.5
                reasoning = f"Breadth needed (current: {breadth_pct:.1%}), strategy is {strategy_id}"
            elif strategy_type == "depth":
                # Depth strategy when breadth is needed - penalty
                raw_score = 0.7
                reasoning = f"Breadth needed (current: {breadth_pct:.1%}), but strategy is {strategy_id}"
            else:
                # Unexpected strategy type when breadth needed
                raw_score = 0.9
                reasoning = f"Breadth needed (current: {breadth_pct:.1%}), but strategy is {strategy_id}"
        elif depth_needed:
            if strategy_type == "depth":
                # Depth strategy when depth is needed - strong boost
                raw_score = 1.5
                reasoning = f"Depth needed (current: {depth_avg:.1f}), strategy is {strategy_id}"
            elif strategy_type in ["breadth", "coverage"]:
                # Breadth strategy when depth is needed - penalty
                raw_score = 0.7
                reasoning = f"Depth needed (current: {depth_avg:.1f}), but strategy is {strategy_id}"
            else:
                # Unexpected strategy type when depth needed
                raw_score = 0.9
                reasoning = f"Depth needed (current: {depth_avg:.1f}), but strategy is {strategy_id}"
        else:
            # Balanced - slight boost for any strategy
            raw_score = 1.1
            reasoning = f"Balanced (breadth: {breadth_pct:.1%}, depth: {depth_avg:.1f})"

        signals = {
            "breadth_pct": breadth_pct,
            "depth_avg": depth_avg,
            "breadth_needed": breadth_needed,
            "depth_needed": depth_needed,
            "strategy_type": strategy_type,
        }

        logger.debug(
            "DepthBreadthBalanceScorer scored",
            score=raw_score,
            breadth_pct=breadth_pct,
            depth_avg=depth_avg,
            reasoning=reasoning,
        )

        return self.make_output(
            raw_score=raw_score, signals=signals, reasoning=reasoning
        )

    def _calculate_breadth(self, graph_state: GraphState) -> float:
        """Calculate breadth as percentage of elements mentioned.

        Args:
            graph_state: Current graph state

        Returns:
            Breadth percentage (0.0-1.0)
        """
        coverage_state = graph_state.properties.get("coverage_state", {})
        elements_seen = coverage_state.get("elements_seen", [])

        # Fallback: use node type diversity as breadth proxy
        # More unique node types = broader exploration
        if not elements_seen:
            nodes_by_type = graph_state.nodes_by_type
            if nodes_by_type:
                # Count types with at least one node
                unique_types_count = len([k for k, v in nodes_by_type.items() if v > 0])
                # Rough heuristic: 5 unique types = 100% breadth
                return min(1.0, unique_types_count / 5.0)

            return 0.0

        # Try to get total elements from config (if stored)
        elements_total = coverage_state.get("elements_total", [])

        if not elements_total or len(elements_total) == 0:
            return 0.0

        return len(elements_seen) / len(elements_total)

    def _calculate_depth(
        self, graph_state: GraphState, recent_nodes: List[Dict[str, Any]]
    ) -> float:
        """Calculate depth as average chain length from root to terminal nodes.

        Args:
            graph_state: Current graph state
            recent_nodes: Recent nodes for analysis

        Returns:
            Average depth (float)
        """
        # Bead: tud - For now, use edge ratio as proxy for depth
        node_count = graph_state.node_count

        # Heuristic: more nodes = potentially deeper exploration
        # But we want average chain length, not just node count
        # Use a simple heuristic for now
        if node_count == 0:
            return 0.0

        # Estimate depth from node count and edge count
        edge_count = graph_state.edge_count
        if node_count > 0:
            avg_edges_per_node = edge_count / node_count
            # Rough approximation of depth
            return min(5.0, avg_edges_per_node * 2)

        return 0.0
