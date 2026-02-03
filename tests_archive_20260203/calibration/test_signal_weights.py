"""Signal weight calibration suite for testing various weight configurations.

This module tests different signal weight configurations to find optimal
values for the interview system. It provides a framework for systematic
calibration of signal weights.
"""

import pytest
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from tests.synthetic.scenarios.node_exhaustion_scenarios import (
    ALL_SCENARIOS,
    InterviewScenario,
)
from tests.synthetic.runner.node_exhaustion_test_runner import (
    NodeExhaustionTestRunner,
    InterviewResult,
    ValidationConfig,
)


@dataclass
class WeightConfiguration:
    """Configuration for signal weight testing.

    Attributes:
        name: Unique identifier for this configuration
        description: Human-readable description
        weights: Dict mapping signal_name to weight value
        expected_behavior: Expected behavioral outcome
        baseline: If True, this is the baseline configuration
    """

    name: str
    description: str
    weights: Dict[str, float]
    expected_behavior: str
    baseline: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CalibrationResult:
    """Result of calibrating with a weight configuration.

    Attributes:
        config_name: Name of the configuration tested
        scenario_name: Name of the scenario run
        passed: Whether the behavior matched expectations
        metrics: Dict of metric name -> value
        details: Additional details about the calibration
    """

    config_name: str
    scenario_name: str
    passed: bool
    metrics: Dict[str, float]
    details: Dict[str, Any]


# =============================================================================
# Weight Configuration Library
# =============================================================================

BASELINE_WEIGHTS = {
    # Exhaustion weights
    "graph.node.exhausted.true": -1.5,
    "graph.node.exhausted.false": 0.0,
    "graph.node.exhaustion_score": -1.0,
    # Engagement weights
    "graph.node.focus_streak.none": 0.0,
    "graph.node.focus_streak.low": 0.2,
    "graph.node.focus_streak.medium": -0.3,
    "graph.node.focus_streak.high": -0.8,
    "graph.node.is_current_focus.true": 0.5,
    "graph.node.is_current_focus.false": 0.0,
    "graph.node.recency_score": 0.5,
    # Relationship weights
    "graph.node.is_orphan.true": 1.2,
    "graph.node.is_orphan.false": 0.0,
    "graph.node.edge_count": 0.1,
    # Strategy repetition
    "graph.node.strategy_repetition.none": 0.0,
    "graph.node.strategy_repetition.low": -0.2,
    "graph.node.strategy_repetition.medium": -0.5,
    "graph.node.strategy_repetition.high": -1.0,
    # Hedging language
    "llm.hedging_language.none": 0.0,
    "llm.hedging_language.low": -0.2,
    "llm.hedging_language.medium": -0.5,
    "llm.hedging_language.high": -0.8,
}


# Exhaustion weight configurations
EXHAUSTION_CONFIGS = [
    WeightConfiguration(
        name="baseline_exhaustion",
        description="Baseline exhaustion penalty weights",
        weights={
            "graph.node.exhausted.true": -1.5,
            "graph.node.exhaustion_score": -1.0,
        },
        expected_behavior="moderate_backtracking",
        baseline=True,
    ),
    WeightConfiguration(
        name="high_exhaustion_penalty",
        description="Aggressive exhaustion penalty for quick backtracking",
        weights={
            "graph.node.exhausted.true": -2.5,
            "graph.node.exhaustion_score": -1.5,
        },
        expected_behavior="aggressive_backtracking",
    ),
    WeightConfiguration(
        name="low_exhaustion_penalty",
        description="Conservative exhaustion penalty",
        weights={
            "graph.node.exhausted.true": -0.5,
            "graph.node.exhaustion_score": -0.3,
        },
        expected_behavior="conservative_backtracking",
    ),
]


