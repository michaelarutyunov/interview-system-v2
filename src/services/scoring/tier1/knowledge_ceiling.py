"""Knowledge Ceiling scorer (Tier 1).

Vetoes strategies when respondent explicitly indicates lack of knowledge
about the focus topic (e.g., "I don't know", "never heard of it").

Enhanced with optional LLM signal integration for more nuanced detection:
- Distinguishes between terminal and exploratory "I don't know"
- Detects curiosity despite knowledge gaps
- Identifies redirection opportunities
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

        # Consecutive terminal response tracking (from ConsecutiveExhaustionScorer)
        self.consecutive_terminal_threshold = self.params.get(
            "consecutive_terminal_threshold", 3
        )

        # Enable LLM signal integration if available
        self.use_llm_signals = self.params.get("use_llm_signals", False)

        logger.info(
            "KnowledgeCeilingScorer initialized",
            patterns_count=len(self.negative_patterns),
            use_llm_signals=self.use_llm_signals,
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
            graph_state: Current graph state (may contain LLM signals)
            recent_nodes: Recent nodes from graph
            conversation_history: Recent conversation for analysis

        Returns:
            Tier1Output with veto decision
        """
        # Check for LLM-enhanced signals first (if enabled)
        if self.use_llm_signals:
            llm_result = self._evaluate_with_llm_signals(strategy, focus, graph_state)
            if llm_result is not None:
                return llm_result

        # Fall back to rule-based pattern matching
        return await self._evaluate_rule_based(
            strategy, focus, graph_state, conversation_history
        )

    def _get_consecutive_terminal_count(self, graph_state: GraphState) -> int:
        """
        Get the current count of consecutive terminal responses from graph_state.

        Args:
            graph_state: Current graph state

        Returns:
            Current consecutive terminal response count
        """
        return graph_state.properties.get("consecutive_terminal_count", 0)

    def _set_consecutive_terminal_count(
        self, graph_state: GraphState, count: int
    ) -> None:
        """
        Set the consecutive terminal response count in graph_state.

        Args:
            graph_state: Current graph state (will be modified)
            count: New count to store
        """
        graph_state.properties["consecutive_terminal_count"] = count

    def _evaluate_with_llm_signals(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
    ) -> Optional[Tier1Output]:
        """
        Evaluate using LLM-extracted qualitative signals.

        Checks graph_state.properties for 'qualitative_signals' key containing
        QualitativeSignalSet. Uses knowledge_ceiling signal if available.

        Also tracks consecutive terminal responses and vetoes deepen/broaden/cover
        when threshold is exceeded (consolidating ConsecutiveExhaustionScorer).

        Args:
            strategy: Strategy being evaluated
            focus: Focus target
            graph_state: Current graph state

        Returns:
            Tier1Output if LLM signals available and decisive, None otherwise
        """
        # Get LLM signals from graph_state.properties
        qualitative_signals = graph_state.properties.get("qualitative_signals")

        if not qualitative_signals:
            logger.debug("No LLM qualitative signals available in graph_state")
            return None

        # Extract knowledge ceiling signal
        kc_signal = qualitative_signals.get("knowledge_ceiling")
        if not kc_signal:
            logger.debug("No knowledge_ceiling signal in LLM qualitative signals")
            return None

        # Track consecutive terminal responses (from ConsecutiveExhaustionScorer)
        current_count = self._get_consecutive_terminal_count(graph_state)
        is_terminal = kc_signal.get("is_terminal", False)

        # Track new count (initialize to current, may be updated below)
        new_count = current_count

        if is_terminal:
            # Increment consecutive terminal counter
            new_count = current_count + 1
            self._set_consecutive_terminal_count(graph_state, new_count)
            logger.debug(
                "Terminal response detected",
                new_count=new_count,
                threshold=self.consecutive_terminal_threshold,
            )
        else:
            # Reset counter on non-terminal response
            if current_count > 0:
                new_count = 0
                self._set_consecutive_terminal_count(graph_state, 0)
                logger.debug("Non-terminal response - reset consecutive count")

        strategy_id = strategy.get("id", "")

        # Check if strategy is exempt (process-management strategies)
        if self.is_strategy_exempt(strategy_id):
            logger.debug(
                "Knowledge ceiling signal but strategy is exempt",
                strategy_id=strategy_id,
                is_terminal=is_terminal,
            )
            return Tier1Output(
                scorer_id=self.scorer_id,
                is_veto=False,
                reasoning=f"LLM detected {kc_signal.get('response_type')} but {strategy_id} is exempt from veto (process-management strategy)",
                signals={
                    "llm_enhanced": True,
                    "exempt_strategy": strategy_id,
                    "is_terminal": is_terminal,
                },
            )

        # Check consecutive terminal threshold (from ConsecutiveExhaustionScorer)
        if new_count >= self.consecutive_terminal_threshold:
            # Veto deepen/broaden/cover on consecutive terminal responses
            if strategy_id in ["deepen", "broaden", "cover_element"]:
                logger.info(
                    "LLM signal: Consecutive terminal threshold exceeded - vetoing content strategies",
                    consecutive_count=new_count,
                    threshold=self.consecutive_terminal_threshold,
                    vetoed_strategy=strategy_id,
                )
                return Tier1Output(
                    scorer_id=self.scorer_id,
                    is_veto=True,
                    reasoning=f"LLM detected {new_count} consecutive terminal responses (threshold: {self.consecutive_terminal_threshold}). Last: {kc_signal.get('response_type')}. Vetoing {strategy_id}.",
                    signals={
                        "llm_enhanced": True,
                        "response_type": kc_signal.get("response_type"),
                        "has_curiosity": kc_signal.get("has_curiosity"),
                        "consecutive_count": new_count,
                        "threshold": self.consecutive_terminal_threshold,
                    },
                )
            else:
                # Allow other strategies even with consecutive terminal responses
                logger.debug(
                    "LLM signal: Consecutive terminal responses but allowing non-content strategy",
                    consecutive_count=new_count,
                    strategy_id=strategy_id,
                )
                return Tier1Output(
                    scorer_id=self.scorer_id,
                    is_veto=False,
                    reasoning=f"LLM detected {new_count} consecutive terminal responses but {strategy_id} is allowed (non-content strategy)",
                    signals={
                        "llm_enhanced": True,
                        "response_type": kc_signal.get("response_type"),
                        "consecutive_count": new_count,
                        "threshold": self.consecutive_terminal_threshold,
                    },
                )

        # Use LLM signal for nuanced decision
        if is_terminal:
            # Terminal knowledge ceiling - veto depth strategies
            strategy_type = strategy.get("type_category", "")
            if strategy_type == "depth" or strategy_id == "deepen":
                logger.info(
                    "LLM signal: Terminal knowledge ceiling detected - vetoing deepen",
                    response_type=kc_signal.get("response_type"),
                    has_curiosity=kc_signal.get("has_curiosity"),
                )
                return Tier1Output(
                    scorer_id=self.scorer_id,
                    is_veto=True,
                    reasoning=f"LLM detected terminal knowledge ceiling ({kc_signal.get('response_type')}): {kc_signal.get('reasoning', '')}",
                    signals={
                        "llm_enhanced": True,
                        "response_type": kc_signal.get("response_type"),
                        "has_curiosity": kc_signal.get("has_curiosity"),
                        "redirection_available": kc_signal.get("redirection_available"),
                        "confidence": kc_signal.get("confidence"),
                    },
                )
            else:
                # Allow breadth/coverage strategies even with terminal ceiling
                logger.debug(
                    "LLM signal: Terminal knowledge ceiling but allowing non-depth strategy",
                    strategy_id=strategy_id,
                )
                return Tier1Output(
                    scorer_id=self.scorer_id,
                    is_veto=False,
                    reasoning=f"LLM detected terminal knowledge ceiling but {strategy_id} may still be productive",
                    signals={
                        "llm_enhanced": True,
                        "allowed_strategies": "breadth/coverage",
                        "response_type": kc_signal.get("response_type"),
                    },
                )
        else:
            # Non-terminal - no veto based on knowledge ceiling
            logger.debug(
                "LLM signal: No terminal knowledge ceiling",
                response_type=kc_signal.get("response_type"),
                has_curiosity=kc_signal.get("has_curiosity"),
            )
            return Tier1Output(
                scorer_id=self.scorer_id,
                is_veto=False,
                reasoning=f"LLM detected {kc_signal.get('response_type')} response with curiosity: {kc_signal.get('reasoning', '')}",
                signals={
                    "llm_enhanced": True,
                    "response_type": kc_signal.get("response_type"),
                    "has_curiosity": kc_signal.get("has_curiosity"),
                    "confidence": kc_signal.get("confidence"),
                },
            )

    async def _evaluate_rule_based(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
        conversation_history: List[Dict[str, str]],
    ) -> Tier1Output:
        """
        Evaluate using rule-based pattern matching (original implementation).

        Args:
            strategy: Strategy being evaluated
            focus: Focus target
            graph_state: Current graph state
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
                signals={"topic_terms": topic_terms, "llm_enhanced": False},
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
                    "llm_enhanced": False,
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
                "llm_enhanced": False,
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
