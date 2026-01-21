"""Richness scorer - adapts to respondent engagement level.

Boosts depth when engagement is high, penalizes depth when engagement is low.
"""

from typing import Any, Dict

import structlog

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.base import ScorerBase, ScorerOutput


# Default configuration values
DEFAULT_LOW_THRESHOLD = 50
DEFAULT_HIGH_THRESHOLD = 200
DEFAULT_LOW_ENGAGEMENT_PENALTY = 0.6
DEFAULT_HIGH_ENGAGEMENT_BOOST = 1.4


logger = structlog.get_logger(__name__)


class RichnessScorer(ScorerBase):
    """
    Adapt to respondent engagement level based on response length.

    Algorithm:
    1. Get avg_response_length from graph_state.properties
    2. Classify engagement: low (<50 chars), medium (50-200), high (>200)
    3. Low: penalize depth, boost breadth/coverage
    4. High: boost depth

    Scoring:
    - 1.0 = medium engagement (neutral)
    - low_engagement_penalty (e.g., 0.6) = low engagement, penalize depth
    - high_engagement_boost (e.g., 1.4) = high engagement, boost depth

    Configuration parameters:
    - low_threshold: Char count for low engagement (default: 50)
    - high_threshold: Char count for high engagement (default: 200)
    - low_engagement_penalty: Penalty for depth on low engagement (default: 0.6)
    - high_engagement_boost: Boost for depth on high engagement (default: 1.4)
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.low_threshold = self.params.get("low_threshold", DEFAULT_LOW_THRESHOLD)
        self.high_threshold = self.params.get("high_threshold", DEFAULT_HIGH_THRESHOLD)
        self.low_penalty = self.params.get("low_engagement_penalty", DEFAULT_LOW_ENGAGEMENT_PENALTY)
        self.high_boost = self.params.get("high_engagement_boost", DEFAULT_HIGH_ENGAGEMENT_BOOST)

    async def score(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
        recent_nodes: list[Dict[str, Any]],
    ) -> ScorerOutput:
        """
        Score based on response richness/engagement.

        Args:
            strategy: Strategy dict with 'type_category'
            focus: Focus dict (unused for richness scorer)
            graph_state: Graph state with avg_response_length in properties
            recent_nodes: Recent nodes (unused for richness scorer)

        Returns:
            ScorerOutput with engagement-based score
        """
        score = 1.0
        signals = {}
        reasons = []

        # Get average response length from graph_state
        avg_length = graph_state.properties.get("avg_response_length", 100)

        signals["avg_response_length"] = avg_length

        # Classify engagement level
        if avg_length < self.low_threshold:
            engagement = "low"
        elif avg_length < self.high_threshold:
            engagement = "medium"
        else:
            engagement = "high"

        signals["engagement_level"] = engagement

        # Apply scoring based on engagement level
        if engagement == "low":
            # Low engagement: penalize complex depth strategies
            if strategy.get("type_category") == "depth":
                score *= self.low_penalty
                reasons.append("Low engagement - depth penalized")
            # Boost simpler breadth/coverage
            elif strategy.get("type_category") in ["breadth", "coverage"]:
                boost = 1.0 / self.low_penalty
                score *= boost
                reasons.append("Low engagement - simpler strategies encouraged")

        elif engagement == "high":
            # High engagement: boost depth strategies
            if strategy.get("type_category") == "depth":
                score *= self.high_boost
                reasons.append("High engagement - depth encouraged")

        if not reasons:
            reasoning = f"Medium engagement (avg length={avg_length:.0f})"
        else:
            reasoning = "; ".join(reasons)

        logger.debug(
            "RichnessScorer output",
            strategy_id=strategy.get("id"),
            engagement=engagement,
            avg_length=avg_length,
            score=score,
        )

        return self.make_output(score, signals, reasoning)
