"""Ambiguity scorer (Tier 2).

Measures clarity/confidence of nodes in the focus area.
Boosts strategies that clarify ambiguous content.

Enhanced with optional LLM signal integration for more nuanced
ambiguity detection that distinguishes between:
- Confidence qualification (productive uncertainty)
- Knowledge gaps (terminal uncertainty)
- Conceptual clarity issues (need for clarification)
"""

from typing import Any, Dict, List, Optional

import structlog

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.two_tier.base import Tier2Scorer, Tier2Output

logger = structlog.get_logger(__name__)


class AmbiguityScorer(Tier2Scorer):
    """
    Scores candidates based on ambiguity/uncertainty in the focus area.

    Measures clarity using:
    - Extraction confidence from node properties
    - Presence of hedge words ("maybe", "sort of", "I think")
    - Uncertainty markers in recent utterances

    Scoring logic:
    - High clarity (confidence > 0.8) → score ≈ 0.9 (no need to clarify)
    - Medium clarity (0.5-0.8) → score ≈ 1.2 (worth clarifying)
    - Low clarity (< 0.5) → score ≈ 1.5 (definitely needs clarification)

    Weight: 0.15-0.20 (medium - quality matters but secondary to coverage)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        if "weight" not in self.config:
            self.weight = 0.15

        # Confidence thresholds
        self.high_clarity_threshold = self.params.get("high_clarity_threshold", 0.8)
        self.low_clarity_threshold = self.params.get("low_clarity_threshold", 0.5)

        # Hedge words indicating uncertainty
        self.hedge_words = self.params.get(
            "hedge_words",
            [
                "maybe",
                "perhaps",
                "possibly",
                "sort of",
                "kind of",
                "i think",
                "i guess",
                "probably",
                "not sure",
                "uncertain",
            ],
        )

        # Enable LLM signal integration if available
        self.use_llm_signals = self.params.get("use_llm_signals", False)

        logger.info(
            "AmbiguityScorer initialized",
            weight=self.weight,
            high_threshold=self.high_clarity_threshold,
            low_threshold=self.low_clarity_threshold,
            use_llm_signals=self.use_llm_signals,
        )

    async def score(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
        recent_nodes: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]],
    ) -> Tier2Output:
        """Score based on ambiguity in the focus area.

        Args:
            strategy: Strategy being evaluated
            focus: Focus target (may contain node_id)
            graph_state: Current graph state (may contain LLM signals)
            recent_nodes: Recent nodes from graph
            conversation_history: Recent conversation turns

        Returns:
            Tier2Output with score based on ambiguity level
        """
        # Check for LLM-enhanced signals first (if enabled)
        if self.use_llm_signals:
            llm_result = self._score_with_llm_signals(
                strategy, focus, graph_state
            )
            if llm_result is not None:
                return llm_result

        # Fall back to rule-based pattern matching
        return await self._score_rule_based(
            strategy, focus, graph_state, recent_nodes, conversation_history
        )

    def _score_with_llm_signals(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
    ) -> Optional[Tier2Output]:
        """
        Score using LLM-extracted qualitative signals.

        Checks graph_state.properties for 'qualitative_signals' key containing
        QualitativeSignalSet. Uses uncertainty_signal if available.

        Args:
            strategy: Strategy being evaluated
            focus: Focus target
            graph_state: Current graph state

        Returns:
            Tier2Output if LLM signals available, None otherwise
        """
        # Get LLM signals from graph_state.properties
        qualitative_signals = graph_state.properties.get("qualitative_signals")

        if not qualitative_signals:
            return None

        # Extract uncertainty signal
        uncertainty_signal = qualitative_signals.get("uncertainty")
        if not uncertainty_signal:
            return None

        # Use LLM signal for nuanced scoring
        uncertainty_type = uncertainty_signal.get("uncertainty_type", "")
        severity = uncertainty_signal.get("severity", 0.5)
        confidence = uncertainty_signal.get("confidence", 0.7)

        # Map uncertainty type to score
        # High ambiguity = higher score (boost clarification strategies)
        if uncertainty_type == "knowledge_gap":
            # Terminal knowledge gap - strong boost for clarification
            raw_score = 1.6
            reasoning = f"LLM detected knowledge gap (severity: {severity:.2f}): {uncertainty_signal.get('reasoning', '')}"
        elif uncertainty_type == "conceptual_clarity":
            # User doesn't understand - very strong boost for clarification
            raw_score = 1.8
            reasoning = f"LLM detected conceptual clarity issue (severity: {severity:.2f}): {uncertainty_signal.get('reasoning', '')}"
        elif uncertainty_type == "apathy":
            # User disengaged - may need rapport repair, not clarification
            raw_score = 0.8
            reasoning = f"LLM detected apathy (severity: {severity:.2f}): clarification may not help"
        elif uncertainty_type == "epistemic_humility":
            # Honest uncertainty - moderate boost for clarification
            raw_score = 1.3
            reasoning = f"LLM detected epistemic humility (severity: {severity:.2f}): worth exploring"
        else:
            # confidence_qualification or default - mild boost
            raw_score = 1.1 + (severity * 0.3)
            reasoning = f"LLM detected {uncertainty_type} (severity: {severity:.2f}): {uncertainty_signal.get('reasoning', '')}"

        logger.debug(
            "AmbiguityScorer LLM-enhanced score",
            score=raw_score,
            uncertainty_type=uncertainty_type,
            severity=severity,
        )

        return self.make_output(
            raw_score=raw_score,
            signals={
                "llm_enhanced": True,
                "uncertainty_type": uncertainty_type,
                "severity": severity,
                "llm_confidence": confidence,
                "examples": uncertainty_signal.get("examples", []),
            },
            reasoning=reasoning,
        )

    async def _score_rule_based(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
        recent_nodes: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]],
    ) -> Tier2Output:
        """
        Score using rule-based pattern matching (original implementation).

        Args:
            strategy: Strategy being evaluated
            focus: Focus target
            graph_state: Current graph state
            recent_nodes: Recent nodes from graph
            conversation_history: Recent conversation turns

        Returns:
            Tier2Output with score based on ambiguity level
        """
        # Get node_id from focus if available
        node_id = focus.get("node_id")

        confidence_values = []
        hedge_count = 0

        if node_id and recent_nodes:
            # Find the node in recent_nodes
            target_node = next(
                (n for n in recent_nodes if str(n.get("id")) == str(node_id)), None
            )

            if target_node:
                # Get confidence from node properties
                confidence = target_node.get("confidence", 0.7)
                confidence_values.append(confidence)

                # Check for hedge words in node text
                node_text = target_node.get("label", "").lower()
                hedge_count = sum(1 for word in self.hedge_words if word in node_text)

        # Also check recent conversation for hedge words
        if conversation_history:
            for turn in conversation_history[-3:]:  # Last 3 turns
                text = turn.get("text", "").lower()
                hedge_count += sum(1 for word in self.hedge_words if word in text)

        # Calculate average confidence
        avg_confidence = (
            sum(confidence_values) / len(confidence_values)
            if confidence_values
            else 0.7
        )

        # Determine ambiguity level
        if avg_confidence > self.high_clarity_threshold and hedge_count == 0:
            # High clarity - slight penalty (no need to clarify)
            raw_score = 0.9
            reasoning = f"High clarity (confidence: {avg_confidence:.2f})"
        elif avg_confidence < self.low_clarity_threshold or hedge_count >= 2:
            # Low clarity - strong boost for clarification
            raw_score = 1.5
            reasoning = (
                f"Low clarity (confidence: {avg_confidence:.2f}, hedges: {hedge_count})"
            )
        else:
            # Medium clarity - moderate boost
            raw_score = 1.2
            reasoning = f"Medium clarity (confidence: {avg_confidence:.2f}, hedges: {hedge_count})"

        signals = {
            "avg_confidence": avg_confidence,
            "hedge_count": hedge_count,
            "confidence_values": confidence_values,
            "node_id": node_id,
            "llm_enhanced": False,
        }

        logger.debug(
            "AmbiguityScorer scored",
            score=raw_score,
            avg_confidence=avg_confidence,
            hedge_count=hedge_count,
            reasoning=reasoning,
        )

        return self.make_output(
            raw_score=raw_score, signals=signals, reasoning=reasoning
        )
