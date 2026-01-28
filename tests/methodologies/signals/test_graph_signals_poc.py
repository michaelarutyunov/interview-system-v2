"""
Proof-of-concept tests for signal pools architecture.

Tests validate:
1. Namespaced signals work correctly
2. Signals can be composed and pooled
3. Techniques use namespaced signals for adaptation
"""

import pytest

from src.methodologies.signals.graph import (
    GraphNodeCountSignal,
    GraphMaxDepthSignal,
    CoverageBreadthSignal,
    MissingTerminalValueSignal,
)
from src.methodologies.techniques import LadderingTechnique, ElaborationTechnique
from src.domain.models.knowledge_graph import (
    GraphState,
    DepthMetrics,
    CoverageState,
)


class TestNamespacedSignals:
    """Tests for namespaced signal format."""

    @pytest.mark.asyncio
    async def test_graph_node_count_signal_returns_namespaced_key(self):
        """Should return namespaced signal key 'graph.node_count'."""
        detector = GraphNodeCountSignal()

        # node_count must equal sum of nodes_by_type values (validation rule)
        graph_state = GraphState(
            node_count=3,
            edge_count=2,
            nodes_by_type={"attribute": 3},  # Sum = 3 matches node_count
            edges_by_type={},
            orphan_count=0,
            depth_metrics=DepthMetrics(max_depth=1, avg_depth=0.6, depth_by_element={}),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=1,
        )

        result = await detector.detect(None, graph_state, "")

        assert result == {"graph.node_count": 3}
        assert "graph.node_count" in result
        assert result["graph.node_count"] == 3

    @pytest.mark.asyncio
    async def test_graph_max_depth_signal_returns_namespaced_key(self):
        """Should return namespaced signal key 'graph.max_depth'."""
        detector = GraphMaxDepthSignal()

        graph_state = GraphState(
            node_count=2,
            edge_count=2,
            nodes_by_type={"attribute": 2},
            edges_by_type={},
            orphan_count=0,
            depth_metrics=DepthMetrics(max_depth=3, avg_depth=1.5, depth_by_element={}),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=1,
        )

        result = await detector.detect(None, graph_state, "")

        assert result == {"graph.max_depth": 3}
        assert "graph.max_depth" in result


class TestSignalComposition:
    """Tests for signal composition and pooling."""

    @pytest.mark.asyncio
    async def test_multiple_signals_can_be_composed(self):
        """Should be able to detect multiple signals and compose results."""
        detectors = [
            GraphNodeCountSignal(),
            GraphMaxDepthSignal(),
        ]

        graph_state = GraphState(
            node_count=2,
            edge_count=2,
            nodes_by_type={"attribute": 2},
            edges_by_type={},
            orphan_count=0,
            depth_metrics=DepthMetrics(max_depth=3, avg_depth=1.5, depth_by_element={}),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=1,
        )

        # Compose signals from multiple detectors
        all_signals = {}
        for detector in detectors:
            signals = await detector.detect(None, graph_state, "")
            all_signals.update(signals)

        assert all_signals == {
            "graph.node_count": 2,
            "graph.max_depth": 3,
        }

    @pytest.mark.asyncio
    async def test_coverage_breadth_signal(self):
        """Should calculate coverage breadth correctly."""
        detector = CoverageBreadthSignal()

        # Create graph with attributes and consequences, but no values
        # 2 out of 3 categories explored = 0.667 breadth
        graph_state = GraphState(
            node_count=3,
            edge_count=2,
            nodes_by_type={
                "attribute": 2,
                "functional_consequence": 1,
            },
            edges_by_type={},
            orphan_count=0,
            depth_metrics=DepthMetrics(max_depth=1, avg_depth=0.6, depth_by_element={}),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=1,
        )

        result = await detector.detect(None, graph_state, "")

        # 2 out of 3 categories explored (attributes, consequences, no values) = 0.667
        assert "graph.coverage_breadth" in result
        assert result["graph.coverage_breadth"] == pytest.approx(0.667, rel=0.1)

    @pytest.mark.asyncio
    async def test_missing_terminal_value_signal(self):
        """Should detect missing terminal values."""
        detector = MissingTerminalValueSignal()

        # Case 1: Has depth but no terminal values (missing terminal)
        graph_state = GraphState(
            node_count=3,
            edge_count=2,
            nodes_by_type={"attribute": 3},
            edges_by_type={},
            orphan_count=0,
            depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.0, depth_by_element={}),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=1,
        )

        result = await detector.detect(None, graph_state, "")
        assert result["graph.missing_terminal_value"] is True

        # Case 2: Has terminal values (not missing)
        graph_state = GraphState(
            node_count=3,
            edge_count=2,
            nodes_by_type={"terminal_value": 1, "attribute": 2},
            edges_by_type={},
            orphan_count=0,
            depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.0, depth_by_element={}),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=1,
        )
        result = await detector.detect(None, graph_state, "")
        assert result["graph.missing_terminal_value"] is False


class MockContext:
    """Mock pipeline context for technique testing."""

    def __init__(self, signals=None, recent_nodes=None):
        self.signals = signals or {}
        self.recent_nodes = recent_nodes or []


class MockNode:
    """Mock graph node."""

    def __init__(self, label):
        self.label = label


class TestTechniquesUseSignals:
    """Tests for techniques using namespaced signals."""

    @pytest.mark.asyncio
    async def test_laddering_technique_adapts_to_depth(self):
        """Should add more questions when depth is shallow."""
        technique = LadderingTechnique()

        # Shallow depth - should add extra question
        context = MockContext(
            signals={"graph.max_depth": 0},
            recent_nodes=[MockNode("quality")],
        )

        questions = await technique.generate_questions("quality", context)

        assert len(questions) == 3
        assert "Why is quality important to you?" in questions
        assert "What does quality give you?" in questions
        assert "And what does that mean for you?" in questions

    @pytest.mark.asyncio
    async def test_laddering_technique_normal_depth(self):
        """Should use standard questions when depth is sufficient."""
        technique = LadderingTechnique()

        # Normal depth - standard questions
        context = MockContext(
            signals={"graph.max_depth": 3},
            recent_nodes=[MockNode("quality")],
        )

        questions = await technique.generate_questions("quality", context)

        assert len(questions) == 2
        assert "Why is quality important to you?" in questions
        assert "What does quality give you?" in questions

    @pytest.mark.asyncio
    async def test_elaboration_technique_basic(self):
        """Should generate elaboration questions."""
        technique = ElaborationTechnique()

        context = MockContext(
            signals={},
            recent_nodes=[MockNode("quality")],
        )

        questions = await technique.generate_questions("quality", context)

        assert len(questions) == 3
        assert "Tell me more about quality." in questions
        assert "Can you elaborate on quality?" in questions
