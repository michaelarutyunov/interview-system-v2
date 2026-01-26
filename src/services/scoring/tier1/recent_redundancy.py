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
    Vetoes candidates when proposed question is too similar to recent questions OR
    when asking about something the user already explained (detected via user response similarity).

    Uses TF-IDF cosine similarity to detect when a proposed question
    would essentially repeat what was recently asked or answered.

    Similarity detection:
    - Character n-grams for robustness (handles typos, word variations)
    - Language-agnostic: no keyword patterns, purely semantic similarity
    - Configurable similarity threshold (default: 0.85)
    - Lookback window to limit comparison scope

    Veto condition: Similarity to any recent question OR user answer > threshold

    Configuration:
    - similarity_threshold: Minimum similarity to trigger veto (default: 0.85)
    - user_response_threshold: Threshold for user response similarity (default: 0.75)
    - lookback_window: How many recent turns to check (default: 6)
    - method: "tfidf_cosine" (TF-IDF with cosine similarity)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        self.similarity_threshold = self.params.get("similarity_threshold", 0.85)
        # Lower threshold for user responses - if user explained something, don't ask about it
        self.user_response_threshold = self.params.get("user_response_threshold", 0.75)
        self.lookback_window = self.params.get("lookback_window", 6)

        # Create similarity calculator
        self.similarity = create_similarity_calculator(
            {
                "similarity_threshold": self.similarity_threshold,
                "min_ngram": 2,  # Word pairs
                "max_ngram": 3,  # Word triples
            }
        )

        logger.info(
            "RecentRedundancyScorer initialized",
            similarity_threshold=self.similarity_threshold,
            user_response_threshold=self.user_response_threshold,
            lookback_window=self.lookback_window,
        )

    async def evaluate(
        self,
        strategy: Dict[str, Any],  # noqa: ARG002 (unused in base interface)
        focus: Dict[str, Any],
        graph_state: GraphState,  # noqa: ARG002 (unused in base interface)
        recent_nodes: List[Dict[str, Any]],  # noqa: ARG002 (unused in base interface)
        conversation_history: List[Dict[str, str]],
    ) -> Tier1Output:
        """
        Evaluate whether to veto based on recent redundancy.

        Checks similarity against both system questions AND user responses.
        This prevents asking about something the user already explained.

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

        # Extract recent system questions and user responses
        recent_questions = self._extract_recent_questions(conversation_history)
        recent_user_responses = self._extract_recent_user_responses(conversation_history)

        # Check 1: Similarity to recent system questions
        question_similarity = 0.0
        if recent_questions:
            _, question_similarity = self.similarity.is_too_similar(
                proposed_question,
                recent_questions,
            )

        # Check 2: Similarity to recent user responses (language-agnostic detection)
        # This catches when user already explained a topic and we're about to ask it again
        user_response_similarity = 0.0
        if recent_user_responses:
            _, user_response_similarity = self.similarity.is_too_similar(
                proposed_question,
                recent_user_responses,
            )

        # Determine veto based on either threshold
        is_question_redundant = question_similarity >= self.similarity_threshold
        is_user_already_explained = user_response_similarity >= self.user_response_threshold

        signals = {
            "proposed_question": proposed_question[:50],
            "question_similarity": round(question_similarity, 3),
            "question_threshold": self.similarity_threshold,
            "user_response_similarity": round(user_response_similarity, 3),
            "user_response_threshold": self.user_response_threshold,
            "recent_questions_count": len(recent_questions),
            "recent_responses_count": len(recent_user_responses),
        }

        if is_question_redundant:
            logger.info(
                "Recent redundancy detected - too similar to recent question",
                similarity=question_similarity,
                threshold=self.similarity_threshold,
            )

            return Tier1Output(
                scorer_id=self.scorer_id,
                is_veto=True,
                reasoning=f"Proposed question too similar to recent question (similarity: {question_similarity:.2f} >= {self.similarity_threshold})",
                signals=signals,
            )

        if is_user_already_explained:
            logger.info(
                "User already explained this topic - vetoing to avoid repetition",
                similarity=user_response_similarity,
                threshold=self.user_response_threshold,
            )

            return Tier1Output(
                scorer_id=self.scorer_id,
                is_veto=True,
                reasoning=f"User already explained this topic (response similarity: {user_response_similarity:.2f} >= {self.user_response_threshold})",
                signals=signals,
            )

        # No redundancy - no veto
        return Tier1Output(
            scorer_id=self.scorer_id,
            is_veto=False,
            reasoning=f"Question distinct from {len(recent_questions)} questions and {len(recent_user_responses)} user responses",
            signals=signals,
        )

    def _extract_recent_questions(
        self, conversation_history: List[Dict[str, str]]
    ) -> List[str]:
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
            turn
            for turn in conversation_history[-self.lookback_window :]
            if turn.get("speaker") == "system"
        ]

        for turn in system_turns:
            text = turn.get("text", "").strip()
            if text:
                recent_questions.append(text)

        return recent_questions

    def _extract_recent_user_responses(
        self, conversation_history: List[Dict[str, str]]
    ) -> List[str]:
        """
        Extract recent user responses from conversation history.

        Used for language-agnostic detection of topics the user already explained.
        If the proposed question is too similar to what the user already said,
        we should avoid asking about it again.

        Args:
            conversation_history: Full conversation history

        Returns:
            List of recent user response texts
        """
        recent_responses = []

        # Get last N user utterances
        user_turns = [
            turn
            for turn in conversation_history[-self.lookback_window :]
            if turn.get("speaker") == "user"
        ]

        for turn in user_turns:
            text = turn.get("text", "").strip()
            if text:
                recent_responses.append(text)

        return recent_responses


def create_recent_redundancy_scorer(
    config: Optional[Dict[str, Any]] = None,
) -> RecentRedundancyScorer:
    """Factory function to create RecentRedundancyScorer."""
    return RecentRedundancyScorer(config=config)
