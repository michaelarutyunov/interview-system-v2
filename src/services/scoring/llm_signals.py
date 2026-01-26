"""
LLM-based qualitative signal extraction for scoring.

This module provides semantic signal extraction from conversation history
using LLM analysis. These signals complement rule-based heuristics by
providing deeper insight into:
- Reasoning quality and depth
- Emotional engagement and trajectory
- Types of uncertainty expressed
- Contradictions and stance shifts
- Knowledge ceiling nuances
- Concept abstraction levels

ADR-006: Two-tier scoring - Layer 3 of signal architecture.
Phase 2 implementation of signal layer improvements.
"""

import time
from typing import Optional, List, Dict, Any

import structlog

from src.llm.client import LLMClient, get_scoring_llm_client, LLMResponse
from src.llm.prompts.qualitative_signals import (
    get_qualitative_signals_system_prompt,
    get_qualitative_signals_user_prompt,
    parse_qualitative_signals_response,
)
from src.domain.models.qualitative_signals import (
    QualitativeSignalSet,
    UncertaintySignal,
    ReasoningSignal,
    EmotionalSignal,
    ContradictionSignal,
    KnowledgeCeilingSignal,
    ConceptDepthSignal,
    UncertaintyType,
    ReasoningQuality,
    EmotionalIntensity,
)

log = structlog.get_logger(__name__)


