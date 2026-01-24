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
        # NOTE: high_momentum_threshold lowered to 70 (from 100) to align with actual observed values
        # Session analysis shows momentum ranges 35-70; 100 was unreachable
        # Bead: 5rt - Revisit after more data collection (may need percentile-based thresholds)
        self.low_momentum_threshold = self.params.get("low_momentum_threshold", 30)
        self.high_momentum_threshold = self.params.get("high_momentum_threshold", 70)

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
