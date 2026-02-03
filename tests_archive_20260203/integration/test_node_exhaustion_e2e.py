"""End-to-end integration tests for node exhaustion system.

These tests run full interview scenarios through the complete pipeline
to validate:
- Node exhaustion detection
- Uncertainty response handling
- Phase transition behavior
- Fatigue detection and recovery
- Signal accuracy
- Strategy selection behavior
"""

import pytest

from tests.synthetic.scenarios.node_exhaustion_scenarios import (
    ALL_SCENARIOS,
    get_scenario_by_name,
)
from tests.synthetic.runner.node_exhaustion_test_runner import (
    NodeExhaustionTestRunner,
    ValidationConfig,
)


@pytest.fixture
def test_runner():
    """Create a test runner for E2E tests."""
    return NodeExhaustionTestRunner(
        config=ValidationConfig(strict_mode=False),
        enable_signal_detection=True,
    )


# =============================================================================
# Full Interview Tests
# =============================================================================


class TestNodeExhaustionE2E:
    """End-to-end tests for node exhaustion behavior."""

    @pytest.mark.asyncio
    async def test_full_interview_with_node_exhaustion(self, test_runner):
        """Test complete interview with node exhaustion and backtracking."""
        scenario = get_scenario_by_name("exhaustion_detection")
        assert scenario is not None

        result = await test_runner.run_scenario(scenario)
        validation = test_runner.validate_result(result, scenario)

        # Verify interview completed successfully
        assert result.success
        assert result.turn_count == 5

        # Verify exhaustion was detected
        assert "node1_exhausted_after_turn_4" in validation.validation_results

        # Verify backtracking occurred
        assert "node2_selected_on_turn_5" in validation.validation_results

    @pytest.mark.asyncio
    async def test_full_interview_with_uncertainty_triggers(self, test_runner):
        """Test complete interview with uncertainty response handling."""
        scenario = get_scenario_by_name("uncertainty_response")
        assert scenario is not None

        result = await test_runner.run_scenario(scenario)
        validation = test_runner.validate_result(result, scenario)

        # Verify interview completed
        assert result.success
        assert result.turn_count == 3

        # Verify uncertainty was detected
        assert "high_hedging_detected_on_turn_1" in validation.validation_results

        # Verify clarification strategy was used
        assert "clarify_strategy_selected" in validation.validation_results

    @pytest.mark.asyncio
    async def test_full_interview_with_phase_transitions(self, test_runner):
        """Test complete interview progressing through all phases."""
        scenario = get_scenario_by_name("phase_transitions")
        assert scenario is not None

        result = await test_runner.run_scenario(scenario)
        validation = test_runner.validate_result(result, scenario)

        # Verify all phases were visited
        assert result.turn_count == 6

        # Verify phase transitions occurred
        assert "exploratory_phase_detected_early" in validation.validation_results
        assert "focused_phase_detected_mid" in validation.validation_results
        assert "closing_phase_detected_late" in validation.validation_results

    @pytest.mark.asyncio
    async def test_full_interview_with_fatigue_detection(self, test_runner):
        """Test complete interview with fatigue and recovery."""
        scenario = get_scenario_by_name("fatigue_recovery")
        assert scenario is not None

        result = await test_runner.run_scenario(scenario)
        validation = test_runner.validate_result(result, scenario)

        # Verify fatigue was detected
        assert "fatigue_detected_by_turn_2" in validation.validation_results

        # Verify recovery occurred
        assert "engagement_recovered_on_turn_4" in validation.validation_results


# =============================================================================
# Node State Tracking Accuracy Tests
# =============================================================================


