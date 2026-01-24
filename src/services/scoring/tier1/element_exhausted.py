"""Element Exhausted scorer (Tier 1).

Vetoes strategies when a focus element has been mentioned too many times
and relationships have been established (no more to learn).
"""

from typing import Any, Dict, List, Optional

import structlog

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.two_tier.base import Tier1Scorer, Tier1Output

logger = structlog.get_logger(__name__)


class ElementExhaustedScorer(Tier1Scorer):
    """
    Vetoes candidates when focus element has been sufficiently explored.

    Checks if element has been:
    - Mentioned ≥ max_mentions times in recent conversation
    - Has established relationships (edges in graph)
    - No new information expected

    Veto condition: Element mentioned ≥ max_mentions AND has relationships

    Configuration:
    - max_mentions: Maximum mentions before veto (default: 5)
    - lookback_window: How many recent turns to check (default: 10)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        self.max_mentions = self.params.get("max_mentions", 5)
        self.lookback_window = self.params.get("lookback_window", 10)

        logger.info(
            "ElementExhaustedScorer initialized",
            max_mentions=self.max_mentions,
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
        Evaluate whether to veto based on element exhaustion.

        Args:
            strategy: Strategy being evaluated
            focus: Focus target
            graph_state: Current graph state
            recent_nodes: Recent nodes from graph
            conversation_history: Recent conversation for analysis

        Returns:
            Tier1Output with veto decision
        """
        # Get element_id from focus
        element_id = focus.get("element_id")

        if not element_id:
            # No element to check - no veto
            return Tier1Output(
                scorer_id=self.scorer_id,
                is_veto=False,
                reasoning="No element_id in focus - cannot check exhaustion",
                signals={"element_id": element_id},
            )

        # Count how many times this element appears in recent conversation
        mention_count = 0
        recent_turns = conversation_history[-self.lookback_window :]

        for turn in recent_turns:
            text = turn.get("text", "").lower()
            element_term = element_id.lower().replace("_", " ")

            if element_term in text:
                mention_count += 1

        # Check if element has established relationships in graph
        has_relationships = self._check_element_has_relationships(
            element_id, graph_state, recent_nodes
        )

        # Determine if exhausted
        is_exhausted = mention_count >= self.max_mentions and has_relationships

        if is_exhausted:
            logger.info(
                "Element exhausted - vetoing",
                element_id=element_id,
                mention_count=mention_count,
                has_relationships=has_relationships,
            )

            return Tier1Output(
                scorer_id=self.scorer_id,
                is_veto=True,
                reasoning=f"Element '{element_id}' has been mentioned {mention_count} times (max: {self.max_mentions}) and has established relationships",
                signals={
                    "element_id": element_id,
                    "mention_count": mention_count,
                    "has_relationships": has_relationships,
                },
            )

        # Not exhausted - no veto
        return Tier1Output(
            scorer_id=self.scorer_id,
            is_veto=False,
            reasoning=f"Element '{element_id}' mentioned {mention_count} times (threshold: {self.max_mentions})",
            signals={
                "element_id": element_id,
                "mention_count": mention_count,
                "has_relationships": has_relationships,
            },
        )

    def _check_element_has_relationships(
        self,
        element_id: str,
        graph_state: GraphState,
        recent_nodes: List[Dict[str, Any]],
    ) -> bool:
        """
        Check if element has established relationships in the graph.

        Args:
            element_id: Element to check
            graph_state: Current graph state
            recent_nodes: Recent nodes for analysis

        Returns:
            True if element has edges/relationships, False otherwise
        """
        # Check if there are nodes related to this element
        # Look for nodes with labels containing the element term
        element_term = element_id.lower().replace("_", " ")

        related_nodes = [
            n for n in recent_nodes if element_term in n.get("label", "").lower()
        ]

        # If there are 2+ related nodes, likely has relationships
        return len(related_nodes) >= 2


def create_element_exhausted_scorer(
    config: Optional[Dict[str, Any]] = None,
) -> ElementExhaustedScorer:
    """Factory function to create ElementExhaustedScorer."""
    return ElementExhaustedScorer(config=config)