class QualitativeSignalExtractor:
    """
    Extract qualitative signals from conversation history using LLM.

    This class provides Layer 3 of the signal architecture, using LLM
    semantic understanding to extract signals that are difficult or
    impossible to detect with rule-based heuristics alone.

    Design principles:
    - Graceful degradation: Return partial signals on parsing errors
    - Cost-conscious: Use light LLM client, limit context window
    - Cache-aware: Extract once per turn, consume multiple times
    - Debuggable: Include reasoning and confidence for all signals

    Usage:
        extractor = QualitativeSignalExtractor()
        signals = await extractor.extract(
            conversation_history=history,
            turn_number=5
        )
        # Use signals in scorers
        if signals.knowledge_ceiling?.is_terminal:
            # Avoid deepen strategies
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        enabled_signals: Optional[List[str]] = None,
    ):
        """
        Initialize qualitative signal extractor.

        Args:
            llm_client: LLM client (uses light client if None)
            enabled_signals: List of signal types to extract.
                If None, extracts all signals.
                Options: "uncertainty", "reasoning", "emotional",
                        "contradiction", "knowledge_ceiling", "concept_depth"
        """
        self.llm = llm_client or get_scoring_llm_client()
        self.enabled_signals = set(enabled_signals) if enabled_signals else None

        log.info(
            "qualitative_signal_extractor_initialized",
            llm_model=self.llm.model if hasattr(self.llm, "model") else "unknown",  # type: ignore[attr-defined]
            enabled_signals=enabled_signals,
        )

    async def extract(
        self,
        conversation_history: List[Dict[str, str]],
        turn_number: int,
    ) -> QualitativeSignalSet:
        """
        Extract qualitative signals from conversation history.

        Args:
            conversation_history: Recent conversation turns.
                Each dict should have "speaker"/"role" and "text" keys.
            turn_number: Current turn number (for context)

        Returns:
            QualitativeSignalSet with extracted signals.
            Signals that couldn't be extracted will be None.

        Raises:
            No exceptions raised. Returns empty signal set on LLM errors.
        """
        start_time = time.perf_counter()
        log.debug(
            "qualitative_signal_extraction_started",
            turn_number=turn_number,
            history_length=len(conversation_history),
        )

        # Fast path: insufficient history
        if len(conversation_history) < 2:
            log.debug(
                "insufficient_history_for_signals",
                history_length=len(conversation_history),
            )
            return QualitativeSignalSet(
                turn_number=turn_number,
                extraction_latency_ms=0,
            )

        # Call LLM for signal extraction
        try:
            raw_signals = await self._extract_via_llm(
                conversation_history=conversation_history,
                turn_number=turn_number,
            )
        except Exception as e:
            log.error(
                "qualitative_signal_extraction_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return QualitativeSignalSet(
                turn_number=turn_number,
                extraction_latency_ms=int((time.perf_counter() - start_time) * 1000),
                extraction_errors=[str(e)],
            )

        # Parse raw signals into domain models
        signal_set = self._parse_signals(raw_signals, turn_number)
        signal_set.extraction_latency_ms = int(
            (time.perf_counter() - start_time) * 1000
        )
        signal_set.llm_model = getattr(self.llm, "model", "unknown")

        log.info(
            "qualitative_signal_extraction_complete",
            turn_number=turn_number,
            latency_ms=signal_set.extraction_latency_ms,
            signals_extracted=sum(
                1
                for s in [
                    signal_set.uncertainty,
                    signal_set.reasoning,
                    signal_set.emotional,
                    signal_set.contradiction,
                    signal_set.knowledge_ceiling,
                    signal_set.concept_depth,
                ]
                if s is not None
            ),
        )

        return signal_set

    async def _extract_via_llm(
        self,
        conversation_history: List[Dict[str, str]],
        turn_number: int,
    ) -> Dict[str, Any]:
        """
        Call LLM for signal extraction.

        Args:
            conversation_history: Conversation turns
            turn_number: Current turn

        Returns:
            Parsed signal dictionary

        Raises:
            ValueError: If LLM response is invalid
        """
        system_prompt = get_qualitative_signals_system_prompt()
        user_prompt = get_qualitative_signals_user_prompt(
            conversation_history=conversation_history,
            turn_count=turn_number,
        )

        response: LLMResponse = await self.llm.complete(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.2,  # Lower temperature for consistent classification
            max_tokens=1500,  # Sufficient for structured JSON output
        )

        return parse_qualitative_signals_response(response.content)

    def _parse_signals(
        self,
        raw: Dict[str, Any],
        turn_number: int,
    ) -> QualitativeSignalSet:
        """
        Parse raw LLM output into QualitativeSignalSet.

        Args:
            raw: Raw signal dictionary from LLM
            turn_number: Current turn number

        Returns:
            QualitativeSignalSet with parsed signals
        """
        signal_set = QualitativeSignalSet(turn_number=turn_number)

        # Parse each signal type, continuing on individual failures
        try:
            if "uncertainty_signal" in raw and raw["uncertainty_signal"]:
                signal_set.uncertainty = self._parse_uncertainty_signal(
                    raw["uncertainty_signal"]
                )
        except Exception as e:
            log.warning("uncertainty_signal_parse_error", error=str(e))
            signal_set.extraction_errors.append(f"uncertainty: {e}")

        try:
            if "reasoning_signal" in raw and raw["reasoning_signal"]:
                signal_set.reasoning = self._parse_reasoning_signal(
                    raw["reasoning_signal"]
                )
        except Exception as e:
            log.warning("reasoning_signal_parse_error", error=str(e))
            signal_set.extraction_errors.append(f"reasoning: {e}")

        try:
            if "emotional_signal" in raw and raw["emotional_signal"]:
                signal_set.emotional = self._parse_emotional_signal(
                    raw["emotional_signal"]
                )
        except Exception as e:
            log.warning("emotional_signal_parse_error", error=str(e))
            signal_set.extraction_errors.append(f"emotional: {e}")

        try:
            if "contradiction_signal" in raw and raw["contradiction_signal"]:
                signal_set.contradiction = self._parse_contradiction_signal(
                    raw["contradiction_signal"]
                )
        except Exception as e:
            log.warning("contradiction_signal_parse_error", error=str(e))
            signal_set.extraction_errors.append(f"contradiction: {e}")

        try:
            if "knowledge_ceiling_signal" in raw and raw["knowledge_ceiling_signal"]:
                signal_set.knowledge_ceiling = self._parse_knowledge_ceiling_signal(
                    raw["knowledge_ceiling_signal"]
                )
        except Exception as e:
            log.warning("knowledge_ceiling_signal_parse_error", error=str(e))
            signal_set.extraction_errors.append(f"knowledge_ceiling: {e}")

        try:
            if "concept_depth_signal" in raw and raw["concept_depth_signal"]:
                signal_set.concept_depth = self._parse_concept_depth_signal(
                    raw["concept_depth_signal"]
                )
        except Exception as e:
            log.warning("concept_depth_signal_parse_error", error=str(e))
            signal_set.extraction_errors.append(f"concept_depth: {e}")

        return signal_set

    def _parse_uncertainty_signal(self, raw: Dict[str, Any]) -> UncertaintySignal:
        """Parse uncertainty signal from raw dict."""
        return UncertaintySignal(
            uncertainty_type=UncertaintyType(raw["uncertainty_type"]),
            confidence=float(raw.get("confidence", 0.7)),
            severity=float(raw.get("severity", 0.5)),
            examples=raw.get("examples", []),
            reasoning=raw.get("reasoning", ""),
        )

    def _parse_reasoning_signal(self, raw: Dict[str, Any]) -> ReasoningSignal:
        """Parse reasoning signal from raw dict."""
        return ReasoningSignal(
            reasoning_quality=ReasoningQuality(raw["reasoning_quality"]),
            confidence=float(raw.get("confidence", 0.7)),
            depth_score=float(raw.get("depth_score", 0.5)),
            has_examples=bool(raw.get("has_examples", False)),
            has_abstractions=bool(raw.get("has_abstractions", False)),
            examples=raw.get("examples", []),
            reasoning=raw.get("reasoning", ""),
        )

    def _parse_emotional_signal(self, raw: Dict[str, Any]) -> EmotionalSignal:
        """Parse emotional signal from raw dict."""
        return EmotionalSignal(
            intensity=EmotionalIntensity(raw["intensity"]),
            confidence=float(raw.get("confidence", 0.7)),
            trajectory=raw.get("trajectory", "stable"),
            markers=raw.get("markers", []),
            reasoning=raw.get("reasoning", ""),
        )

    def _parse_contradiction_signal(self, raw: Dict[str, Any]) -> ContradictionSignal:
        """Parse contradiction signal from raw dict."""
        return ContradictionSignal(
            has_contradiction=bool(raw.get("has_contradiction", False)),
            contradiction_type=raw.get("contradiction_type"),
            earlier_statement=raw.get("earlier_statement", ""),
            current_statement=raw.get("current_statement", ""),
            confidence=float(raw.get("confidence", 0.7)),
            reasoning=raw.get("reasoning", ""),
        )

    def _parse_knowledge_ceiling_signal(
        self, raw: Dict[str, Any]
    ) -> KnowledgeCeilingSignal:
        """Parse knowledge ceiling signal from raw dict."""
        return KnowledgeCeilingSignal(
            is_terminal=bool(raw.get("is_terminal", False)),
            response_type=raw.get("response_type", "unknown"),
            has_curiosity=bool(raw.get("has_curiosity", False)),
            redirection_available=bool(raw.get("redirection_available", False)),
            confidence=float(raw.get("confidence", 0.7)),
            reasoning=raw.get("reasoning", ""),
        )

    def _parse_concept_depth_signal(self, raw: Dict[str, Any]) -> ConceptDepthSignal:
        """Parse concept depth signal from raw dict."""
        return ConceptDepthSignal(
            abstraction_level=float(raw.get("abstraction_level", 0.5)),
            has_concrete_examples=bool(raw.get("has_concrete_examples", False)),
            has_abstract_principles=bool(raw.get("has_abstract_principles", False)),
            suggestion=raw.get("suggestion", "stay"),
            confidence=float(raw.get("confidence", 0.7)),
            reasoning=raw.get("reasoning", ""),
        )


__all__ = ["QualitativeSignalExtractor"]
