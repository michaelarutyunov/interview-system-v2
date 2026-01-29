"""Hedging language signal - detects uncertainty and tentative language.

This signal uses LLM analysis to detect:
- Hedging words: maybe, I think, sort of, kind of, I guess, probably
- Uncertain phrasing: not sure, it depends, might be, could be
- Tentative statements: qualifiers, hesitations

Levels: none / low / medium / high
"""

from src.methodologies.signals.llm.common import BaseLLMSignal
import re


class HedgingLanguageSignal(BaseLLMSignal):
    """Detect hedging, uncertainty, tentative language in responses.

    Namespaced signal: llm.hedging_language
    Cost: high (LLM analysis in production)
    Refresh: per_response (ALWAYS fresh)

    Hedging categories:
    - none: No hedging, confident statements
    - low: Minimal hedging, mostly confident
    - medium: Moderate hedging, some uncertainty
    - high: Significant hedging, very uncertain

    Production implementation: Uses LLM to analyze semantic hedging.
    Proof-of-concept: Uses regex-based heuristic pattern matching.
    """

    signal_name = "llm.hedging_language"

    # Hedging patterns for PoC implementation
    # TODO: Replace with LLM-based analysis in production
    HEDGING_PATTERNS = {
        "high": [
            r"\b(maybe|perhaps|possibly|i guess|i suppose|i think)\b",
            r"\b(not sure|not certain|don't know|uncertain|unsure)\b",
            r"\b(it depends|might be|could be|may be|somewhat)\b",
            r"\b(sort of|kind of|a little bit|more or less)\b",
            r"\b(probably|likely|possibly|presumably|ostensibly)\b",
        ],
        "medium": [
            r"\b(I believe|I feel|It seems|appears to be)\b",
            r"\b(generally|typically|usually|normally)\b",
            r"\b(somewhat|rather|quite|fairly)\b",
            r"\b(I'd say|I reckon|I imagine)\b",
        ],
        "low": [
            r"\b(basically|essentially|fundamentally)\b",
            r"\b(mostly|chiefly|primarily)\b",
        ],
    }

    def __init__(self, use_llm: bool = False):
        """Initialize signal.

        Args:
            use_llm: If True, use LLM for analysis (requires LLM infrastructure)
                   If False, use regex-based heuristic (PoC)
        """
        self.use_llm = use_llm

    async def _analyze_with_llm(self, response_text: str) -> dict:
        """Analyze response for hedging language.

        Args:
            response_text: User's response to analyze

        Returns:
            Dictionary with signal_name: hedging_level
        """
        if self.use_llm:
            return await self._llm_analysis(response_text)
        else:
            return self._heuristic_analysis(response_text)

    async def _llm_analysis(self, response_text: str) -> dict:
        """Use LLM to detect hedging/uncertainty.

        TODO: Implement LLM-based analysis when infrastructure is available.
        See bead: interview-system-v2-1xx

        LLM Prompt:
        Analyze this response for hedging and uncertainty:
        "{response_text}"
        Look for:
        - Hedging words: maybe, I think, sort of, kind of, I guess, probably
        - Uncertain phrasing: not sure, it depends, might be, could be
        - Tentative statements: qualifiers, hesitations
        Rate the level of hedging/uncertainty:
        - none: No hedging, confident statements
        - low: Minimal hedging, mostly confident
        - medium: Moderate hedging, some uncertainty
        - high: Significant hedging, very uncertain
        """
        # TODO: Implement LLM call when infrastructure is wired
        # For now, fall back to heuristic
        return self._heuristic_analysis(response_text)

    def _heuristic_analysis(self, response_text: str) -> dict:
        """Use regex-based heuristic to detect hedging (PoC).

        Args:
            response_text: User's response to analyze

        Returns:
            Dictionary with signal_name: hedging_level
        """
        text_lower = response_text.lower()

        # Count matches for each hedging level
        high_count = 0
        medium_count = 0
        low_count = 0

        for pattern in self.HEDGING_PATTERNS["high"]:
            high_count += len(re.findall(pattern, text_lower))

        for pattern in self.HEDGING_PATTERNS["medium"]:
            medium_count += len(re.findall(pattern, text_lower))

        for pattern in self.HEDGING_PATTERNS["low"]:
            low_count += len(re.findall(pattern, text_lower))

        # Determine hedging level based on weighted count
        # High patterns count most, low patterns count least
        score = (high_count * 3) + (medium_count * 2) + (low_count * 1)

        if score >= 4:
            level = "high"
        elif score >= 2:
            level = "medium"
        elif score >= 1:
            level = "low"
        else:
            level = "none"

        return {self.signal_name: level}