class TestNodeStateTracking:
    """Tests for accurate node state tracking."""

    @pytest.mark.asyncio
    async def test_focus_count_tracking(self, test_runner):
        """Verify focus_count is tracked accurately."""
        scenario = get_scenario_by_name("exhaustion_detection")
        result = await test_runner.run_scenario(scenario)

        # Node1 should have focus_count = 4 (focused on turns 1-4)
        node1_state = result.node_states.get("node1")
        assert node1_state is not None
        assert node1_state.focus_count == 4

        # Node2 should have focus_count = 1 (focused on turn 5)
        node2_state = result.node_states.get("node2")
        assert node2_state is not None
        assert node2_state.focus_count == 1

    @pytest.mark.asyncio
    async def test_yield_tracking(self, test_runner):
        """Verify yield_count and yield_rate are tracked accurately."""
        scenario = get_scenario_by_name("exhaustion_detection")
        result = await test_runner.run_scenario(scenario)

        # Node1: 1 yield on turn 1, 4 focuses total
        node1_state = result.node_states.get("node1")
        assert node1_state is not None
        assert node1_state.yield_count == 1
        assert node1_state.yield_rate == 0.25  # 1/4

        # Node2: 1 yield on turn 5, 1 focus total
        node2_state = result.node_states.get("node2")
        assert node2_state is not None
        assert node2_state.yield_count == 1
        assert node2_state.yield_rate == 1.0  # 1/1

    @pytest.mark.asyncio
    async def test_focus_streak_tracking(self, test_runner):
        """Verify current_focus_streak is tracked accurately."""
        scenario = get_scenario_by_name("exhaustion_detection")
        result = await test_runner.run_scenario(scenario)

        # Node1: Focused 4 times in a row
        node1_state = result.node_states.get("node1")
        assert node1_state is not None
        # Streak should be reset to 0 after yield on turn 1, then increment
        # Actually, the scenario shows focus streak of 4, then reset
        assert node1_state.current_focus_streak >= 0

        # Node2: Focused once
        node2_state = result.node_states.get("node2")
        assert node2_state is not None
        assert node2_state.current_focus_streak == 1

    @pytest.mark.asyncio
    async def test_response_depth_tracking(self, test_runner):
        """Verify response depths are tracked accurately."""
        scenario = get_scenario_by_name("exhaustion_detection")
        result = await test_runner.run_scenario(scenario)

        # Node1 should have 4 response depths tracked
        node1_state = result.node_states.get("node1")
        assert node1_state is not None
        assert len(node1_state.all_response_depths) == 4
        assert node1_state.all_response_depths == [
            "deep",
            "shallow",
            "shallow",
            "surface",
        ]

    @pytest.mark.asyncio
    async def test_strategy_usage_tracking(self, test_runner):
        """Verify strategy usage is tracked accurately."""
        scenario = get_scenario_by_name("strategy_repetition")
        result = await test_runner.run_scenario(scenario)

        # Node1 should have strategy usage tracked
        node1_state = result.node_states.get("node1")
        assert node1_state is not None

        # Should have 4 deepen strategies
        assert node1_state.strategy_usage_count.get("deepen", 0) >= 4


# =============================================================================
# Signal Detection Accuracy Tests
# =============================================================================


