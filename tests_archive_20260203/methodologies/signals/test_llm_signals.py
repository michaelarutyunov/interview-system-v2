"""Unit tests for LLM signals including global response tracking and hedging language."""

import pytest
from src.methodologies.signals.llm.global_response_trend import (
    GlobalResponseTrendSignal,
)
from src.methodologies.signals.llm.hedging_language import HedgingLanguageSignal


class TestGlobalResponseTrendSignal:
    """Test GlobalResponseTrendSignal detects response trends."""

    @pytest.mark.asyncio
    async def test_initial_state_is_stable(self):
        """Test that signal returns 'stable' when no history."""
        signal = GlobalResponseTrendSignal()
        result = await signal.detect(None, None, "")
        assert result["llm.global_response_trend"] == "stable"

    @pytest.mark.asyncio
    async def test_deepening_trend(self):
        """Test detection of deepening trend (more deep than shallow)."""
        signal = GlobalResponseTrendSignal()
        # Add 3 deep responses, 1 shallow
        signal.add_response_depth("deep")
        signal.add_response_depth("moderate")
        signal.add_response_depth("deep")
        signal.add_response_depth("shallow")

        result = await signal.detect(None, None, "")
        assert result["llm.global_response_trend"] == "deepening"

    @pytest.mark.asyncio
    async def test_shallowing_trend(self):
        """Test detection of shallowing trend (more shallow than deep)."""
        signal = GlobalResponseTrendSignal()
        # Add 3 shallow responses, 1 deep
        signal.add_response_depth("surface")
        signal.add_response_depth("shallow")
        signal.add_response_depth("surface")
        signal.add_response_depth("deep")

        result = await signal.detect(None, None, "")
        assert result["llm.global_response_trend"] == "shallowing"

    @pytest.mark.asyncio
    async def test_fatigued_trend(self):
        """Test detection of fatigue (4+ shallow responses)."""
        signal = GlobalResponseTrendSignal()
        # Add 4 shallow responses
        signal.add_response_depth("surface")
        signal.add_response_depth("shallow")
        signal.add_response_depth("surface")
        signal.add_response_depth("surface")

        result = await signal.detect(None, None, "")
        assert result["llm.global_response_trend"] == "fatigued"

    @pytest.mark.asyncio
    async def test_stable_trend(self):
        """Test stable trend (equal deep and shallow)."""
        signal = GlobalResponseTrendSignal()
        # Add 2 deep, 2 shallow
        signal.add_response_depth("deep")
        signal.add_response_depth("surface")
        signal.add_response_depth("moderate")
        signal.add_response_depth("shallow")

        result = await signal.detect(None, None, "")
        assert result["llm.global_response_trend"] == "stable"

    def test_history_trimming(self):
        """Test that history is trimmed to history_size."""
        signal = GlobalResponseTrendSignal(history_size=5)
        # Add 10 responses
        for i in range(10):
            signal.add_response_depth("deep" if i % 2 == 0 else "shallow")

        assert len(signal.response_history) == 5
        # Should only keep last 5
        assert signal.response_history == [
            "shallow",
            "deep",
            "shallow",
            "deep",
            "shallow",
        ]

    def test_clear_history(self):
        """Test clearing history."""
        signal = GlobalResponseTrendSignal()
        signal.add_response_depth("deep")
        signal.add_response_depth("shallow")

        signal.clear_history()
        assert len(signal.response_history) == 0

    @pytest.mark.asyncio
    async def test_detect_with_current_depth(self):
        """Test that detect can add current_depth to history."""
        signal = GlobalResponseTrendSignal()
        signal.add_response_depth("deep")
        signal.add_response_depth("shallow")

        result = await signal.detect(None, None, "", current_depth="deep")
        assert result["llm.global_response_trend"] == "deepening"  # 2 deep, 1 shallow
        assert len(signal.response_history) == 3


class TestHedgingLanguageSignal:
    """Test HedgingLanguageSignal detects uncertainty."""

    @pytest.mark.asyncio
    async def test_no_hedging(self):
        """Test detection of confident statements (no hedging)."""
        signal = HedgingLanguageSignal(use_llm=False)
        result = await signal._analyze_with_llm("I am certain this is correct.")
        assert result["llm.hedging_language"] == "none"

    @pytest.mark.asyncio
    async def test_low_hedging(self):
        """Test detection of low hedging."""
        signal = HedgingLanguageSignal(use_llm=False)
        result = await signal._analyze_with_llm("This is basically the right approach.")
        assert result["llm.hedging_language"] == "low"

    @pytest.mark.asyncio
    async def test_medium_hedging(self):
        """Test detection of medium hedging."""
        signal = HedgingLanguageSignal(use_llm=False)
        result = await signal._analyze_with_llm(
            "I believe this might work, and typically it does."
        )
        assert result["llm.hedging_language"] == "medium"

    @pytest.mark.asyncio
    async def test_high_hedging(self):
        """Test detection of high hedging."""
        signal = HedgingLanguageSignal(use_llm=False)
        result = await signal._analyze_with_llm(
            "I guess maybe it could be sort of right, but I'm not sure."
        )
        assert result["llm.hedging_language"] == "high"

    @pytest.mark.asyncio
    async def test_multiple_hedging_patterns(self):
        """Test detection with multiple hedging patterns."""
        signal = HedgingLanguageSignal(use_llm=False)
        text = "Maybe I think it's kind of possible, but I'm not certain."
        result = await signal._analyze_with_llm(text)
        assert result["llm.hedging_language"] in ["medium", "high"]

    @pytest.mark.asyncio
    async def test_uncertainty_phrases(self):
        """Test detection of uncertainty phrases."""
        signal = HedgingLanguageSignal(use_llm=False)
        result = await signal._analyze_with_llm(
            "It depends on various factors and might be the case."
        )
        assert result["llm.hedging_language"] in ["low", "medium", "high"]

    @pytest.mark.asyncio
    async def test_case_insensitive(self):
        """Test that pattern matching is case-insensitive."""
        signal = HedgingLanguageSignal(use_llm=False)
        result1 = await signal._analyze_with_llm("Maybe this works")
        result2 = await signal._analyze_with_llm("MAYBE this works")
        result3 = await signal._analyze_with_llm("maybe this works")
        # All should detect the same level of hedging
        assert result1 == result2 == result3

    @pytest.mark.asyncio
    async def test_score_thresholds(self):
        """Test that score thresholds map correctly to levels."""
        signal = HedgingLanguageSignal(use_llm=False)

        # Test various scores
        # Score 0 = none
        # Score 1 = low
        # Score 2-3 = medium
        # Score 4+ = high

        # High hedging (4+ weighted score)
        result = await signal._analyze_with_llm(
            "Maybe I think maybe it could possibly be, I guess."
        )
        assert result["llm.hedging_language"] == "high"
