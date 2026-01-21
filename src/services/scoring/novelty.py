"""Novelty scorer - prevents repetitive exploration.

Penalizes strategies that focus on recently explored concepts.
"""

from typing import Any, Dict

import structlog

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.base import ScorerBase, ScorerOutput


# Default configuration values
DEFAULT_RECENCY_WINDOW = 3
DEFAULT_RECENCY_PENALTY = 0.3


logger = structlog.get_logger(__name__)


class NoveltyScorer(ScorerBase):
    """
    Penalize redundant exploration of recently covered concepts.

    Algorithm:
    1. Get recent node IDs from recent_nodes parameter
    2. Check if current focus node_id matches recent nodes
    3. Apply penalty for repeated focus

    Scoring:
    - 1.0 = novel focus (not seen recently)
    - recency_penalty (e.g., 0.3) = focus was seen recently

    Configuration parameters:
    - recency_window: Number of recent turns to check (default: 3)
    - recency_penalty: Penalty multiplier for recent nodes (default: 0.3)
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.recency_window = self.params.get("recency_window", DEFAULT_RECENCY_WINDOW)
        self.recency_penalty = self.params.get("recency_penalty", DEFAULT_RECENCY_PENALTY)

    async def score(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
        recent_nodes: list[Dict[str, Any]],
    ) -> ScorerOutput:
        """
        Score strategy/focus based on novelty.

        Args:
            strategy: Strategy dict
            focus: Focus dict with 'node_id'
            graph_state: Graph state (unused for novelty scorer)
            recent_nodes: List of recent node dicts from last N turns

        Returns:
            ScorerOutput with novelty-based score
        """
        score = 1.0
        signals = {}
        reasons = []

        # Get recent node IDs
        recent_node_ids = [n.get("id") for n in recent_nodes[-self.recency_window:]]
        signals["recent_nodes_count"] = len(recent_node_ids)

        # Check for exact node match
        focus_node_id = focus.get("node_id")
        if focus_node_id and focus_node_id in recent_node_ids:
            score *= self.recency_penalty
            reasons.append(
                f"Node {focus_node_id} explored in last {self.recency_window} turns"
            )
            signals["node_match"] = True
            logger.debug(
                "Novelty penalty: recent node",
                focus_node_id=focus_node_id,
                recency_window=self.recency_window,
                penalty=self.recency_penalty,
            )
        else:
            signals["node_match"] = False

        # Build reasoning string
        if not reasons:
            reasoning = f"Novel focus - not seen in last {self.recency_window} turns"
        else:
            reasoning = "; ".join(reasons)

        logger.debug(
            "NoveltyScorer output",
            strategy_id=strategy.get("id"),
            focus_node_id=focus_node_id,
            score=score,
        )

        return self.make_output(score, signals, reasoning)