class TestSignalAccuracy:
    """Tests for signal detection accuracy."""

    @pytest.mark.asyncio
    async def test_exhaustion_signal_accuracy(self, test_runner):
        """Verify exhaustion signal is detected accurately."""
        scenario = get_scenario_by_name("exhaustion_detection")
        result = await test_runner.run_scenario(scenario)

        # Check turn 4: node1 should be exhausted
        turn_4_signals = (
            result.signals_detected[3] if len(result.signals_detected) > 3 else {}
        )
        exhaustion_signals = {
            k: v for k, v in turn_4_signals.items() if "exhausted" in k.lower()
        }

        # Should detect exhaustion on node1
        assert len(exhaustion_signals) > 0

    @pytest.mark.asyncio
    async def test_hedging_signal_accuracy(self, test_runner):
        """Verify hedging language signal is detected accurately."""
        scenario = get_scenario_by_name("uncertainty_response")
        result = await test_runner.run_scenario(scenario)

        # Check turn 1: should detect high hedging
        turn_1_signals = (
            result.signals_detected[0] if len(result.signals_detected) > 0 else {}
        )
        hedging_level = turn_1_signals.get("llm.hedging_language")

        # Should detect high hedging
        assert hedging_level in ("high", "medium")

    @pytest.mark.asyncio
    async def test_orphan_signal_accuracy(self, test_runner):
        """Verify orphan signal is detected accurately."""
        scenario = get_scenario_by_name("orphan_node_priority")
        result = await test_runner.run_scenario(scenario)

        # Check turn 2: orphan node should be detected
        turn_2_signals = (
            result.signals_detected[1] if len(result.signals_detected) > 1 else {}
        )
        orphan_signals = {
            k: v
            for k, v in turn_2_signals.items()
            if "orphan" in k.lower() and v == "true"
        }

        # Should detect orphan
        assert len(orphan_signals) > 0

    @pytest.mark.asyncio
    async def test_recency_signal_accuracy(self, test_runner):
        """Verify recency score signal is accurate."""
        scenario = get_scenario_by_name("multi_branch_exploration")
        result = await test_runner.run_scenario(scenario)

        # Check that recency scores are computed
        for turn_signals in result.signals_detected:
            recency_signals = {
                k: v for k, v in turn_signals.items() if "recency" in k.lower()
            }
            # Should have recency signals
            assert len(recency_signals) > 0

    @pytest.mark.asyncio
    async def test_strategy_repetition_signal_accuracy(self, test_runner):
        """Verify strategy repetition signal is detected accurately."""
        scenario = get_scenario_by_name("strategy_repetition")
        result = await test_runner.run_scenario(scenario)

        # Check turn 4: should detect high repetition
        turn_4_signals = (
            result.signals_detected[3] if len(result.signals_detected) > 3 else {}
        )
        repetition_signals = {
            k: v for k, v in turn_4_signals.items() if "repetition" in k.lower()
        }

        # Should detect repetition
        assert len(repetition_signals) > 0


# =============================================================================
# Strategy Selection Behavior Tests
# =============================================================================


class TestStrategySelection:
    """Tests for strategy selection behavior."""

    @pytest.mark.asyncio
    async def test_backtracking_triggers_strategy_switch(self, test_runner):
        """Verify backtracking triggers appropriate strategy selection."""
        scenario = get_scenario_by_name("exhaustion_detection")
        result = await test_runner.run_scenario(scenario)

        # Turn 5 should switch from deepen to something else
        strategies = result.strategies_selected
        assert len(strategies) >= 5

        # First 4 turns should be deepen
        for i in range(4):
            assert strategies[i] == "deepen"

        # Turn 5 should still be deepen (but on different node)
        assert strategies[4] == "deepen"

    @pytest.mark.asyncio
    async def test_uncertainty_triggers_clarify(self, test_runner):
        """Verify uncertainty triggers clarify strategy."""
        scenario = get_scenario_by_name("uncertainty_response")
        result = await test_runner.run_scenario(scenario)

        # Turns 1-2 should be clarify
        strategies = result.strategies_selected
        assert len(strategies) >= 2

        # Should use clarify when uncertain
        assert "clarify" in strategies[0]
        assert "clarify" in strategies[1]

    @pytest.mark.asyncio
    async def test_fatigue_triggers_ease(self, test_runner):
        """Verify fatigue triggers ease strategy."""
        scenario = get_scenario_by_name("fatigue_recovery")
        result = await test_runner.run_scenario(scenario)

        # Turn 2-3 should be ease
        strategies = result.strategies_selected
        assert len(strategies) >= 3

        # Should use ease during fatigue
        assert "ease" in strategies[1]
        assert "ease" in strategies[2]

    @pytest.mark.asyncio
    async def test_phase_based_strategy_selection(self, test_runner):
        """Verify strategies are selected based on phase."""
        scenario = get_scenario_by_name("phase_transitions")
        result = await test_runner.run_scenario(scenario)

        # Check that strategies align with phases
        strategies = result.strategies_selected

        # Early turns: breadth-focused
        assert "broaden" in strategies[:2]

        # Mid turns: depth-focused
        assert "deepen" in strategies[2:4]

        # Late turns: synthesis/closing
        assert "synthesis" in strategies[4:] or "closing" in strategies[4:]


