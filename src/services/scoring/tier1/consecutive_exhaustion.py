"""Consecutive Exhaustion scorer (Tier 1).

Vetoes deepen/broaden strategies when user gives 3+ consecutive exhaustion
responses (e.g., "nothing", "nothing else", "nothing really", "don't know").

This prevents the system from repeatedly asking "What else" questions when
the user has indicated they have nothing more to add.

Detection:
- Analyzes conversation_history to count consecutive exhaustion responses
- Detects patterns: "nothing", "nothing else", "nothing really", "don't know", "can't think of anything"
- Resets counter when non-exhaustion response detected
- Veto condition: 3+ consecutive exhaustion responses

When veto triggered:
- VETO: deepen, broaden, cover_element strategies (they ask for "more" content)
- ALLOW: synthesis, reflection, laddering, ease, bridge, closing, contrast strategies (they shift conversation mode)
"""

from typing import Any, Dict, List, Optional

import structlog

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.two_tier.base import Tier1Scorer, Tier1Output

logger = structlog.get_logger(__name__)


class ConsecutiveExhaustionScorer(Tier1Scorer):
    """
    Vetoes deepen/broaden strategies after 3+ consecutive exhaustion responses.

    Tracks consecutive exhaustion signals in conversation:
    - "nothing", "nothing else", "nothing really"
    - "don't know", "can't think of anything"
    - "that's it", "that's all"

    Veto condition: 3+ consecutive exhaustion responses

    Configuration:
    - threshold: Number of consecutive responses before veto (default: 3)
    - negative_patterns: List of patterns to look for
    """

    # Strategies to veto during exhaustion (they ask for "more")
    VETOED_STRATEGIES = {"deepen", "broaden", "cover_element"}

    # Strategies to allow during exhaustion (they shift mode)
    ALLOWED_STRATEGIES = {
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

        # Number of consecutive exhaustion responses before veto
        self.threshold = self.params.get("threshold", 3)

        # Patterns that indicate exhaustion
        self.negative_patterns = self.params.get(
            "negative_patterns",
            [
                "nothing",
                "nothing else",
                "nothing really",
                "nothing more",
                "nothing much",
                "nothing comes to mind",
                "don't know",
                "do not know",
                "can't think",
                "cannot think",
                "can't think of anything",
                "that's it",
                "that is it",
                "that's all",
                "that is all",
                "no, that's",
                "no, nothing",
                "nothing else i",
            ],
        )

        logger.info(
            "ConsecutiveExhaustionScorer initialized",
            threshold=self.threshold,
            patterns_count=len(self.negative_patterns),
        )

    async def evaluate(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],  # noqa: ARG002 (unused in base interface)
        graph_state: GraphState,  # noqa: ARG002 (unused in base interface)
        recent_nodes: List[Dict[str, Any]],  # noqa: ARG002 (unused in base interface)
        conversation_history: List[Dict[str, str]],
    ) -> Tier1Output:
        """
        Evaluate whether to veto based on consecutive exhaustion responses.

        Args:
            strategy: Strategy being evaluated
            focus: Focus target
            graph_state: Current graph state
            recent_nodes: Recent nodes from graph
            conversation_history: Recent conversation for analysis

        Returns:
            Tier1Output with veto decision
        """
        # Calculate consecutive exhaustion count from conversation history
        consecutive_count = self._calculate_consecutive_exhaustion(conversation_history)

        # Get latest user response for context
        latest_user_response = self._get_latest_user_response(conversation_history)

        # Check if threshold exceeded
        if consecutive_count >= self.threshold:
            strategy_id = strategy.get("id", "")

            # Determine if this strategy should be vetoed
            if strategy_id in self.VETOED_STRATEGIES:
                logger.info(
                    "Consecutive exhaustion threshold exceeded - vetoing deepen/broaden",
                    consecutive_count=consecutive_count,
                    threshold=self.threshold,
                    vetoed_strategy=strategy_id,
                    last_response=latest_user_response[:50]
                    if latest_user_response
                    else "",  # type: ignore[optional]
                )

                return Tier1Output(
                    scorer_id=self.scorer_id,
                    is_veto=True,
                    reasoning=f"User has given {consecutive_count} consecutive exhaustion responses (threshold: {self.threshold}). Last response: '{latest_user_response[:50] if latest_user_response else 'None'}'. Vetoing {strategy_id} to avoid repetitive 'what else' questions.",
                    signals={
                        "consecutive_count": consecutive_count,
                        "threshold": self.threshold,
                        "last_response": latest_user_response[:100]
                        if latest_user_response
                        else "",  # type: ignore[optional]
                        "strategy_type": strategy_id,
                        "recommended_strategies": list(self.ALLOWED_STRATEGIES),
                    },
                )
            else:
                # Allow non-deepen/broaden strategies
                logger.debug(
                    "Consecutive exhaustion detected but allowing strategy",
                    consecutive_count=consecutive_count,
                    allowed_strategy=strategy_id,
                )

                return Tier1Output(
                    scorer_id=self.scorer_id,
                    is_veto=False,
                    reasoning=f"User has given {consecutive_count} consecutive exhaustion responses, but {strategy_id} is allowed as it shifts conversation mode.",
                    signals={
                        "consecutive_count": consecutive_count,
                        "threshold": self.threshold,
                        "last_response": latest_user_response[:100]
                        if latest_user_response
                        else "",  # type: ignore[optional]
                        "strategy_type": strategy_id,
                        "allow_reason": "strategy shifts mode",
                    },
                )

        # Threshold not yet reached - no veto
        return Tier1Output(
            scorer_id=self.scorer_id,
            is_veto=False,
            reasoning=f"Consecutive exhaustion count: {consecutive_count} (threshold: {self.threshold}). Last response: '{latest_user_response[:50] if latest_user_response else 'None'}'",
            signals={
                "consecutive_count": consecutive_count,
                "threshold": self.threshold,
                "last_response": latest_user_response[:100]
                if latest_user_response
                else "",
            },
        )

    def _calculate_consecutive_exhaustion(
        self, conversation_history: List[Dict[str, str]]
    ) -> int:
        """
        Calculate consecutive exhaustion responses from conversation history.

        Walks backwards through conversation history, counting consecutive
        user responses that match exhaustion patterns. Stops at first
        non-exhaustion response.

        Args:
            conversation_history: Full conversation history

        Returns:
            Number of consecutive exhaustion responses
        """
        consecutive_count = 0

        # Walk backwards through conversation history
        for turn in reversed(conversation_history):
            if turn.get("speaker") != "user":
                continue

            text = turn.get("text", "").strip()
            if not text:
                continue

            if self._is_exhaustion_response(text):
                consecutive_count += 1
            else:
                # Stop at first non-exhaustion response
                break

        return consecutive_count

    def _get_latest_user_response(
        self, conversation_history: List[Dict[str, str]]
    ) -> Optional[str]:
        """
        Get the latest user response from conversation history.

        Args:
            conversation_history: Full conversation history

        Returns:
            Latest user response text or None
        """
        # Get last user utterance
        for turn in reversed(conversation_history):
            if turn.get("speaker") == "user":
                text = turn.get("text", "").strip()
                if text:
                    return text

        return None

    def _is_exhaustion_response(self, response: str) -> bool:
        """
        Check if response indicates exhaustion.

        Args:
            response: User response text

        Returns:
            True if response indicates exhaustion, False otherwise
        """
        response_lower = response.lower().strip()

        for pattern in self.negative_patterns:
            if pattern in response_lower:
                return True

        return False


def create_consecutive_exhaustion_scorer(
    config: Optional[Dict[str, Any]] = None,
) -> ConsecutiveExhaustionScorer:
    """Factory function to create ConsecutiveExhaustionScorer."""
    return ConsecutiveExhaustionScorer(config=config)
