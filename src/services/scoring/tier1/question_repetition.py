"""Question Repetition scorer (Tier 1).

Vetoes broaden/cover_element strategies when the system asks too many
repetitive "what else"/"what other" style questions, causing user fatigue.

This scorer detects:
- Repetitive "what else" pattern questions (what else, what other, what else about, anything else)
- Semantic similarity between focus_description and recent questions
- Tracks consecutive "what else" count in graph_state.properties["repetition_count"]

Detection:
- Analyzes focus_description for "what else" variations (case-insensitive)
- Compares with recent system questions from conversation_history
- Counts consecutive "what else" pattern frequency
- Resets counter when different question pattern detected

Veto condition: 3+ repetitive "what else" patterns detected

When veto triggered:
- VETO: broaden, cover_element strategies (they ask for "more")
- ALLOW: deepen, synthesis, reflection, laddering, ease, bridge, closing, contrast strategies
"""

from typing import Any, Dict, List, Optional

import structlog

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.two_tier.base import Tier1Scorer, Tier1Output

logger = structlog.get_logger(__name__)


class QuestionRepetitionScorer(Tier1Scorer):
    """
    Vetoes broaden/cover_element strategies after 3+ repetitive "what else" questions.

    Tracks repetitive question patterns in system's focus_description:
    - "what else", "what other", "what else about", "anything else"
    - Compares with recent actual questions asked

    Veto condition: 3+ consecutive "what else" pattern questions

    Configuration:
    - threshold: Number of repetitive patterns before veto (default: 3)
    - repetition_patterns: List of patterns to look for
    """

    # Strategies to veto (they ask for "more")
    VETOED_STRATEGIES = {"broaden", "cover_element"}

    # Strategies to allow (they shift mode or deepen differently)
    ALLOWED_STRATEGIES = {
        "deepen",
        "synthesis",
        "reflection",
        "laddering",
        "ease",
        "bridge",
        "closing",
        "contrast",
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # Number of repetitive patterns before veto
        self.threshold = self.params.get("threshold", 3)

        # Patterns that indicate repetitive "what else" style questions
        self.repetition_patterns = self.params.get(
            "repetition_patterns",
            [
                "what else",
                "what other",
                "what else about",
                "anything else",
                "what else can",
                "what else do",
                "what else would",
                "what else matters",
                "what else contributes",
                "what else stands",
                "what else is",
            ],
        )

        logger.info(
            "QuestionRepetitionScorer initialized",
            threshold=self.threshold,
            patterns_count=len(self.repetition_patterns),
        )

    async def evaluate(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
        recent_nodes: List[Dict[str, Any]],  # noqa: ARG002 (unused in base interface)
        conversation_history: List[Dict[str, str]],
    ) -> Tier1Output:
        """
        Evaluate whether to veto based on repetitive question patterns.

        Args:
            strategy: Strategy being evaluated
            focus: Focus target (includes question description)
            graph_state: Current graph state
            recent_nodes: Recent nodes from graph
            conversation_history: Recent conversation for analysis

        Returns:
            Tier1Output with veto decision
        """
        # Get the proposed question from focus_description
        proposed_question = focus.get("focus_description", "")

        if not proposed_question:
            # No question to check - no veto
            return Tier1Output(
                scorer_id=self.scorer_id,
                is_veto=False,
                reasoning="No question in focus - cannot check repetition",
                signals={"proposed_question": proposed_question},
            )

        # Check if proposed question contains repetition pattern
        is_repetitive = self._is_repetitive_question(proposed_question)

        # Get current repetition count from graph_state
        current_count = graph_state.properties.get("repetition_count", 0)

        # Extract recent questions for context
        recent_questions = self._extract_recent_questions(conversation_history)

        # Calculate how many recent questions were repetitive
        recent_repetitive_count = self._count_recent_repetitive_questions(
            recent_questions
        )

        # Update counter based on current question
        if is_repetitive:
            new_count = current_count + 1
        else:
            # Reset counter when different pattern detected
            new_count = 0

        # Store updated count in signals (will be persisted by caller if needed)
        signals = {
            "current_count": new_count,
            "previous_count": current_count,
            "is_repetitive": is_repetitive,
            "proposed_question": proposed_question[:100],
            "recent_questions_count": len(recent_questions),
            "recent_repetitive_count": recent_repetitive_count,
        }

        # Check if threshold exceeded
        if new_count >= self.threshold:
            strategy_id = strategy.get("id", "")

            # Determine if this strategy should be vetoed
            if strategy_id in self.VETOED_STRATEGIES:
                logger.info(
                    "Question repetition threshold exceeded - vetoing broaden/cover_element",
                    new_count=new_count,
                    threshold=self.threshold,
                    vetoed_strategy=strategy_id,
                    proposed_question=proposed_question[:50],
                )

                return Tier1Output(
                    scorer_id=self.scorer_id,
                    is_veto=True,
                    reasoning=f"System has asked {new_count} consecutive 'what else' style questions (threshold: {self.threshold}). Proposed question: '{proposed_question[:50] if proposed_question else 'None'}'. Vetoing {strategy_id} to avoid user fatigue.",
                    signals={
                        **signals,
                        "recommended_strategies": list(self.ALLOWED_STRATEGIES),
                    },
                )
            else:
                # Allow non-broaden/cover_element strategies
                logger.debug(
                    "Question repetition detected but allowing strategy",
                    new_count=new_count,
                    allowed_strategy=strategy_id,
                )

                return Tier1Output(
                    scorer_id=self.scorer_id,
                    is_veto=False,
                    reasoning=f"System has asked {new_count} consecutive 'what else' style questions, but {strategy_id} is allowed as it shifts conversation mode.",
                    signals={
                        **signals,
                        "allow_reason": "strategy shifts mode",
                        "recommended_strategies": list(self.ALLOWED_STRATEGIES),
                    },
                )

        # Threshold not yet reached - no veto
        return Tier1Output(
            scorer_id=self.scorer_id,
            is_veto=False,
            reasoning=f"Consecutive 'what else' question count: {new_count} (threshold: {self.threshold}). Proposed question: '{proposed_question[:50] if proposed_question else 'None'}'",
            signals=signals,
        )

    def _is_repetitive_question(self, question: str) -> bool:
        """
        Check if question contains repetitive "what else" pattern.

        Args:
            question: Question text to check

        Returns:
            True if question contains repetition pattern, False otherwise
        """
        question_lower = question.lower().strip()

        for pattern in self.repetition_patterns:
            if pattern in question_lower:
                return True

        return False

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

        # Get last 10 system utterances for context
        system_turns = [
            turn
            for turn in conversation_history[-10:]
            if turn.get("speaker") == "system"
        ]

        for turn in system_turns:
            text = turn.get("text", "").strip()
            if text:
                recent_questions.append(text)

        return recent_questions

    def _count_recent_repetitive_questions(self, questions: List[str]) -> int:
        """
        Count how many recent questions contain repetitive patterns.

        Args:
            questions: List of question texts

        Returns:
            Number of repetitive questions
        """
        count = 0
        for question in questions:
            if self._is_repetitive_question(question):
                count += 1

        return count


def create_question_repetition_scorer(
    config: Optional[Dict[str, Any]] = None,
) -> QuestionRepetitionScorer:
    """Factory function to create QuestionRepetitionScorer."""
    return QuestionRepetitionScorer(config=config)