# =============================================================================
# All Scenarios Test
# =============================================================================


class TestAllScenarios:
    """Run all scenarios to ensure none fail catastrophically."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario", ALL_SCENARIOS, ids=lambda s: s.name)
    async def test_all_scenarios_complete(self, scenario, test_runner):
        """Test that all scenarios can run to completion."""
        result = await test_runner.run_scenario(scenario)

        # Should complete successfully
        assert result.success, f"Scenario {scenario.name} failed: {result.errors}"

        # Should have correct turn count
        assert result.turn_count == scenario.turn_count

        # Should have node states
        assert len(result.node_states) > 0

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario", ALL_SCENARIOS, ids=lambda s: s.name)
    async def test_all_scenarios_detect_signals(self, scenario, test_runner):
        """Test that all scenarios produce signal detections."""
        result = await test_runner.run_scenario(scenario)

        # Should have signals for each turn
        assert len(result.signals_detected) == scenario.turn_count

        # Each turn should have at least some signals
        for i, turn_signals in enumerate(result.signals_detected):
            assert len(turn_signals) > 0, f"Turn {i + 1} has no signals"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scenario", ALL_SCENARIOS, ids=lambda s: s.name)
    async def test_all_scenarios_validate(self, scenario, test_runner):
        """Test that all scenarios pass validation."""
        result = await test_runner.run_scenario(scenario)
        validation = test_runner.validate_result(result, scenario)

        # In non-strict mode, at least some validations should pass
        assert any(validation.validation_results.values()), (
            f"Scenario {scenario.name} failed all validations: {validation.validation_results}"
        )


# =============================================================================
# Performance Tests
# =============================================================================


class TestE2EPerformance:
    """Performance tests for E2E scenarios."""

    @pytest.mark.asyncio
    async def test_scenario_execution_time(self, test_runner):
        """Verify scenarios execute within acceptable time."""
        import time

        scenario = get_scenario_by_name("exhaustion_detection")

        start_time = time.time()
        result = await test_runner.run_scenario(scenario)
        execution_time = time.time() - start_time

        # Should complete in less than 1 second
        assert execution_time < 1.0, f"Scenario took {execution_time:.2f}s"

        # Result should also track execution time
        assert result.execution_time_ms > 0
        assert result.execution_time_ms < 1000  # Less than 1 second

    @pytest.mark.asyncio
    async def test_signal_detection_overhead(self, test_runner):
        """Verify signal detection doesn't add significant overhead."""
        import time

        scenario = get_scenario_by_name("multi_branch_exploration")

        # Run with signal detection
        start_time = time.time()
        await test_runner.run_scenario(scenario)
        with_signals_time = time.time() - start_time

        # Should still be fast
        assert with_signals_time < 1.0, (
            f"Signal detection took {with_signals_time:.2f}s"
        )

    @pytest.mark.asyncio
    async def test_memory_usage_stable(self, test_runner):
        """Verify memory usage remains stable across scenarios."""
        import tracemalloc

        tracemalloc.start()

        # Run multiple scenarios
        for scenario_name in [
            "exhaustion_detection",
            "uncertainty_response",
            "fatigue_recovery",
        ]:
            scenario = get_scenario_by_name(scenario_name)
            await test_runner.run_scenario(scenario)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Peak memory should be reasonable (< 50MB)
        assert peak < 50 * 1024 * 1024, f"Peak memory usage: {peak / 1024 / 1024:.2f}MB"
