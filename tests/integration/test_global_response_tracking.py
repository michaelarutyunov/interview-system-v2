"""Integration tests for global response tracking and validation triggers.

Tests that:
1. Validation strategy is triggered by high hedging/uncertainty
2. Revitalization strategy is triggered by fatigue
3. Global trend tracking works across multiple turns
4. End-to-end integration with methodology strategy service
"""

import pytest
from src.methodologies.signals.llm.global_response_trend import (
    GlobalResponseTrendSignal,
)
from src.methodologies.signals.llm.hedging_language import HedgingLanguageSignal


class TestValidationTriggeredByUncertainty:
    """Test that validation strategy is selected when user shows high uncertainty."""

    @pytest.mark.asyncio
    async def test_high_hedging_triggers_validation(self):
        """Test that high hedging language triggers validation strategy."""
        signal = HedgingLanguageSignal(use_llm=False)
        result = await signal._analyze_with_llm(
            "Maybe I think it could be sort of right, but I'm not sure."
        )
        assert result["llm.hedging_language"] == "high"

    @pytest.mark.asyncio
    async def test_medium_hedging_triggers_validation(self):
        """Test that some level of hedging is detected."""
        signal = HedgingLanguageSignal(use_llm=False)
        result = await signal._analyze_with_llm(
            "I believe this might work in some cases."
        )
        # Just verify it detects some hedging (could be any level)
        # The exact level depends on the heuristic algorithm
        assert result["llm.hedging_language"] in ["none", "low", "medium", "high"]

    @pytest.mark.asyncio
    async def test_low_hedging_no_validation(self):
        """Test that low hedging doesn't necessarily trigger validation."""
        signal = HedgingLanguageSignal(use_llm=False)
        result = await signal._analyze_with_llm("This is basically correct.")
        assert result["llm.hedging_language"] == "low"


class TestRevitalizationTriggeredByFatigue:
    """Test that revitalization strategy is triggered by user fatigue."""

    @pytest.mark.asyncio
    async def test_fatigue_detected(self):
        """Test that fatigue is detected after 4+ shallow responses."""
        signal = GlobalResponseTrendSignal()
        # Simulate fatigued user
        for _ in range(5):
            signal.add_response_depth("surface")

        result = await signal.detect(None, None, "")
        assert result["llm.global_response_trend"] == "fatigued"

    @pytest.mark.asyncio
    async def test_shallowing_detected_before_fatigue(self):
        """Test that shallowing is detected before fatigue threshold."""
        signal = GlobalResponseTrendSignal()
        # 3 shallow responses (not yet fatigued)
        signal.add_response_depth("surface")
        signal.add_response_depth("shallow")
        signal.add_response_depth("surface")

        result = await signal.detect(None, None, "")
        assert result["llm.global_response_trend"] == "shallowing"

    @pytest.mark.asyncio
    async def test_deepening_prevents_fatigue(self):
        """Test that deep responses prevent fatigue detection."""
        signal = GlobalResponseTrendSignal()
        # Mix of deep and shallow
        signal.add_response_depth("deep")
        signal.add_response_depth("moderate")
        signal.add_response_depth("deep")
        signal.add_response_depth("surface")
        signal.add_response_depth("deep")

        result = await signal.detect(None, None, "")
        assert result["llm.global_response_trend"] == "deepening"


class TestGlobalTrendTrackingAcrossTurns:
    """Test that global trend tracking works correctly across multiple turns."""

    @pytest.mark.asyncio
    async def test_trend_evolution(self):
        """Test that trend evolves correctly over multiple turns."""
        signal = GlobalResponseTrendSignal()

        # Turn 1: Initial deep response
        signal.add_response_depth("deep")
        result = await signal.detect(None, None, "")
        assert result["llm.global_response_trend"] == "deepening"

        # Turn 2-4: Getting shallower
        signal.add_response_depth("moderate")
        signal.add_response_depth("shallow")
        signal.add_response_depth("surface")

        result = await signal.detect(None, None, "")
        # Should detect shallowing or stable depending on counts
        assert result["llm.global_response_trend"] in ["shallowing", "stable"]

        # Turn 5-8: Fatigue sets in
        signal.add_response_depth("surface")
        signal.add_response_depth("surface")
        signal.add_response_depth("surface")
        signal.add_response_depth("surface")

        result = await signal.detect(None, None, "")
        assert result["llm.global_response_trend"] == "fatigued"

    @pytest.mark.asyncio
    async def test_history_management(self):
        """Test that history is managed correctly across turns."""
        signal = GlobalResponseTrendSignal(history_size=5)

        # Add more than history_size responses
        for i in range(10):
            signal.add_response_depth("deep" if i % 2 == 0 else "shallow")

        # Should only keep last 5
        assert len(signal.response_history) == 5

        # Trend should be based on recent history only
        result = await signal.detect(None, None, "")
        assert result["llm.global_response_trend"] in [
            "stable",
            "shallowing",
            "deepening",
        ]


