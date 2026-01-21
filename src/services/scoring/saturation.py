"""Saturation scorer - detects topic exhaustion.

Penalizes depth strategies when topic is saturated, boosts breadth.
"""

from typing import Any, Dict

import structlog

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.base import ScorerBase, ScorerOutput


# Default configuration values
DEFAULT_NEW_INFO_THRESHOLD = 0.05
DEFAULT_RUN_LENGTH = 2
DEFAULT_SATURATED_PENALTY = 0.3


logger = structlog.get_logger(__name__)


class SaturationScorer(ScorerBase):
    """
    Detect topic exhaustion using new info rate and low-info turn tracking.

    Algorithm:
    1. Check new_info_rate from graph_state
    2. Check consecutive_low_info_turns from graph_state
    3. Penalize depth strategies when saturated
    4. Boost breadth strategies when saturated

    Scoring:
    - 1.0 = not saturated
    - saturated_penalty (e.g., 0.3) = topic exhausted, penalize depth
    - 1/penalty (e.g., 3.3) = boost for breadth when saturated

    Configuration parameters:
    - new_info_threshold: Min new info rate (default: 0.05)
    - run_length: Consecutive low-info turns to trigger (default: 2)
    - saturated_penalty: Penalty for depth on saturated topic (default: 0.3)
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.new_info_threshold = self.params.get("new_info_threshold", DEFAULT_NEW_INFO_THRESHOLD)
        self.run_length = self.params.get("run_length", DEFAULT_RUN_LENGTH)
        self.saturated_penalty = self.params.get("saturated_penalty", DEFAULT_SATURATED_PENALTY)

    async def score(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
        recent_nodes: list[Dict[str, Any]],
    ) -> ScorerOutput:
        """
        Score based on topic saturation.

        Args:
            strategy: Strategy dict with 'type_category'
            focus: Focus dict (unused for saturation scorer)
            graph_state: Graph state with saturation metrics
            recent_nodes: Recent nodes (unused for saturation scorer)

        Returns:
            ScorerOutput with saturation-based score
        """
        score = 1.0
        signals = {}
        reasons = []

        # Get saturation metrics from graph_state properties
        new_info_rate = graph_state.properties.get("new_info_rate", 1.0)
        consecutive_low_info = graph_state.properties.get("consecutive_low_info_turns", 0)

        signals["new_info_rate"] = new_info_rate
        signals["consecutive_low_info"] = consecutive_low_info

        # Check if saturated
        is_low_info = new_info_rate < self.new_info_threshold
        is_low_info_run = consecutive_low_info >= self.run_length
        is_saturated = is_low_info or is_low_info_run

        signals["is_saturated"] = is_saturated

        # Apply penalties/bonuses based on strategy type
        if is_saturated:
            if strategy.get("type_category") == "depth":
                # Penalize depth on saturated topic
                score *= self.saturated_penalty
                reasons.append(
                    f"Topic saturated (new_info_rate={new_info_rate:.2f}, "
                    f"low_info_turns={consecutive_low_info})"
                )
            elif strategy.get("type_category") == "breadth":
                # Boost breadth when saturated (switch topics)
                boost = 1.0 / self.saturated_penalty
                score *= boost
                reasons.append("Topic saturated - breadth encouraged")

        if not reasons:
            reasoning = "Topic not saturated - no adjustment"
        else:
            reasoning = "; ".join(reasons)

        logger.debug(
            "SaturationScorer output",
            strategy_id=strategy.get("id"),
            is_saturated=is_saturated,
            new_info_rate=new_info_rate,
            score=score,
        )

        return self.make_output(score, signals, reasoning)
