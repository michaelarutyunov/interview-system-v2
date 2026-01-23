"""Novelty scorer (Tier 2).

Measures whether focus target is "fresh" (not recently discussed).
Distributes attention across topics to prevent fixation.
"""

from typing import Any, Dict, List, Optional

import structlog

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.two_tier.base import Tier2Scorer, Tier2Output

logger = structlog.get_logger(__name__)


class NoveltyScorer(Tier2Scorer):
    """
    Scores candidates based on focus novelty/previous discussion.

    Penalizes recently-discussed topics to encourage breadth.
    Helps prevent fixation on single topics.

    Scoring logic:
    - Focus mentioned 0-1 times in last 8 turns → boost (1.2)
    - Focus mentioned 2-3 times → neutral (1.0)
    - Focus mentioned 4+ times → penalty (0.7)

    Weight: 0.10-0.15 (lower - novelty is good but not primary)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        if "weight" not in self.config:
            self.weight = 0.10

        # Lookback window for counting mentions
        self.lookback_window = self.params.get("lookback_window", 8)

        # Novelty thresholds
        self.fresh_threshold = self.params.get("fresh_threshold", 1)
        self.overdiscussed_threshold = self.params.get("overdiscussed_threshold", 4)

        # Score values
        self.fresh_boost = self.params.get("fresh_boost", 1.2)
        self.overdiscussed_penalty = self.params.get("overdiscussed_penalty", 0.7)

        logger.info(
            "NoveltyScorer initialized",
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
        """Score based on focus novelty to distribute attention.

        Args:
            strategy: Strategy being evaluated
            focus: Focus target (may contain node_id or element_id)
            graph_state: Current graph state
            recent_nodes: Recent nodes from graph
            conversation_history: Recent conversation turns

        Returns:
            Tier2Output with score based on focus novelty
        """
        # Get focus target
        node_id = focus.get("node_id")
        element_id = focus.get("element_id")
        focus_description = focus.get("focus_description", "")

        # Count how many times this focus has been mentioned recently
        mention_count = 0

        # Check recent nodes for mentions
        if node_id and recent_nodes:
            for node in recent_nodes[-self.lookback_window:]:
                if str(node.get("id")) == str(node_id):
                    mention_count += 1

        # Also check conversation history for focus keywords
        if focus_description and conversation_history:
            # Extract key terms from focus description
            key_terms = focus_description.lower().split()[:3]  # First 3 words
            for turn in conversation_history[-self.lookback_window:]:
                text = turn.get("text", "").lower()
                if any(term in text for term in key_terms if len(term) > 3):
                    mention_count += 1

        # Score based on mention count
        if mention_count <= self.fresh_threshold:
            raw_score = self.fresh_boost
            reasoning = f"Focus is fresh (mentioned {mention_count} times recently)"
        elif mention_count < self.overdiscussed_threshold:
            raw_score = 1.0
            reasoning = f"Focus moderately discussed (mentioned {mention_count} times recently)"
        else:
            raw_score = self.overdiscussed_penalty
            reasoning = f"Focus overdiscussed (mentioned {mention_count} times recently)"

        signals = {
            "mention_count": mention_count,
            "node_id": node_id,
            "element_id": element_id,
            "focus_description": focus_description,
            "lookback_window": self.lookback_window,
        }

        logger.debug(
            "NoveltyScorer scored",
            score=raw_score,
            mention_count=mention_count,
            reasoning=reasoning,
        )

        return self.make_output(raw_score=raw_score, signals=signals, reasoning=reasoning)
