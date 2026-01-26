"""Clarification Veto scorer (Tier 1).

Vetoes depth/bridge strategies when respondent shows conceptual confusion
(e.g., "I don't understand", "what do you mean").

Uses LLM signal integration to distinguish between:
- Conceptual clarity issues (need rephrasing)
- Knowledge gaps (need redirection)
- Apathy (need rapport repair)
"""

from typing import Any, Dict, List, Optional

import structlog

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.two_tier.base import Tier1Scorer, Tier1Output

logger = structlog.get_logger(__name__)


class ClarificationVetoScorer(Tier1Scorer):
    """
    Vetoes candidates when respondent shows conceptual confusion.

    Detects confusion signals from LLM-extracted qualitative signals:
    - uncertainty_type: "conceptual_clarity" indicates user doesn't understand
    - severity: 0.0-1.0 scale of how confused the user is

    Veto condition:
    - uncertainty_type == "conceptual_clarity"
    - severity > threshold (default 0.3)
    - strategy in vetoed_strategies (deepen, broaden, bridge by default)

    Configuration:
    - severity_threshold: Minimum severity to trigger veto (default 0.3)
    - vetoed_strategies: List of strategy IDs to veto (default: deepen, broaden, bridge)
    - use_llm_signals: Enable LLM signal integration (default: True)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # Severity threshold for triggering veto
        self.severity_threshold = self.params.get("severity_threshold", 0.3)

        # Strategies to veto when confusion detected
        self.vetoed_strategies = self.params.get(
            "vetoed_strategies", ["deepen", "broaden", "bridge"]
        )

        # Enable LLM signal integration
        self.use_llm_signals = self.params.get("use_llm_signals", True)

        logger.info(
            "ClarificationVetoScorer initialized",
            severity_threshold=self.severity_threshold,
            vetoed_strategies=self.vetoed_strategies,
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
        Evaluate whether to veto based on conceptual confusion.

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

    def _evaluate_with_llm_signals(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
    ) -> Optional[Tier1Output]:
        """
        Evaluate using LLM-extracted qualitative signals.

        Checks graph_state.properties for 'qualitative_signals' key containing
        QualitativeSignalSet. Uses uncertainty_signal if available.

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

        # Extract uncertainty signal
        uncertainty_signal = qualitative_signals.get("uncertainty")
        if not uncertainty_signal:
            logger.debug("No uncertainty signal in LLM qualitative signals")
            return None

        # Get uncertainty type and severity
        uncertainty_type = uncertainty_signal.get("uncertainty_type", "")
        severity = uncertainty_signal.get("severity", 0.0)

        # Check if this is a conceptual clarity issue above threshold
        if (
            uncertainty_type == "conceptual_clarity"
            and severity > self.severity_threshold
        ):
            strategy_id = strategy.get("id", "")

            # Check if strategy is exempt (process-management strategies)
            if self.is_strategy_exempt(strategy_id):
                logger.debug(
                    "ClarificationVetoScorer: Confusion detected but strategy is exempt",
                    strategy_id=strategy_id,
                    severity=severity,
                )
                return Tier1Output(
                    scorer_id=self.scorer_id,
                    is_veto=False,
                    reasoning=f"Conceptual confusion detected but {strategy_id} is exempt from veto (process-management strategy)",
                    signals={
                        "uncertainty_type": uncertainty_type,
                        "severity": severity,
                        "exempt_strategy": strategy_id,
                    },
                )

            # Veto only if this is a depth/bridge strategy
            if strategy_id in self.vetoed_strategies:
                logger.info(
                    "ClarificationVetoScorer: Vetoing %s due to conceptual confusion",
                    strategy_id,
                    severity=severity,
                    uncertainty_type=uncertainty_type,
                )
                return Tier1Output(
                    scorer_id=self.scorer_id,
                    is_veto=True,
                    reasoning=f"User shows conceptual confusion (severity: {severity:.2f}, "
                    f"threshold: {self.severity_threshold}): "
                    f"{uncertainty_signal.get('reasoning', '')}",
                    signals={
                        "uncertainty_type": uncertainty_type,
                        "severity": severity,
                        "threshold": self.severity_threshold,
                        "llm_enhanced": True,
                        "vetoed_strategies": self.vetoed_strategies,
                    },
                )
            else:
                # Allow non-vetoed strategies (clarify, ease, synthesis, etc.)
                logger.debug(
                    "ClarificationVetoScorer: Confusion detected but allowing %s",
                    strategy_id,
                    severity=severity,
                )
                return Tier1Output(
                    scorer_id=self.scorer_id,
                    is_veto=False,
                    reasoning=f"Conceptual confusion detected but {strategy_id} may still be productive",
                    signals={
                        "uncertainty_type": uncertainty_type,
                        "severity": severity,
                        "llm_enhanced": True,
                        "allowed_strategy": strategy_id,
                    },
                )

        # No veto - confusion not detected or below threshold
        logger.debug(
            "ClarificationVetoScorer: No veto",
            uncertainty_type=uncertainty_type,
            severity=severity,
            threshold=self.severity_threshold,
        )
        return Tier1Output(
            scorer_id=self.scorer_id,
            is_veto=False,
            reasoning=f"No conceptual confusion above threshold (detected: {uncertainty_type}, "
            f"severity: {severity:.2f}, threshold: {self.severity_threshold})",
            signals={
                "uncertainty_type": uncertainty_type,
                "severity": severity,
                "threshold": self.severity_threshold,
                "llm_enhanced": True,
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
        Evaluate using rule-based pattern matching (fallback).

        Checks recent conversation for explicit confusion markers.

        Args:
            strategy: Strategy being evaluated
            focus: Focus target
            graph_state: Current graph state
            conversation_history: Recent conversation for analysis

        Returns:
            Tier1Output with veto decision
        """
        # Confusion patterns to detect
        confusion_patterns = [
            "i don't understand",
            "i do not understand",
            "what do you mean",
            "not sure what you mean",
            "don't get it",
            "do not get it",
            "confused",
            "don't follow",
            "do not follow",
            "not clear",
            "unclear",
        ]

        # Check recent user responses for confusion markers
        recent_user_responses = [
            turn.get("text", "")
            for turn in conversation_history[-3:]  # Last 3 turns
            if turn.get("speaker") == "user"
        ]

        confusion_detected = False
        matched_patterns = []

        for response_text in recent_user_responses:
            response_lower = response_text.lower()

            for pattern in confusion_patterns:
                if pattern in response_lower:
                    confusion_detected = True
                    matched_patterns.append(pattern)
                    break

            if confusion_detected:
                break

        if confusion_detected:
            strategy_id = strategy.get("id", "")

            # Veto only depth/bridge strategies on confusion
            if strategy_id in self.vetoed_strategies:
                logger.info(
                    "ClarificationVetoScorer: Rule-based veto",
                    patterns=matched_patterns,
                    strategy_id=strategy_id,
                )
                return Tier1Output(
                    scorer_id=self.scorer_id,
                    is_veto=True,
                    reasoning=f"User indicated confusion: {', '.join(matched_patterns)}",
                    signals={
                        "matched_patterns": matched_patterns,
                        "vetoed_strategies": self.vetoed_strategies,
                        "llm_enhanced": False,
                    },
                )
            else:
                # Allow non-vetoed strategies
                return Tier1Output(
                    scorer_id=self.scorer_id,
                    is_veto=False,
                    reasoning=f"User confusion detected but {strategy_id} may still be productive",
                    signals={
                        "matched_patterns": matched_patterns,
                        "allowed_strategy": strategy_id,
                        "llm_enhanced": False,
                    },
                )

        # No veto - no confusion detected
        return Tier1Output(
            scorer_id=self.scorer_id,
            is_veto=False,
            reasoning="No confusion signals detected in recent conversation",
            signals={
                "checked_responses_count": len(recent_user_responses),
                "llm_enhanced": False,
            },
        )


def create_clarification_veto_scorer(
    config: Optional[Dict[str, Any]] = None,
) -> ClarificationVetoScorer:
    """Factory function to create ClarificationVetoScorer."""
    return ClarificationVetoScorer(config=config)