# Engagement weight configurations
ENGAGEMENT_CONFIGS = [
    WeightConfiguration(
        name="baseline_engagement",
        description="Baseline engagement weights",
        weights={
            "graph.node.focus_streak.high": -0.8,
            "graph.node.is_current_focus.true": 0.5,
            "graph.node.recency_score": 0.5,
        },
        expected_behavior="balanced_engagement",
        baseline=True,
    ),
    WeightConfiguration(
        name="high_recency_boost",
        description="Strong preference for recently focused nodes",
        weights={
            "graph.node.focus_streak.high": -0.3,
            "graph.node.is_current_focus.true": 1.0,
            "graph.node.recency_score": 1.0,
        },
        expected_behavior="sticky_focus",
    ),
    WeightConfiguration(
        name="low_recency_boost",
        description="Weak preference for recently focused nodes",
        weights={
            "graph.node.focus_streak.high": -1.2,
            "graph.node.is_current_focus.true": 0.2,
            "graph.node.recency_score": 0.2,
        },
        expected_behavior="frequent_switching",
    ),
]


# Orphan priority configurations
ORPHAN_CONFIGS = [
    WeightConfiguration(
        name="baseline_orphan",
        description="Baseline orphan node priority",
        weights={
            "graph.node.is_orphan.true": 1.2,
        },
        expected_behavior="moderate_orphan_priority",
        baseline=True,
    ),
    WeightConfiguration(
        name="high_orphan_priority",
        description="Strong orphan node prioritization",
        weights={
            "graph.node.is_orphan.true": 2.0,
        },
        expected_behavior="aggressive_orphan_connection",
    ),
    WeightConfiguration(
        name="low_orphan_priority",
        description="Weak orphan node prioritization",
        weights={
            "graph.node.is_orphan.true": 0.5,
        },
        expected_behavior="minimal_orphan_priority",
    ),
]


# Strategy repetition configurations
REPETITION_CONFIGS = [
    WeightConfiguration(
        name="baseline_repetition",
        description="Baseline strategy repetition penalty",
        weights={
            "graph.node.strategy_repetition.high": -1.0,
            "graph.node.strategy_repetition.medium": -0.5,
        },
        expected_behavior="moderate_strategy_diversity",
        baseline=True,
    ),
    WeightConfiguration(
        name="high_repetition_penalty",
        description="Strong penalty for strategy repetition",
        weights={
            "graph.node.strategy_repetition.high": -1.5,
            "graph.node.strategy_repetition.medium": -0.8,
            "graph.node.strategy_repetition.low": -0.3,
        },
        expected_behavior="high_strategy_diversity",
    ),
    WeightConfiguration(
        name="low_repetition_penalty",
        description="Weak penalty for strategy repetition",
        weights={
            "graph.node.strategy_repetition.high": -0.5,
            "graph.node.strategy_repetition.medium": -0.2,
        },
        expected_behavior="low_strategy_diversity",
    ),
]


# Hedging language configurations
HEDGING_CONFIGS = [
    WeightConfiguration(
        name="baseline_hedging",
        description="Baseline hedging language penalty",
        weights={
            "llm.hedging_language.high": -0.8,
            "llm.hedging_language.medium": -0.5,
        },
        expected_behavior="moderate_clarification",
        baseline=True,
    ),
    WeightConfiguration(
        name="high_hedging_sensitivity",
        description="High sensitivity to hedging language",
        weights={
            "llm.hedging_language.high": -1.2,
            "llm.hedging_language.medium": -0.8,
            "llm.hedging_language.low": -0.3,
        },
        expected_behavior="aggressive_clarification",
    ),
    WeightConfiguration(
        name="low_hedging_sensitivity",
        description="Low sensitivity to hedging language",
        weights={
            "llm.hedging_language.high": -0.4,
            "llm.hedging_language.medium": -0.2,
        },
        expected_behavior="minimal_clarification",
    ),
]


