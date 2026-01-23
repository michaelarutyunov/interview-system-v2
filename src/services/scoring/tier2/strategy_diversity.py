"""Strategy Diversity scorer (Tier 2).

Measures recency of strategy use.
Encourages varied questioning patterns to avoid repetitive interview feel.
"""

from typing import Any, Dict, List, Optional

import structlog

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.two_tier.base import Tier2Scorer, Tier2Output

logger = structlog.get_logger(__name__)


class StrategyDiversityScorer(Tier2Scorer):
    """
    Scores candidates based on strategy recency to encourage variety.

    Tracks how often each strategy was used in recent turns.
    Penalizes overused strategies to maintain interview variety.

    Scoring logic:
    - Strategy used 0-1 times in last 5 turns → neutral (1.0)
    - Strategy used 2 times in last 5 turns → penalty (0.8)
    - Strategy used 3+ times in last 5 turns → strong penalty (0.6)

    Weight: 0.10-0.15 (lower - variety is good but not primary goal)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        if "weight" not in self.config:
            self.weight = 0.10

        # Lookback window for counting strategy usage
        self.lookback_window = self.params.get("lookback_window", 5)

        # Penalty thresholds
        self.moderate_use_threshold = self.params.get("moderate_use_threshold", 2)
        self.overuse_threshold = self.params.get("overuse_threshold", 3)

        # Penalty values
        self.moderate_penalty = self.params.get("moderate_penalty", 0.8)
        self.overuse_penalty = self.params.get("overuse_penalty", 0.6)

        logger.info(
            "StrategyDiversityScorer initialized",
            weight=self.weight,
            lookback_window=self.lookback_window,
        )

    async def score(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
        recent_nodes: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]],
    ) -> Tier2Output:
        """Score based on strategy recency to encourage variety.

        Args:
            strategy: Strategy being evaluated
            focus: Focus target
            graph_state: Current graph state
            recent_nodes: Recent nodes from graph
            conversation_history: Recent conversation turns

        Returns:
            Tier2Output with score based on strategy usage recency
        """
        # Get strategy ID
        strategy_id = strategy.get("id", "")

        # Count how many times this strategy was used recently
        # This would require tracking strategy history in graph_state
        # For now, use a simplified approach

        # Check if strategy type info is in graph_state properties
        strategy_history = graph_state.properties.get("strategy_history", [])

        # Count recent uses of this strategy
        recent_uses = 0
        for hist_strategy_id in strategy_history[-self.lookback_window:]:
            if hist_strategy_id == strategy_id:
                recent_uses += 1

        # Score based on usage count
        if recent_uses == 0:
            raw_score = 1.0
            reasoning = f"Strategy {strategy_id} not used recently"
        elif recent_uses == 1:
            raw_score = 1.0
            reasoning = f"Strategy {strategy_id} used once recently (neutral)"
        elif recent_uses == 2:
            raw_score = self.moderate_penalty
            reasoning = f"Strategy {strategy_id} used {recent_uses} times recently (moderate penalty)"
        else:  # 3 or more
            raw_score = self.overuse_penalty
            reasoning = f"Strategy {strategy_id} used {recent_uses} times recently (strong penalty)"

        signals = {
            "strategy_id": strategy_id,
            "recent_uses": recent_uses,
            "lookback_window": self.lookback_window,
            "strategy_history": strategy_history[-self.lookback_window:] if strategy_history else [],
        }

        logger.debug(
            "StrategyDiversityScorer scored",
            score=raw_score,
            strategy_id=strategy_id,
            recent_uses=recent_uses,
            reasoning=reasoning,
        )

        return self.make_output(raw_score=raw_score, signals=signals, reasoning=reasoning)
