"""Performance tests for node exhaustion system.

These tests benchmark:
- Signal detection latency
- Joint scoring performance with varying node counts
- Memory usage of NodeStateTracker
- Total turn processing time
"""

import pytest
import time
import tracemalloc
from typing import List
from dataclasses import dataclass, field

from src.services.node_state_tracker import NodeStateTracker
from src.domain.models.knowledge_graph import KGNode


@dataclass
class PerformanceBenchmark:
    """Result of a performance benchmark.

    Attributes:
        name: Benchmark name
        metric_name: Name of the metric measured
        value: Measured value
        unit: Unit of measurement (ms, MB, etc.)
        target: Target value for this metric
        acceptable: Acceptable threshold
        passed: Whether value is within acceptable range
    """

    name: str
    metric_name: str
    value: float
    unit: str
    target: float
    acceptable: float
    passed: bool

    def __post_init__(self):
        self.passed = self.value <= self.acceptable


@dataclass
class BenchmarkResult:
    """Aggregate result of benchmark suite.

    Attributes:
        suite_name: Name of the benchmark suite
        benchmarks: List of individual benchmarks
        total_passed: Number of benchmarks that passed
        total_count: Total number of benchmarks
        success_rate: Percentage of benchmarks that passed
    """

    suite_name: str
    benchmarks: List[PerformanceBenchmark] = field(default_factory=list)
    total_passed: int = 0
    total_count: int = 0
    success_rate: float = 0.0

    def add_benchmark(self, benchmark: PerformanceBenchmark):
        """Add a benchmark to the result."""
        self.benchmarks.append(benchmark)
        self.total_count += 1
        if benchmark.passed:
            self.total_passed += 1
        self.success_rate = self.total_passed / self.total_count


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def performance_targets():
    """Performance targets from implementation plan."""
    return {
        "signal_detection_all": {"target": 100, "acceptable": 200},  # ms
        "joint_scoring_10_nodes": {"target": 50, "acceptable": 100},  # ms
        "joint_scoring_50_nodes": {"target": 150, "acceptable": 300},  # ms
        "total_turn_processing": {"target": 500, "acceptable": 1000},  # ms
    }