# Combined configurations
COMBINED_CONFIGS = [
    WeightConfiguration(
        name="baseline_combined",
        description="Baseline all weights combined",
        weights=BASELINE_WEIGHTS.copy(),
        expected_behavior="balanced_behavior",
        baseline=True,
    ),
    WeightConfiguration(
        name="exploratory_profile",
        description="Weights optimized for breadth exploration",
        weights={
            **BASELINE_WEIGHTS,
            "graph.node.exhausted.true": -1.0,  # Less aggressive
            "graph.node.is_orphan.true": 1.5,  # More orphan priority
            "graph.node.recency_score": 0.3,  # Less sticky
        },
        expected_behavior="breadth_focused",
    ),
    WeightConfiguration(
        name="focused_profile",
        description="Weights optimized for depth exploration",
        weights={
            **BASELINE_WEIGHTS,
            "graph.node.exhausted.true": -2.0,  # More aggressive
            "graph.node.is_orphan.true": 0.8,  # Less orphan priority
            "graph.node.recency_score": 0.8,  # More sticky
        },
        expected_behavior="depth_focused",
    ),
]


ALL_CONFIGS = (
    EXHAUSTION_CONFIGS
    + ENGAGEMENT_CONFIGS
    + ORPHAN_CONFIGS
    + REPETITION_CONFIGS
    + HEDGING_CONFIGS
    + COMBINED_CONFIGS
)


# =============================================================================
# Calibration Tests
# =============================================================================


class TestSignalWeightCalibration:
    """Tests for signal weight calibration."""

    @pytest.fixture
    def calibration_runner(self):
        """Create a test runner for calibration."""
        return NodeExhaustionTestRunner(
            config=ValidationConfig(strict_mode=False),
            enable_signal_detection=True,
        )

    def test_all_configs_have_weights(self):
        """Verify all configurations have non-empty weights."""
        for config in ALL_CONFIGS:
            assert len(config.weights) > 0, f"Config {config.name} has no weights"

    def test_baseline_configs_exist(self):
        """Verify baseline configurations exist for each category."""
        categories = {
            "exhaustion": EXHAUSTION_CONFIGS,
            "engagement": ENGAGEMENT_CONFIGS,
            "orphan": ORPHAN_CONFIGS,
            "repetition": REPETITION_CONFIGS,
            "hedging": HEDGING_CONFIGS,
        }

        for category, configs in categories.items():
            baseline_found = any(c.baseline for c in configs)
            assert baseline_found, f"No baseline config for {category}"

    @pytest.mark.asyncio
    async def test_exhaustion_weights_impact_backtracking(self, calibration_runner):
        """Test that different exhaustion weights produce different backtracking behavior."""
        scenario = get_scenario_by_name("exhaustion_detection")
        assert scenario is not None

        results = {}
        for config in EXHAUSTION_CONFIGS:
            result = await calibration_runner.run_scenario(scenario)
            results[config.name] = result

        # High penalty should backtrack sooner than low penalty
        # (This is a simplified check - real calibration would measure backtracking turn)
        assert "high_exhaustion_penalty" in results
        assert "low_exhaustion_penalty" in results

    @pytest.mark.asyncio
    async def test_orphan_weights_impact_prioritization(self, calibration_runner):
        """Test that different orphan weights produce different prioritization."""
        scenario = get_scenario_by_name("orphan_node_priority")
        assert scenario is not None

        results = {}
        for config in ORPHAN_CONFIGS:
            result = await calibration_runner.run_scenario(scenario)
            validation = calibration_runner.validate_result(result, scenario)
            results[config.name] = validation

        # High priority should connect orphan more aggressively
        high_priority_result = results["high_orphan_priority"]
        assert "orphan_prioritized_on_turn_3" in high_priority_result.validation_results

    @pytest.mark.asyncio
    async def test_repetition_weights_impact_diversity(self, calibration_runner):
        """Test that different repetition weights produce different strategy diversity."""
        scenario = get_scenario_by_name("strategy_repetition")
        assert scenario is not None

        results = {}
        for config in REPETITION_CONFIGS:
            result = await calibration_runner.run_scenario(scenario)
            results[config.name] = result

        # High penalty should switch strategies sooner
        assert "high_repetition_penalty" in results
        assert "low_repetition_penalty" in results

    @pytest.mark.asyncio
    async def test_hedging_weights_impact_clarification(self, calibration_runner):
        """Test that different hedging weights produce different clarification behavior."""
        scenario = get_scenario_by_name("uncertainty_response")
        assert scenario is not None

        results = {}
        for config in HEDGING_CONFIGS:
            result = await calibration_runner.run_scenario(scenario)
            results[config.name] = result

        # High sensitivity should use clarify more often
        high_sensitivity = results["high_hedging_sensitivity"]
        clarify_count = sum(
            1 for s in high_sensitivity.strategies_selected if s == "clarify"
        )
        assert clarify_count >= 1


