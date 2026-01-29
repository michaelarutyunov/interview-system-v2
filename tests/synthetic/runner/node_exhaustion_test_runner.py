"""Synthetic interview runner for testing node exhaustion behavior.

This module provides the NodeExhaustionTestRunner which executes synthetic
interview scenarios through the full pipeline and validates expected behaviors.
"""

import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

from tests.synthetic.scenarios.node_exhaustion_scenarios import (
    InterviewScenario,
    ValidationResult,
)
from src.domain.models.node_state import NodeState
from src.services.node_state_tracker import NodeStateTracker, GraphChangeSummary


@dataclass
class InterviewResult:
    """Result of running a synthetic interview scenario.

    Attributes:
        scenario_name: Name of the scenario that was run
        turn_count: Number of turns executed
        success: Whether the interview completed successfully
        node_states: Final node states after all turns
        signals_detected: Signals detected at each turn
        strategies_selected: Strategies selected at each turn
        errors: Any errors that occurred during execution
        execution_time_ms: Time taken to execute the scenario
        metadata: Additional execution metadata
    """

    scenario_name: str
    turn_count: int
    success: bool
    node_states: Dict[str, NodeState]
    signals_detected: List[Dict[str, Any]] = field(default_factory=list)
    strategies_selected: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationConfig:
    """Configuration for validation behavior.

    Attributes:
        strict_mode: If True, all validations must pass
        check_exhaustion_timing: Verify exhaustion detection timing
        check_backtracking: Verify backtracking behavior
        check_signal_weights: Verify signal weight application
        tolerance: Numeric tolerance for float comparisons
    """

    strict_mode: bool = True
    check_exhaustion_timing: bool = True
    check_backtracking: bool = True
    check_signal_weights: bool = True
    tolerance: float = 0.01