@pytest.fixture
def signal_detectors():
    """Get all signal detector classes."""
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

    return {
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


# =============================================================================
# Signal Detection Latency Tests
# =============================================================================


class TestSignalDetectionLatency:
    """Tests for signal detection performance."""

    @pytest.mark.asyncio
    async def test_individual_signal_latency(
        self, signal_detectors, performance_targets
    ):
        """Test latency of individual signal detectors."""
        tracker = NodeStateTracker()

        # Set up some test nodes
        for i in range(10):
            node = KGNode(
                id=f"node{i}",
                session_id="test-session",
                label=f"Node {i}",
                node_type="attribute",
                properties={"depth": 0},
            )
            await tracker.register_node(node, turn_number=0)
            await tracker.update_focus(f"node{i}", turn_number=i + 1, strategy="deepen")

        results = []

        for signal_name, detector_class in signal_detectors.items():
            if signal_name == "hedging_language":
                detector = detector_class(use_llm=False)
            else:
                detector = detector_class(tracker)

            # Measure detection time
            start_time = time.perf_counter()
            _ = await detector.detect(None, None, "test response")
            end_time = time.perf_counter()

            latency_ms = (end_time - start_time) * 1000

            # Most signals should be fast (< 10ms)
            benchmark = PerformanceBenchmark(
                name=f"signal_detection_{signal_name}",
                metric_name="latency",
                value=latency_ms,
                unit="ms",
                target=5.0,
                acceptable=10.0,
            )
            results.append(benchmark)

        # Log results
        for result in results:
            pytest.stash.setdefault(f"perf_{result.name}", result)

        # Most should pass
        passed_count = sum(1 for r in results if r.passed)
        assert passed_count >= len(results) * 0.8, (
            f"Too many slow signals: {passed_count}/{len(results)} passed"
        )

    @pytest.mark.asyncio
    async def test_all_signals_latency(self, signal_detectors, performance_targets):
        """Test latency of detecting all signals together."""
        tracker = NodeStateTracker()

        # Set up test nodes
        for i in range(10):
            node = KGNode(
                id=f"node{i}",
                label=f"Node {i}",
                properties={"depth": 0},
            )
            await tracker.register_node(node, turn_number=0)
            await tracker.update_focus(f"node{i}", turn_number=i + 1, strategy="deepen")

        # Detect all signals
        start_time = time.perf_counter()

        for signal_name, detector_class in signal_detectors.items():
            if signal_name == "hedging_language":
                detector = detector_class(use_llm=False)
            else:
                detector = detector_class(tracker)
            _ = await detector.detect(None, None, "test response")

        end_time = time.perf_counter()

        total_latency_ms = (end_time - start_time) * 1000

        target = performance_targets["signal_detection_all"]["target"]
        acceptable = performance_targets["signal_detection_all"]["acceptable"]

        benchmark = PerformanceBenchmark(
            name="signal_detection_all",
            metric_name="latency",
            value=total_latency_ms,
            unit="ms",
            target=target,
            acceptable=acceptable,
        )

        pytest.stash["perf_signal_detection_all"] = benchmark

        assert total_latency_ms < acceptable, (
            f"Signal detection too slow: {total_latency_ms:.2f}ms > {acceptable}ms"
        )

    @pytest.mark.asyncio
    async def test_signal_detection_scalability(self, signal_detectors):
        """Test signal detection latency scales with node count."""
        node_counts = [10, 50, 100]
        results = []

        for node_count in node_counts:
            tracker = NodeStateTracker()

            # Set up nodes
            for i in range(node_count):
                node = KGNode(
                    id=f"node{i}",
                    label=f"Node {i}",
                    properties={"depth": 0},
                )
                await tracker.register_node(node, turn_number=0)

            # Test one signal (exhausted)
            detector = signal_detectors["exhausted"](tracker)

            start_time = time.perf_counter()
            _ = await detector.detect(None, None, "test response")
            end_time = time.perf_counter()

            latency_ms = (end_time - start_time) * 1000
            results.append((node_count, latency_ms))

        # Check that latency scales roughly linearly
        # 10 nodes: < 5ms
        # 50 nodes: < 20ms
        # 100 nodes: < 40ms
        assert results[0][1] < 5.0, f"10 nodes: {results[0][1]:.2f}ms"
        assert results[1][1] < 20.0, f"50 nodes: {results[1][1]:.2f}ms"
        assert results[2][1] < 40.0, f"100 nodes: {results[2][1]:.2f}ms"


# =============================================================================
# Joint Scoring Performance Tests
# =============================================================================


class TestJointScoringPerformance:
    """Tests for joint scoring performance."""

    @pytest.mark.asyncio
    async def test_joint_scoring_10_nodes(self, performance_targets):
        """Test joint scoring performance with 10 nodes."""
        tracker = NodeStateTracker()

        # Set up 10 nodes
        for i in range(10):
            node = KGNode(
                id=f"node{i}",
                session_id="test-session",
                label=f"Node {i}",
                node_type="attribute",
                properties={"depth": 0},
            )
            await tracker.register_node(node, turn_number=0)
            await tracker.update_focus(f"node{i}", turn_number=i + 1, strategy="deepen")

        # Simulate joint scoring
        strategies = ["deepen", "broaden", "contrast", "cover_element"]

        start_time = time.perf_counter()

        # Score all strategy-node combinations
        for strategy in strategies:
            for node_id in tracker.get_all_states():
                # Simulate scoring computation
                state = tracker.get_state(node_id)
                _ = {
                    "focus_count": state.focus_count,
                    "yield_rate": state.yield_rate,
                    "depth": state.depth,
                }

        end_time = time.perf_counter()

        scoring_time_ms = (end_time - start_time) * 1000

        target = performance_targets["joint_scoring_10_nodes"]["target"]
        acceptable = performance_targets["joint_scoring_10_nodes"]["acceptable"]

        benchmark = PerformanceBenchmark(
            name="joint_scoring_10_nodes",
            metric_name="latency",
            value=scoring_time_ms,
            unit="ms",
            target=target,
            acceptable=acceptable,
        )

        pytest.stash["perf_joint_scoring_10_nodes"] = benchmark

        assert scoring_time_ms < acceptable, (
            f"Joint scoring too slow: {scoring_time_ms:.2f}ms > {acceptable}ms"
        )

    @pytest.mark.asyncio
    async def test_joint_scoring_50_nodes(self, performance_targets):
        """Test joint scoring performance with 50 nodes."""
        tracker = NodeStateTracker()

        # Set up 50 nodes
        for i in range(50):
            node = KGNode(
                id=f"node{i}",
                session_id="test-session",
                label=f"Node {i}",
                node_type="attribute",
                properties={"depth": 0},
            )
            await tracker.register_node(node, turn_number=0)
            if i < 10:  # Only focus on first 10
                await tracker.update_focus(
                    f"node{i}", turn_number=i + 1, strategy="deepen"
                )

        # Simulate joint scoring
        strategies = ["deepen", "broaden", "contrast", "cover_element"]

        start_time = time.perf_counter()

        for strategy in strategies:
            for node_id in tracker.get_all_states():
                state = tracker.get_state(node_id)
                _ = {
                    "focus_count": state.focus_count,
                    "yield_rate": state.yield_rate,
                    "depth": state.depth,
                }

        end_time = time.perf_counter()

        scoring_time_ms = (end_time - start_time) * 1000

        target = performance_targets["joint_scoring_50_nodes"]["target"]
        acceptable = performance_targets["joint_scoring_50_nodes"]["acceptable"]

        benchmark = PerformanceBenchmark(
            name="joint_scoring_50_nodes",
            metric_name="latency",
            value=scoring_time_ms,
            unit="ms",
            target=target,
            acceptable=acceptable,
        )

        pytest.stash["perf_joint_scoring_50_nodes"] = benchmark

        assert scoring_time_ms < acceptable, (
            f"Joint scoring too slow: {scoring_time_ms:.2f}ms > {acceptable}ms"
        )

    @pytest.mark.asyncio
    async def test_joint_scoring_100_nodes(self):
        """Test joint scoring performance with 100 nodes."""
        tracker = NodeStateTracker()

        # Set up 100 nodes
        for i in range(100):
            node = KGNode(
                id=f"node{i}",
                session_id="test-session",
                label=f"Node {i}",
                node_type="attribute",
                properties={"depth": 0},
            )
            await tracker.register_node(node, turn_number=0)
            if i < 10:  # Only focus on first 10
                await tracker.update_focus(
                    f"node{i}", turn_number=i + 1, strategy="deepen"
                )

        # Simulate joint scoring
        strategies = ["deepen", "broaden", "contrast", "cover_element"]

        start_time = time.perf_counter()

        for strategy in strategies:
            for node_id in tracker.get_all_states():
                state = tracker.get_state(node_id)
                _ = {
                    "focus_count": state.focus_count,
                    "yield_rate": state.yield_rate,
                    "depth": state.depth,
                }

        end_time = time.perf_counter()

        scoring_time_ms = (end_time - start_time) * 1000

        # 100 nodes should still be fast (< 500ms)
        assert scoring_time_ms < 500.0, (
            f"Joint scaling poorly: {scoring_time_ms:.2f}ms for 100 nodes"
        )


# =============================================================================
# Memory Usage Tests
# =============================================================================


class TestMemoryUsage:
    """Tests for memory usage."""

    @pytest.mark.asyncio
    async def test_node_state_tracker_memory_10_nodes(self):
        """Test memory usage of NodeStateTracker with 10 nodes."""
        tracemalloc.start()

        tracker = NodeStateTracker()

        # Set up 10 nodes
        for i in range(10):
            node = KGNode(
                id=f"node{i}",
                session_id="test-session",
                label=f"Node {i}",
                node_type="attribute",
                properties={"depth": 0},
            )
            await tracker.register_node(node, turn_number=0)
            await tracker.update_focus(f"node{i}", turn_number=i + 1, strategy="deepen")

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Memory usage should be modest (< 1MB)
        peak_mb = peak / 1024 / 1024
        assert peak_mb < 1.0, f"Memory usage too high: {peak_mb:.2f}MB"

    @pytest.mark.asyncio
    async def test_node_state_tracker_memory_100_nodes(self):
        """Test memory usage of NodeStateTracker with 100 nodes."""
        tracemalloc.start()

        tracker = NodeStateTracker()

        # Set up 100 nodes
        for i in range(100):
            node = KGNode(
                id=f"node{i}",
                label=f"Node {i}",
                properties={"depth": 0},
            )
            await tracker.register_node(node, turn_number=0)
            if i < 10:
                await tracker.update_focus(
                    f"node{i}", turn_number=i + 1, strategy="deepen"
                )

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Memory usage should scale linearly (< 10MB)
        peak_mb = peak / 1024 / 1024
        assert peak_mb < 10.0, f"Memory usage too high: {peak_mb:.2f}MB"

    @pytest.mark.asyncio
    async def test_signal_detectors_memory(self, signal_detectors):
        """Test memory usage of signal detectors."""
        tracemalloc.start()

        tracker = NodeStateTracker()

        # Set up 50 nodes
        for i in range(50):
            node = KGNode(
                id=f"node{i}",
                label=f"Node {i}",
                properties={"depth": 0},
            )
            await tracker.register_node(node, turn_number=0)
            await tracker.update_focus(f"node{i}", turn_number=i + 1, strategy="deepen")

        # Create all detectors
        detectors = []
        for signal_name, detector_class in signal_detectors.items():
            if signal_name == "hedging_language":
                detectors.append(detector_class(use_llm=False))
            else:
                detectors.append(detector_class(tracker))

        # Run detection
        for detector in detectors:
            await detector.detect(None, None, "test response")

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Memory usage should be modest (< 5MB)
        peak_mb = peak / 1024 / 1024
        assert peak_mb < 5.0, f"Memory usage too high: {peak_mb:.2f}MB"


# =============================================================================
# Total Turn Processing Tests
# =============================================================================


class TestTurnProcessingPerformance:
    """Tests for complete turn processing performance."""

    @pytest.mark.asyncio
    async def test_single_turn_processing(self, performance_targets):
        """Test processing a single turn."""
        from tests.synthetic.runner.node_exhaustion_test_runner import (
            NodeExhaustionTestRunner,
        )
        from tests.synthetic.scenarios.node_exhaustion_scenarios import (
            get_scenario_by_name,
        )

        scenario = get_scenario_by_name("exhaustion_detection")
        runner = NodeExhaustionTestRunner(enable_signal_detection=True)

        start_time = time.perf_counter()
        result = await runner.run_scenario(scenario)
        end_time = time.perf_counter()

        total_time_ms = (end_time - start_time) * 1000
        avg_turn_time_ms = total_time_ms / result.turn_count

        target = performance_targets["total_turn_processing"]["target"]
        acceptable = performance_targets["total_turn_processing"]["acceptable"]

        benchmark = PerformanceBenchmark(
            name="total_turn_processing",
            metric_name="avg_turn_time",
            value=avg_turn_time_ms,
            unit="ms",
            target=target,
            acceptable=acceptable,
        )

        pytest.stash["perf_total_turn_processing"] = benchmark

        assert avg_turn_time_ms < acceptable, (
            f"Turn processing too slow: {avg_turn_time_ms:.2f}ms > {acceptable}ms"
        )

    @pytest.mark.asyncio
    async def test_multiple_turns_processing(self):
        """Test processing multiple turns efficiently."""
        from tests.synthetic.scenarios.node_exhaustion_scenarios import (
            ALL_SCENARIOS,
        )
        from tests.synthetic.runner.node_exhaustion_test_runner import (
            NodeExhaustionTestRunner,
        )

        runner = NodeExhaustionTestRunner(enable_signal_detection=True)

        start_time = time.perf_counter()

        for scenario in ALL_SCENARIOS:
            await runner.run_scenario(scenario)

        end_time = time.perf_counter()

        total_time_ms = (end_time - start_time) * 1000
        total_turns = sum(s.turn_count for s in ALL_SCENARIOS)
        avg_turn_time_ms = total_time_ms / total_turns

        # Average turn time should be reasonable (< 500ms)
        assert avg_turn_time_ms < 500.0, (
            f"Average turn time too high: {avg_turn_time_ms:.2f}ms"
        )


# =============================================================================
# Benchmark Summary
# =============================================================================


@pytest.fixture(autouse=True)
def benchmark_summary(request, performance_targets):
    """Generate benchmark summary at end of test session."""
    yield

    # Only run summary at the end of the session
    if request.node.name == "test_sessionfinish":
        print("\n" + "=" * 70)
        print("PERFORMANCE BENCHMARK SUMMARY")
        print("=" * 70)

        benchmarks = []
        for key, value in request.config.stash.items():
            if key.startswith("perf_"):
                benchmarks.append(value)

        if benchmarks:
            for benchmark in benchmarks:
                if isinstance(benchmark, PerformanceBenchmark):
                    status = "✓ PASS" if benchmark.passed else "✗ FAIL"
                    print(
                        f"{status} | {benchmark.name:40} | "
                        f"{benchmark.value:8.2f} {benchmark.unit:4} | "
                        f"(target: {benchmark.target:.0f}, "
                        f"acceptable: {benchmark.acceptable:.0f})"
                    )

            print("=" * 70)

            passed = sum(1 for b in benchmarks if b.passed)
            total = len(benchmarks)
            print(
                f"Total: {passed}/{total} benchmarks passed ({passed / total * 100:.1f}%)"
            )
            print("=" * 70)