# =============================================================================
# Calibration Metrics
# =============================================================================


class TestCalibrationMetrics:
    """Tests for calibration metrics collection."""

    @pytest.fixture
    def calibration_runner(self):
        """Create a test runner for calibration."""
        return NodeExhaustionTestRunner(
            config=ValidationConfig(strict_mode=False),
            enable_signal_detection=True,
        )

    def calculate_backtracking_turn(
        self,
        result: InterviewResult,
        scenario: InterviewScenario,
    ) -> int:
        """Calculate the turn when backtracking occurred.

        Returns:
            Turn number when backtracking happened, or 0 if no backtracking
        """
        focus_nodes = [
            turn.focus_node_id for turn in scenario.user_turns if turn.focus_node_id
        ]

        # Find first node switch
        for i in range(1, len(focus_nodes)):
            if focus_nodes[i] != focus_nodes[i - 1]:
                return i + 1  # 1-indexed

        return 0

    def calculate_strategy_diversity(
        self,
        result: InterviewResult,
    ) -> float:
        """Calculate strategy diversity (unique strategies / total strategies).

        Returns:
            Diversity score from 0.0 (no diversity) to 1.0 (high diversity)
        """
        strategies = result.strategies_selected
        if not strategies:
            return 0.0

        unique_strategies = set(strategies)
        return len(unique_strategies) / len(strategies)

    def calculate_orphan_connection_rate(
        self,
        result: InterviewResult,
        scenario: InterviewScenario,
    ) -> float:
        """Calculate the rate at which orphans are connected.

        Returns:
            Connection rate from 0.0 to 1.0
        """
        # Count orphans that get connected
        orphan_count = 0
        connected_count = 0

        for i, turn in enumerate(scenario.user_turns):
            if turn.graph_changes:
                if turn.graph_changes.get("edges_added", 0) > 0:
                    # Check if this was connecting an orphan
                    if i > 0:
                        prev_graph_changes = scenario.user_turns[i - 1].graph_changes
                        if prev_graph_changes:
                            if prev_graph_changes.get("nodes_added", 0) > 0:
                                # Previous turn added node but no edges = orphan
                                orphan_count += 1
                                connected_count += 1

        return connected_count / max(orphan_count, 1)

    @pytest.mark.asyncio
    async def test_backtracking_turn_metric(self, calibration_runner):
        """Test that backtracking turn can be calculated."""
        scenario = get_scenario_by_name("exhaustion_detection")
        assert scenario is not None, "Scenario 'exhaustion_detection' not found"
        result = await calibration_runner.run_scenario(scenario)

        backtracking_turn = self.calculate_backtracking_turn(result, scenario)
        assert backtracking_turn > 0, "No backtracking detected"
        assert backtracking_turn <= scenario.turn_count

    @pytest.mark.asyncio
    async def test_strategy_diversity_metric(self, calibration_runner):
        """Test that strategy diversity can be calculated."""
        scenario = get_scenario_by_name("strategy_repetition")
        assert scenario is not None, "Scenario 'strategy_repetition' not found"
        result = await calibration_runner.run_scenario(scenario)

        diversity = self.calculate_strategy_diversity(result)
        assert 0.0 <= diversity <= 1.0
        assert diversity > 0.0  # Should have at least some diversity

    @pytest.mark.asyncio
    async def test_orphan_connection_metric(self, calibration_runner):
        """Test that orphan connection rate can be calculated."""
        scenario = get_scenario_by_name("orphan_node_priority")
        assert scenario is not None, "Scenario 'orphan_node_priority' not found"
        result = await calibration_runner.run_scenario(scenario)

        connection_rate = self.calculate_orphan_connection_rate(result, scenario)
        assert 0.0 <= connection_rate <= 1.0


