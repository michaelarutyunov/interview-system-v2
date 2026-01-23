"""Recent Redundancy scorer (Tier 1).

Vetoes strategies when the proposed question is too similar to recent questions,
using TF-IDF cosine similarity to detect semantic overlap.
"""

from typing import Any, Dict, List, Optional

import structlog

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.two_tier.base import Tier1Scorer, Tier1Output
from src.services.scoring.tier1.text_similarity import create_similarity_calculator

logger = structlog.get_logger(__name__)


class RecentRedundancyScorer(Tier1Scorer):
    """
    Vetoes candidates when proposed question is too similar to recent questions.

    Uses TF-IDF cosine similarity to detect when a proposed question
    would essentially repeat what was recently asked.

    Similarity detection:
    - Character n-grams for robustness (handles typos, word variations)
    - Configurable similarity threshold (default: 0.85)
    - Lookback window to limit comparison scope

    Veto condition: Similarity to any recent question > threshold

    Configuration:
    - similarity_threshold: Minimum similarity to trigger veto (default: 0.85)
    - lookback_window: How many recent questions to check (default: 6)
    - method: "tfidf_cosine" (TF-IDF with cosine similarity)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        self.similarity_threshold = self.params.get("similarity_threshold", 0.85)
        self.lookback_window = self.params.get("lookback_window", 6)

        # Create similarity calculator
        self.similarity = create_similarity_calculator({
            "similarity_threshold": self.similarity_threshold,
            "min_ngram": 2,  # Word pairs
            "max_ngram": 3,  # Word triples
        })

        logger.info(
            "RecentRedundancyScorer initialized",
            similarity_threshold=self.similarity_threshold,
            lookback_window=self.lookback_window,
        )

    async def evaluate(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
        recent_nodes: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]],
    ) -> Tier1Output:
        """
        Evaluate whether to veto based on recent redundancy.

        Args:
            strategy: Strategy being evaluated
            focus: Focus target (includes question description)
            graph_state: Current graph state
            recent_nodes: Recent nodes from graph
            conversation_history: Recent conversation for analysis

        Returns:
            Tier1Output with veto decision
        """
        # Get the proposed question from focus
        proposed_question = focus.get("focus_description", "")

        if not proposed_question:
            # No question to check - no veto
            return Tier1Output(
                scorer_id=self.scorer_id,
                is_veto=False,
                reasoning="No question in focus - cannot check redundancy",
                signals={"proposed_question": proposed_question},
            )

        # Extract recent system questions from conversation history
        recent_questions = self._extract_recent_questions(conversation_history)

        if not recent_questions:
            # No recent questions to compare - no veto
            return Tier1Output(
                scorer_id=self.scorer_id,
                is_veto=False,
                reasoning="No recent questions to compare against",
                signals={
                    "proposed_question": proposed_question,
                    "recent_questions_count": 0,
                },
            )

        # Check similarity
        is_too_similar, max_similarity = self.similarity.is_too_similar(
            proposed_question,
            recent_questions,
        )

        if is_too_similar:
            logger.info(
                "Recent redundancy detected - vetoing",
                similarity=max_similarity,
                threshold=self.similarity_threshold,
            )

            return Tier1Output(
                scorer_id=self.scorer_id,
                is_veto=True,
                reasoning=f"Proposed question too similar to recent question (similarity: {max_similarity:.2f} >= {self.similarity_threshold})",
                signals={
                    "similarity": max_similarity,
                    "threshold": self.similarity_threshold,
                    "proposed_question": proposed_question[:50],  # First 50 chars
                    "recent_questions_count": len(recent_questions),
                },
            )

        # No redundancy - no veto
        return Tier1Output(
            scorer_id=self.scorer_id,
            is_veto=False,
            reasoning=f"Question sufficiently distinct from recent {len(recent_questions)} questions",
            signals={
                "similarity": max_similarity,
                "threshold": self.similarity_threshold,
                "proposed_question": proposed_question[:50],
            },
        )

    def _extract_recent_questions(self, conversation_history: List[Dict[str, str]]) -> List[str]:
        """
        Extract recent system questions from conversation history.

        Args:
            conversation_history: Full conversation history

        Returns:
            List of recent system question texts
        """
        recent_questions = []

        # Get last N system utterances
        system_turns = [
            turn for turn in conversation_history[-self.lookback_window:]
            if turn.get("speaker") == "system"
        ]

        for turn in system_turns:
            text = turn.get("text", "").strip()
            if text:
                recent_questions.append(text)

        return recent_questions


def create_recent_redundancy_scorer(config: Optional[Dict[str, Any]] = None) -> RecentRedundancyScorer:
    """Factory function to create RecentRedundancyScorer."""
    return RecentRedundancyScorer(config=config)