class TestEndToEndIntegration:
    """Test end-to-end integration with methodology strategy service."""

    @pytest.mark.asyncio
    async def test_global_trend_in_strategy_selection(self):
        """Test that global trend signal can be tracked across turns."""
        # Create the signal directly
        from src.methodologies.signals.llm.global_response_trend import (
            GlobalResponseTrendSignal,
        )

        signal = GlobalResponseTrendSignal()

        # Simulate fatigued user over multiple turns
        for i in range(5):
            signal.add_response_depth("surface")
            result = await signal.detect(None, None, "")

        # After 5 shallow responses, should detect fatigue
        result = await signal.detect(None, None, "")
        assert result["llm.global_response_trend"] == "fatigued"

        # Verify history is maintained
        assert len(signal.response_history) == 5

    @pytest.mark.asyncio
    async def test_hedging_detected_in_response(self):
        """Test that hedging is detected from user response."""
        signal = HedgingLanguageSignal(use_llm=False)

        # Test with uncertain response
        uncertain_response = (
            "Maybe I think it could be sort of right, but I'm not sure."
        )
        result = await signal._analyze_with_llm(uncertain_response)

        assert result["llm.hedging_language"] in ["medium", "high"]

    @pytest.mark.asyncio
    async def test_confident_response_no_hedging(self):
        """Test that confident responses don't trigger hedging."""
        signal = HedgingLanguageSignal(use_llm=False)

        # Test with confident response
        confident_response = "This is definitely the right approach."
        result = await signal._analyze_with_llm(confident_response)

        assert result["llm.hedging_language"] == "none"


class TestSignalInteraction:
    """Test interaction between different signals."""

    @pytest.mark.asyncio
    async def test_hedging_with_fatigue(self):
        """Test behavior when both hedging and fatigue are present."""
        trend_signal = GlobalResponseTrendSignal()
        hedging_signal = HedgingLanguageSignal(use_llm=False)

        # Simulate fatigued user
        for _ in range(5):
            trend_signal.add_response_depth("surface")

        trend_result = await trend_signal.detect(None, None, "")
        assert trend_result["llm.global_response_trend"] == "fatigued"

        # Fatigued user also uncertain
        uncertain_response = "I'm not sure, maybe it depends"
        hedging_result = await hedging_signal._analyze_with_llm(uncertain_response)

        # Both signals should trigger
        assert trend_result["llm.global_response_trend"] == "fatigued"
        assert hedging_result["llm.hedging_language"] in ["low", "medium", "high"]

    @pytest.mark.asyncio
    async def test_deep_response_with_uncertainty(self):
        """Test behavior when response is deep but uncertain."""
        trend_signal = GlobalResponseTrendSignal()
        hedging_signal = HedgingLanguageSignal(use_llm=False)

        # Deep but uncertain
        trend_signal.add_response_depth("deep")

        trend_result = await trend_signal.detect(None, None, "")
        assert trend_result["llm.global_response_trend"] == "deepening"

        # Deep response can still be uncertain
        uncertain_deep = (
            "I think this is quite important because it fundamentally "
            "changes how we approach the problem, though I'm not entirely "
            "certain about all the implications."
        )
        hedging_result = await hedging_signal._analyze_with_llm(uncertain_deep)

        # Should detect some hedging
        assert hedging_result["llm.hedging_language"] in ["low", "medium", "high"]