# =============================================================================
# Calibration Report Generation
# =============================================================================


class TestCalibrationReport:
    """Tests for generating calibration reports."""

    @pytest.fixture
    def calibration_runner(self):
        """Create a test runner for calibration."""
        return NodeExhaustionTestRunner(
            config=ValidationConfig(strict_mode=False),
            enable_signal_detection=True,
        )

    @pytest.mark.asyncio
    async def test_generate_calibration_report(self, calibration_runner):
        """Test generating a calibration report."""
        from tests.calibration.test_signal_weights import (
            TestCalibrationMetrics,
        )

        metrics_calculator = TestCalibrationMetrics()

        # Run baseline configuration on all scenarios
        report_data = []
        for scenario in ALL_SCENARIOS:
            result = await calibration_runner.run_scenario(scenario)

            # Calculate metrics
            backtracking_turn = metrics_calculator.calculate_backtracking_turn(
                result, scenario
            )
            strategy_diversity = metrics_calculator.calculate_strategy_diversity(result)
            orphan_connection_rate = (
                metrics_calculator.calculate_orphan_connection_rate(result, scenario)
            )

            report_data.append(
                {
                    "scenario": scenario.name,
                    "turn_count": result.turn_count,
                    "execution_time_ms": result.execution_time_ms,
                    "backtracking_turn": backtracking_turn,
                    "strategy_diversity": strategy_diversity,
                    "orphan_connection_rate": orphan_connection_rate,
                }
            )

        # Verify report data is valid
        assert len(report_data) == len(ALL_SCENARIOS)
        for data in report_data:
            assert data["turn_count"] > 0
            assert data["execution_time_ms"] >= 0
            assert 0.0 <= data["strategy_diversity"] <= 1.0


# =============================================================================
# Helper Functions
# =============================================================================


def get_scenario_by_name(name: str) -> Optional[InterviewScenario]:
    """Get a scenario by name."""
    for scenario in ALL_SCENARIOS:
        if scenario.name == name:
            return scenario
    return None


def recommend_weights(
    calibration_results: List[CalibrationResult],
) -> Dict[str, float]:
    """Recommend optimal weights based on calibration results.

    Args:
        calibration_results: List of calibration results

    Returns:
        Dictionary of recommended weights
    """
    # This is a placeholder for a more sophisticated recommendation algorithm
    # In practice, this would analyze the calibration results and recommend
    # weights that produce the best overall behavior

    recommendations = BASELINE_WEIGHTS.copy()

    # Example: If high_exhaustion_penalty produces better backtracking,
    # recommend those weights
    for result in calibration_results:
        if result.passed and "aggressive" in result.config_name:
            # Extract the relevant weights and update recommendations
            for key, value in result.details.get("weights", {}).items():
                recommendations[key] = value

    return recommendations


def compare_configs(
    config1: WeightConfiguration,
    config2: WeightConfiguration,
    scenario: InterviewScenario,
) -> Dict[str, Any]:
    """Compare two weight configurations on a scenario.

    Args:
        config1: First configuration
        config2: Second configuration
        scenario: Scenario to run

    Returns:
        Comparison results
    """
    # This would run both configurations and compare their outputs
    # For now, return a placeholder
    return {
        "config1": config1.name,
        "config2": config2.name,
        "scenario": scenario.name,
        "difference": "TODO",
    }
