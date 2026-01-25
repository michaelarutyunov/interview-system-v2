"""Engagement scorer (Tier 2).

Measures recent respondent engagement/momentum.
Adapts strategy complexity based on respondent energy level.
"""

from typing import Any, Dict, List, Optional

import structlog

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.two_tier.base import Tier2Scorer, Tier2Output

logger = structlog.get_logger(__name__)


class EngagementScorer(Tier2Scorer):
    """
    Scores candidates based on respondent engagement level.

    Measures engagement using:
    - Response length (longer = more engaged)
    - Elaboration markers ("because", "for example", "specifically")
    - Enthusiasm markers ("!", "really", "absolutely", "love")

    Scoring logic:
    - Low engagement (3+ consecutive low momentum) → favor simpler strategies
    - High engagement → neutral or slight boost for complex strategies

    Weight: 0.10-0.15 (lower - adaptation is important but not primary)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        if "weight" not in self.config:
            self.weight = 0.10

        # Momentum thresholds
        # Per bead 5rt (P3): Revisit after more data collection
        # Current values based on limited observation (35-70 range)
        # TODO: Analyze full dataset to set percentile-based thresholds
        # Recommended analysis when data available:
        # 1. Collect momentum scores from 100+ turns across multiple sessions
        # 2. Calculate percentiles: p25, p50 (median), p75, p90
        # 3. Set low_momentum_threshold = p25, high_momentum_threshold = p75
        # 4. Consider dynamic thresholds based on session phase
        self.low_momentum_threshold = self.params.get("low_momentum_threshold", 30)
        self.high_momentum_threshold = self.params.get("high_momentum_threshold", 70)

        # Alternative: percentile-based threshold configuration
        # When more data is available, can switch to this approach:
        # self.percentile_thresholds = self.params.get("percentile_thresholds", {
        #     "low_percentile": 25,   # p25 for low threshold
        #     "high_percentile": 75,  # p75 for high threshold
        #     "min_samples": 50,     # Minimum samples before using percentiles
        # })

        # Elaboration markers
        self.elaboration_markers = self.params.get(
            "elaboration_markers",
            ["because", "since", "for example", "specifically", "such as", "meaning"],
        )

        # Enthusiasm markers
        self.enthusiasm_markers = self.params.get(
            "enthusiasm_markers",
            ["!", "really", "absolutely", "love", "great", "perfect", "excited"],
        )

        logger.info(
            "EngagementScorer initialized",
            weight=self.weight,
            low_threshold=self.low_momentum_threshold,
            high_threshold=self.high_momentum_threshold,
        )

    async def score(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
        recent_nodes: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]],
    ) -> Tier2Output:
        """Score based on respondent engagement and adapt strategy complexity.

        Args:
            strategy: Strategy being evaluated
            focus: Focus target
            graph_state: Current graph state
            recent_nodes: Recent nodes from graph
            conversation_history: Recent conversation turns

        Returns:
            Tier2Output with score based on engagement level
        """
        # Calculate momentum from recent conversation
        momentum_scores = []
        low_momentum_count = 0

        if conversation_history:
            # Look at last 5 user responses
            user_responses = [
                turn
                for turn in conversation_history[-10:]
                if turn.get("speaker") == "user"
            ][-5:]

            for response in user_responses:
                text = response.get("text", "")
                momentum = self._calculate_momentum(text)
                momentum_scores.append(momentum)

                if momentum < self.low_momentum_threshold:
                    low_momentum_count += 1

        avg_momentum = (
            sum(momentum_scores) / len(momentum_scores) if momentum_scores else 50
        )

        # Get strategy complexity
        strategy_type = strategy.get("type_category", "")
        strategy_id = strategy.get("id", "")

        # Score based on engagement and strategy complexity
        raw_score = 1.0  # Default: neutral

        if low_momentum_count >= 3:
            # Low engagement - favor simpler strategies
            if strategy_type == "depth" or strategy_id == "deepen":
                # Deep strategies require more effort - penalty
                raw_score = 0.8
                reasoning = (
                    f"Low engagement (avg momentum: {avg_momentum:.0f}), "
                    f"favor simpler strategies over {strategy_id}"
                )
            else:
                # Simpler strategies - slight boost
                raw_score = 1.2
                reasoning = f"Low engagement (avg momentum: {avg_momentum:.0f}), favor {strategy_id}"
        elif avg_momentum > self.high_momentum_threshold:
            # High engagement - neutral or slight boost for complex
            if strategy_type == "depth":
                raw_score = 1.1
                reasoning = f"High engagement (avg momentum: {avg_momentum:.0f}), {strategy_id} appropriate"
            else:
                raw_score = 1.0
                reasoning = (
                    f"High engagement (avg momentum: {avg_momentum:.0f}), neutral"
                )
        else:
            # Medium engagement - neutral
            raw_score = 1.0
            reasoning = f"Medium engagement (avg momentum: {avg_momentum:.0f})"

        signals = {
            "avg_momentum": avg_momentum,
            "low_momentum_count": low_momentum_count,
            "momentum_scores": momentum_scores,
            "strategy_type": strategy_type,
        }

        logger.debug(
            "EngagementScorer scored",
            score=raw_score,
            avg_momentum=avg_momentum,
            low_momentum_count=low_momentum_count,
            reasoning=reasoning,
        )

        return self.make_output(
            raw_score=raw_score, signals=signals, reasoning=reasoning
        )

    def _calculate_momentum(self, text: str) -> float:
        """Calculate momentum score for a single response.

        Args:
            text: Response text

        Returns:
            Momentum score (0-200+)
        """
        # Base score from length
        length_score = len(text.split()) * 5

        # Bonus for elaboration markers
        elaboration_bonus = sum(
            20 for marker in self.elaboration_markers if marker in text.lower()
        )

        # Bonus for enthusiasm markers
        enthusiasm_bonus = sum(
            15 for marker in self.enthusiasm_markers if marker in text.lower()
        )

        return length_score + elaboration_bonus + enthusiasm_bonus
