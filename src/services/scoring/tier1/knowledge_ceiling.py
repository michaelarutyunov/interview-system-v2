"""Knowledge Ceiling scorer (Tier 1).

Vetoes strategies when respondent explicitly indicates lack of knowledge
about the focus topic (e.g., "I don't know", "never heard of it").
"""

from typing import Any, Dict, List, Optional

import structlog

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.two_tier.base import Tier1Scorer, Tier1Output

logger = structlog.get_logger(__name__)


class KnowledgeCeilingScorer(Tier1Scorer):
    """
    Vetoes candidates when respondent lacks knowledge about the focus topic.

    Detects knowledge lack signals:
    - Explicit statements: "don't know", "no idea", "never heard of"
    - Uncertainty markers: "not sure", "unfamiliar with"
    - Negative responses: "no experience with", "never used"

    Veto condition: Any knowledge lack signal detected in recent conversation.

    Configuration:
    - negative_patterns: List of patterns to look for
    - min_confidence: Minimum confidence to consider
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # Knowledge lack patterns to detect
        self.negative_patterns = self.params.get(
            "negative_patterns",
            [
                "don't know",
                "do not know",
                "no idea",
                "never heard",
                "not sure",
                "unfamiliar",
                "no experience",
                "never used",
                "haven't tried",
                "can't say",
                "not familiar",
            ],
        )

        logger.info(
            "KnowledgeCeilingScorer initialized",
            patterns_count=len(self.negative_patterns),
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
        Evaluate whether to veto based on knowledge ceiling.

        Args:
            strategy: Strategy being evaluated
            focus: Focus target
            graph_state: Current graph state
            recent_nodes: Recent nodes from graph
            conversation_history: Recent conversation for analysis

        Returns:
            Tier1Output with veto decision
        """
        # Get the focus topic (element_id or node_id)
        element_id = focus.get("element_id")
        node_id = focus.get("node_id")
        focus_description = focus.get("focus_description", "")

        # Build search patterns for the focus topic
        topic_terms = self._extract_topic_terms(focus_description, element_id, node_id)

        if not topic_terms:
            # No specific topic to check - no veto
            return Tier1Output(
                scorer_id=self.scorer_id,
                is_veto=False,
                reasoning="No specific focus topic to check knowledge ceiling",
                signals={"topic_terms": topic_terms},
            )

        # Check recent conversation for knowledge lack signals
        recent_user_responses = [
            turn.get("text", "")
            for turn in conversation_history[-5:]  # Last 5 turns
            if turn.get("speaker") == "user"
        ]

        knowledge_lack_detected = False
        matched_patterns = []

        for response_text in recent_user_responses:
            response_lower = response_text.lower()

            for pattern in self.negative_patterns:
                if pattern in response_lower:
                    # Check if it's related to the focus topic
                    # Simple heuristic: if pattern appears near topic terms
                    if any(
                        term.lower() in response_lower
                        for term in topic_terms
                        if len(term) > 3
                    ):
                        knowledge_lack_detected = True
                        matched_patterns.append(f"{pattern} (near topic)")
                        break

            if knowledge_lack_detected:
                break

        if knowledge_lack_detected:
            logger.info(
                "Knowledge ceiling detected - vetoing",
                patterns=matched_patterns,
                topic_terms=topic_terms,
            )

            return Tier1Output(
                scorer_id=self.scorer_id,
                is_veto=True,
                reasoning=f"Respondent indicated lack of knowledge about topic: {', '.join(matched_patterns)}",
                signals={
                    "matched_patterns": matched_patterns,
                    "topic_terms": topic_terms,
                    "element_id": element_id,
                    "node_id": node_id,
                },
            )

        # No veto - respondent appears to have knowledge
        return Tier1Output(
            scorer_id=self.scorer_id,
            is_veto=False,
            reasoning="No knowledge lack signals detected for this topic",
            signals={
                "topic_terms": topic_terms,
                "checked_responses_count": len(recent_user_responses),
            },
        )

    def _extract_topic_terms(
        self,
        focus_description: str,
        element_id: Optional[str] = None,
        node_id: Optional[str] = None,
    ) -> List[str]:
        """
        Extract topic terms from focus for knowledge checking.

        Args:
            focus_description: Description of the focus
            element_id: Element identifier
            node_id: Node identifier

        Returns:
            List of topic terms to search for
        """
        terms = []

        # Add terms from description
        if focus_description:
            # Split into meaningful terms (filter out common words)
            words = focus_description.lower().split()
            meaningful_words = [
                w
                for w in words
                if len(w) > 3
                and w not in {"deepen", "cover", "explore", "understanding"}
            ]
            terms.extend(meaningful_words[:5])  # Top 5 words

        # Add element_id if available
        if element_id:
            terms.append(element_id.lower().replace("_", " "))

        # Add node label if available
        # Note: Would need to fetch from graph, using node_id as placeholder
        if node_id:
            # Could look up node in recent_nodes
            pass

        return list(set(terms))  # Remove duplicates


def create_knowledge_ceiling_scorer(
    config: Optional[Dict[str, Any]] = None,
) -> KnowledgeCeilingScorer:
    """Factory function to create KnowledgeCeilingScorer."""
    return KnowledgeCeilingScorer(config=config)