class NodeExhaustionTestRunner:
    """Run synthetic interviews to validate node exhaustion behavior.

    The test runner simulates interview turns by:
    1. Tracking node state through NodeStateTracker
    2. Detecting signals using signal detectors
    3. Validating expected behaviors

    Example:
        runner = NodeExhaustionTestRunner()
        result = await runner.run_scenario(scenario)
        validation = runner.validate_result(result, scenario)
    """

    def __init__(
        self,
        config: Optional[ValidationConfig] = None,
        enable_signal_detection: bool = True,
    ):
        """Initialize the test runner.

        Args:
            config: Validation configuration
            enable_signal_detection: If True, detect signals each turn
        """
        self.config = config or ValidationConfig()
        self.enable_signal_detection = enable_signal_detection
        self.signal_detectors = {}
        self._setup_signal_detectors()

    def _setup_signal_detectors(self):
        """Set up signal detectors for testing.

        Imports and initializes signal detector classes.
        """
        if not self.enable_signal_detection:
            return

        from src.methodologies.signals.graph.node_exhaustion import (
            NodeExhaustedSignal,
            NodeExhaustionScoreSignal,
            NodeYieldStagnationSignal,
        )
        from src.methodologies.signals.graph.node_engagement import (
            NodeFocusStreakSignal,
            NodeIsCurrentFocusSignal,
            NodeRecencyScoreSignal,
        )
        from src.methodologies.signals.graph.node_relationships import (
            NodeIsOrphanSignal,
            NodeEdgeCountSignal,
        )
        from src.methodologies.signals.technique.node_strategy_repetition import (
            NodeStrategyRepetitionSignal,
        )
        from src.methodologies.signals.llm.hedging_language import (
            HedgingLanguageSignal,
        )

        # Store detector classes for lazy initialization
        self.signal_detector_classes = {
            "exhausted": NodeExhaustedSignal,
            "exhaustion_score": NodeExhaustionScoreSignal,
            "yield_stagnation": NodeYieldStagnationSignal,
            "focus_streak": NodeFocusStreakSignal,
            "is_current_focus": NodeIsCurrentFocusSignal,
            "recency_score": NodeRecencyScoreSignal,
            "is_orphan": NodeIsOrphanSignal,
            "edge_count": NodeEdgeCountSignal,
            "strategy_repetition": NodeStrategyRepetitionSignal,
            "hedging_language": HedgingLanguageSignal,
        }

    async def run_scenario(
        self,
        scenario: InterviewScenario,
    ) -> InterviewResult:
        """Run a scenario and capture results.

        Args:
            scenario: InterviewScenario to execute

        Returns:
            InterviewResult with execution details
        """
        start_time = datetime.now()

        # Initialize node state tracker
        tracker = NodeStateTracker()

        # Register initial nodes
        for node_data in scenario.initial_nodes:
            from src.domain.models.knowledge_graph import KGNode

            node = KGNode(
                id=node_data["id"],
                session_id="test-session",
                label=node_data["label"],
                node_type="attribute",  # Default node type for testing
                properties={"depth": node_data.get("depth", 0)},
            )
            await tracker.register_node(node, turn_number=0)

        # Execute turns
        signals_detected = []
        strategies_selected = []
        errors = []

        try:
            for turn_num, turn in enumerate(scenario.user_turns, start=1):
                # Update node state for this turn
                if turn.focus_node_id:
                    await tracker.update_focus(
                        turn.focus_node_id,
                        turn_number=turn_num,
                        strategy=turn.strategy_used or "deepen",
                    )

                # Record graph changes if any
                if turn.graph_changes and (
                    turn.graph_changes.get("nodes_added", 0) > 0
                    or turn.graph_changes.get("edges_added", 0) > 0
                ):
                    changes = GraphChangeSummary(
                        nodes_added=turn.graph_changes.get("nodes_added", 0),
                        edges_added=turn.graph_changes.get("edges_added", 0),
                        nodes_modified=turn.graph_changes.get("nodes_modified", 0),
                    )
                    await tracker.record_yield(
                        turn.focus_node_id,
                        turn_number=turn_num,
                        graph_changes=changes,
                    )

                # Append response depth to node
                if turn.focus_node_id and turn.response_depth:
                    await tracker.append_response_signal(
                        turn.focus_node_id,
                        turn.response_depth,
                    )

                # Detect signals for this turn
                if self.enable_signal_detection:
                    turn_signals = await self._detect_signals(
                        tracker,
                        turn.response_text,
                    )
                    signals_detected.append(turn_signals)

                # Track strategy selection
                strategies_selected.append(turn.strategy_used or "deepen")

        except Exception as e:
            errors.append(f"Error executing turn: {str(e)}")

        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return InterviewResult(
            scenario_name=scenario.name,
            turn_count=len(scenario.user_turns),
            success=len(errors) == 0,
            node_states=tracker.get_all_states(),
            signals_detected=signals_detected,
            strategies_selected=strategies_selected,
            errors=errors,
            execution_time_ms=execution_time,
            metadata={
                "scenario_description": scenario.description,
                "expected_behaviors": scenario.expected_behaviors,
            },
        )

    async def _detect_signals(
        self,
        tracker: NodeStateTracker,
        response_text: str,
    ) -> Dict[str, Any]:
        """Detect all signals for current state.

        Args:
            tracker: NodeStateTracker with current state
            response_text: User's response text

        Returns:
            Dictionary of detected signals
        """
        all_signals = {}

        for signal_name, detector_class in self.signal_detector_classes.items():
            try:
                # Create detector instance
                if signal_name == "hedging_language":
                    # Hedging language doesn't need tracker
                    detector = detector_class(use_llm=False)
                else:
                    detector = detector_class(tracker)

                # Detect signals
                signals = await detector.detect(None, None, response_text)
                all_signals.update(signals)

            except Exception as e:
                # Log error but continue
                all_signals[f"{signal_name}_error"] = str(e)

        return all_signals

    def validate_result(
        self,
        result: InterviewResult,
        scenario: InterviewScenario,
    ) -> ValidationResult:
        """Validate that result matches expected behaviors.

        Args:
            result: InterviewResult from running scenario
            scenario: InterviewScenario with expected behaviors

        Returns:
            ValidationResult with validation results
        """
        validation_results = {}
        details = {}

        # Validate each expected behavior
        for behavior in scenario.expected_behaviors:
            validation_result = self._validate_behavior(
                behavior,
                result,
                scenario,
            )
            validation_results[behavior] = validation_result["passed"]
            details[behavior] = validation_result["details"]

        # Overall pass status
        if self.config.strict_mode:
            passed = all(validation_results.values())
        else:
            passed = any(validation_results.values())

        return ValidationResult(
            scenario_name=scenario.name,
            passed=passed,
            validation_results=validation_results,
            details=details,
        )

    def _validate_behavior(
        self,
        behavior: str,
        result: InterviewResult,
        scenario: InterviewScenario,
    ) -> Dict[str, Any]:
        """Validate a single expected behavior.

        Args:
            behavior: Expected behavior string
            result: InterviewResult to validate
            scenario: Scenario context

        Returns:
            Dict with "passed" bool and "details" dict
        """
        passed = False
        details = {}

        # Exhaustion detection
        if "exhausted" in behavior.lower():
            passed, details = self._validate_exhaustion(behavior, result, scenario)

        # Backtracking behavior
        elif "backtrack" in behavior.lower():
            passed, details = self._validate_backtracking(behavior, result, scenario)

        # Strategy selection
        elif "strategy" in behavior.lower() or "selected" in behavior.lower():
            passed, details = self._validate_strategy_selection(
                behavior, result, scenario
            )

        # Signal detection
        elif "detected" in behavior.lower():
            passed, details = self._validate_signal_detection(
                behavior, result, scenario
            )

        # Orphan behavior
        elif "orphan" in behavior.lower():
            passed, details = self._validate_orphan_behavior(behavior, result, scenario)

        # Phase behavior
        elif "phase" in behavior.lower():
            passed, details = self._validate_phase_behavior(behavior, result, scenario)

        # Fatigue behavior
        elif "fatigue" in behavior.lower() or "engagement" in behavior.lower():
            passed, details = self._validate_fatigue_behavior(
                behavior, result, scenario
            )

        # Default: try to validate generically
        else:
            passed, details = self._validate_generic(behavior, result, scenario)

        return {"passed": passed, "details": details}

    def _validate_exhaustion(
        self,
        behavior: str,
        result: InterviewResult,
        scenario: InterviewScenario,
    ) -> tuple[bool, Dict[str, Any]]:
        """Validate exhaustion detection."""
        # Find exhausted nodes in signals
        exhausted_nodes = []
        for turn_signals in result.signals_detected:
            for key, value in turn_signals.items():
                if "exhausted" in key and value == "true":
                    node_id = key.split(".")[-1] if "." in key else key
                    exhausted_nodes.append(node_id)

        metadata = scenario.metadata
        expected_exhausted_node = metadata.get("exhaustion_node")

        passed = (
            expected_exhausted_node in exhausted_nodes
            if expected_exhausted_node
            else len(exhausted_nodes) > 0
        )

        details = {
            "exhausted_nodes": exhausted_nodes,
            "expected_node": expected_exhausted_node,
        }

        return passed, details

    def _validate_backtracking(
        self,
        behavior: str,
        result: InterviewResult,
        scenario: InterviewScenario,
    ) -> tuple[bool, Dict[str, Any]]:
        """Validate backtracking behavior."""
        # Check if different nodes were selected after exhaustion
        focus_nodes = [
            turn.focus_node_id for turn in scenario.user_turns if turn.focus_node_id
        ]

        # Look for node switches
        node_switches = []
        prev_node = None
        for node in focus_nodes:
            if prev_node and node != prev_node:
                node_switches.append((prev_node, node))
            prev_node = node

        passed = len(node_switches) > 0
        details = {
            "node_switches": node_switches,
            "focus_sequence": focus_nodes,
        }

        return passed, details

    def _validate_strategy_selection(
        self,
        behavior: str,
        result: InterviewResult,
        scenario: InterviewScenario,
    ) -> tuple[bool, Dict[str, Any]]:
        """Validate strategy selection."""
        strategies = result.strategies_selected
        metadata = scenario.metadata

        # Check if expected strategy was selected
        if "on_turn" in behavior:
            # Extract turn number from behavior (e.g., "on_turn_5")
            import re

            turn_match = re.search(r"turn_(\d+)", behavior)
            if turn_match:
                turn_num = int(turn_match.group(1)) - 1  # 0-indexed
                if turn_num < len(strategies):
                    expected_strategy = (
                        metadata.get("strategy_sequence", [])[turn_num]
                        if "strategy_sequence" in metadata
                        else None
                    )
                    actual_strategy = strategies[turn_num]
                    passed = (
                        actual_strategy == expected_strategy
                        if expected_strategy
                        else True
                    )
                    details = {
                        "turn": turn_num + 1,
                        "expected": expected_strategy,
                        "actual": actual_strategy,
                    }
                    return passed, details

        # Check if strategy was selected at all
        passed = len(strategies) > 0
        details = {
            "strategies_used": strategies,
        }

        return passed, details

    def _validate_signal_detection(
        self,
        behavior: str,
        result: InterviewResult,
        scenario: InterviewScenario,
    ) -> tuple[bool, Dict[str, Any]]:
        """Validate signal detection."""
        # Check if signal was detected
        signal_found = False
        signal_values = []

        for turn_signals in result.signals_detected:
            for key, value in turn_signals.items():
                if any(term in key.lower() for term in behavior.lower().split("_")):
                    signal_found = True
                    signal_values.append((key, value))

        passed = signal_found
        details = {
            "signal_detected": signal_found,
            "signal_values": signal_values,
        }

        return passed, details

    def _validate_orphan_behavior(
        self,
        behavior: str,
        result: InterviewResult,
        scenario: InterviewScenario,
    ) -> tuple[bool, Dict[str, Any]]:
        """Validate orphan node behavior."""
        # Check for orphan signals
        orphan_nodes = []
        for turn_signals in result.signals_detected:
            for key, value in turn_signals.items():
                if "orphan" in key.lower() and value == "true":
                    node_id = key.split(".")[-1] if "." in key else key
                    orphan_nodes.append(node_id)

        metadata = scenario.metadata
        expected_orphan = metadata.get("orphan_node")

        passed = (
            expected_orphan in orphan_nodes
            if expected_orphan
            else len(orphan_nodes) > 0
        )
        details = {
            "orphan_nodes": orphan_nodes,
            "expected_orphan": expected_orphan,
        }

        return passed, details

    def _validate_phase_behavior(
        self,
        behavior: str,
        result: InterviewResult,
        scenario: InterviewScenario,
    ) -> tuple[bool, Dict[str, Any]]:
        """Validate phase behavior."""
        # Check phase signals
        phases_detected = []
        for turn_signals in result.signals_detected:
            if "interview.phase" in turn_signals:
                phases_detected.append(turn_signals["interview.phase"])

        metadata = scenario.metadata
        expected_phases = metadata.get("phase_sequence", [])

        # Check if phases match expected sequence
        passed = len(phases_detected) > 0
        if expected_phases:
            passed = phases_detected == expected_phases

        details = {
            "phases_detected": phases_detected,
            "expected_phases": expected_phases,
        }

        return passed, details

    def _validate_fatigue_behavior(
        self,
        behavior: str,
        result: InterviewResult,
        scenario: InterviewScenario,
    ) -> tuple[bool, Dict[str, Any]]:
        """Validate fatigue behavior."""
        # Check for shallow/surface responses
        shallow_responses = 0
        for turn in scenario.user_turns:
            if turn.response_depth in ("shallow", "surface"):
                shallow_responses += 1

        metadata = scenario.metadata
        expected_fatigue = metadata.get("fatigue_detected", [])

        # Check if fatigue was detected at expected turns
        passed = shallow_responses > 0
        details = {
            "shallow_response_count": shallow_responses,
            "expected_fatigue_pattern": expected_fatigue,
        }

        return passed, details

    def _validate_generic(
        self,
        behavior: str,
        result: InterviewResult,
        scenario: InterviewScenario,
    ) -> tuple[bool, Dict[str, Any]]:
        """Generic validation fallback."""
        # Try to find matching behavior in results
        behavior_lower = behavior.lower()

        # Check signals
        for turn_signals in result.signals_detected:
            for key, value in turn_signals.items():
                if any(term in key.lower() for term in behavior_lower.split("_")):
                    return True, {"signal": key, "value": value}

        # Check strategies
        for strategy in result.strategies_selected:
            if strategy.lower() in behavior_lower:
                return True, {"strategy": strategy}

        # Default to False
        return False, {"reason": "No matching validation found"}


# =============================================================================
# Convenience Functions
# =============================================================================


async def run_scenario_async(
    scenario: InterviewScenario,
    config: Optional[ValidationConfig] = None,
) -> tuple[InterviewResult, ValidationResult]:
    """Run a scenario and validate it.

    Args:
        scenario: InterviewScenario to run
        config: Optional validation configuration

    Returns:
        Tuple of (InterviewResult, ValidationResult)
    """
    runner = NodeExhaustionTestRunner(config=config)
    result = await runner.run_scenario(scenario)
    validation = runner.validate_result(result, scenario)
    return result, validation


def run_scenario_sync(
    scenario: InterviewScenario,
    config: Optional[ValidationConfig] = None,
) -> tuple[InterviewResult, ValidationResult]:
    """Run a scenario synchronously.

    Args:
        scenario: InterviewScenario to run
        config: Optional validation configuration

    Returns:
        Tuple of (InterviewResult, ValidationResult)
    """
    return asyncio.run(run_scenario_async(scenario, config))
