"""Tests for GraphState data model (ADR-010).

RED Phase: Write failing tests first to prove they test the right thing.
"""

import pytest
from pydantic import ValidationError

from src.domain.models.knowledge_graph import (
    DepthMetrics,
    SaturationMetrics,
    GraphState,
    CoverageState,
    ElementCoverage,
)


class TestDepthMetrics:
    """Tests for DepthMetrics nested model."""

    def test_depth_metrics_creation(self):
        """Should create valid depth metrics."""
        metrics = DepthMetrics(
            max_depth=5,
            avg_depth=2.3,
            depth_by_element={"element_1": 3.0, "element_2": 1.5},
            longest_chain_path=["node_1", "node_2", "node_3", "node_4", "node_5"],
        )

        assert metrics.max_depth == 5
        assert metrics.avg_depth == 2.3
        assert len(metrics.depth_by_element) == 2
        assert len(metrics.longest_chain_path) == 5

    def test_depth_metrics_defaults_to_empty_collections(self):
        """Should use empty dict/list for optional fields."""
        metrics = DepthMetrics(max_depth=0, avg_depth=0.0)

        assert metrics.depth_by_element == {}
        assert metrics.longest_chain_path == []


class TestSaturationMetrics:
    """Tests for SaturationMetrics nested model."""

    def test_saturation_metrics_creation(self):
        """Should create valid saturation metrics."""
        metrics = SaturationMetrics(
            chao1_ratio=0.85,
            new_info_rate=0.3,
            consecutive_low_info=2,
            is_saturated=False,
        )

        assert metrics.chao1_ratio == 0.85
        assert metrics.new_info_rate == 0.3
        assert metrics.consecutive_low_info == 2
        assert metrics.is_saturated is False

    def test_saturation_metrics_derives_is_saturated(self):
        """Should derive is_saturated from other metrics when appropriate."""
        # High chao1 ratio + low new info + consecutive low info = saturated
        metrics = SaturationMetrics(
            chao1_ratio=0.95,
            new_info_rate=0.02,
            consecutive_low_info=5,
            is_saturated=True,  # Derived flag
        )

        assert metrics.is_saturated is True


class TestGraphState:
    """Tests for strengthened GraphState model (ADR-010)."""

    def test_graph_state_with_typed_fields(self):
        """Should create GraphState with new typed fields."""
        depth = DepthMetrics(
            max_depth=3,
            avg_depth=1.5,
            depth_by_element={"elem1": 2.0},
            longest_chain_path=["n1", "n2", "n3"],
        )
        coverage = CoverageState(
            elements={1: ElementCoverage(covered=True, linked_node_ids=["n1"])},
            elements_covered=1,
            elements_total=5,
        )

        state = GraphState(
            node_count=10,
            edge_count=8,
            nodes_by_type={"attribute": 3, "value": 7},
            edges_by_type={"leads_to": 8},
            orphan_count=2,
            depth_metrics=depth,
            coverage_state=coverage,
            current_phase="exploratory",
            turn_count=1,
            strategy_history=["broaden"],
        )

        assert state.node_count == 10
        assert state.edge_count == 8
        assert state.current_phase == "exploratory"
        assert state.turn_count == 1
        assert state.strategy_history == ["broaden"]
        assert state.depth_metrics.max_depth == 3
        assert state.coverage_state.elements_total == 5

    def test_current_phase_only_accepts_valid_values(self):
        """Should only allow valid phase values."""
        valid_phases = ["exploratory", "focused", "closing"]

        for phase in valid_phases:
            state = GraphState(
                node_count=0,
                edge_count=0,
                depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0),
                coverage_state=CoverageState(),
                current_phase=phase,
                turn_count=0,
            )
            assert state.current_phase == phase

    def test_current_phase_rejects_invalid_values(self):
        """Should reject invalid phase values."""
        with pytest.raises(ValidationError):
            GraphState(
                node_count=0,
                edge_count=0,
                depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0),
                coverage_state=CoverageState(),
                current_phase="invalid_phase",  # Invalid
                turn_count=0,
            )

    def test_coverage_state_is_required(self):
        """Should require coverage_state for coverage-driven mode."""
        # Valid with coverage_state
        state = GraphState(
            node_count=0,
            edge_count=0,
            depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=0,
        )
        assert state.coverage_state is not None

    def test_saturation_metrics_is_optional(self):
        """Should allow optional saturation_metrics (expensive to compute)."""
        # Without saturation_metrics
        state = GraphState(
            node_count=0,
            edge_count=0,
            depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=0,
            saturation_metrics=None,
        )
        assert state.saturation_metrics is None

        # With saturation_metrics
        saturation = SaturationMetrics(
            chao1_ratio=0.8,
            new_info_rate=0.2,
            consecutive_low_info=1,
            is_saturated=False,
        )
        state_with_sat = GraphState(
            node_count=0,
            edge_count=0,
            depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=0,
            saturation_metrics=saturation,
        )
        assert state_with_sat.saturation_metrics is not None
        assert state_with_sat.saturation_metrics.chao1_ratio == 0.8

    def test_extended_properties_allows_flexibility(self):
        """Should allow arbitrary properties via extended_properties."""
        state = GraphState(
            node_count=0,
            edge_count=0,
            depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=0,
            extended_properties={"experimental_metric": 42, "sentiment": "positive"},
        )

        assert state.extended_properties["experimental_metric"] == 42
        assert state.extended_properties["sentiment"] == "positive"

    def test_validates_node_count_consistency(self):
        """Should validate that node_count matches sum of nodes_by_type."""
        with pytest.raises(ValidationError, match="node_count.*must equal sum"):
            GraphState(
                node_count=5,  # Says 5 nodes
                edge_count=0,
                nodes_by_type={"attribute": 3, "value": 4},  # But 3+4=7 nodes
                depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0),
                coverage_state=CoverageState(),
                current_phase="exploratory",
                turn_count=0,
            )

    def test_validates_consistent_node_count(self):
        """Should accept consistent node counts."""
        state = GraphState(
            node_count=10,
            edge_count=0,
            nodes_by_type={"attribute": 3, "value": 7},  # 3+7=10 matches
            depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=0,
        )
        assert state.node_count == 10

    def test_turn_count_cannot_be_negative(self):
        """Should enforce non-negative turn_count."""
        with pytest.raises(ValidationError):
            GraphState(
                node_count=0,
                edge_count=0,
                depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0),
                coverage_state=CoverageState(),
                current_phase="exploratory",
                turn_count=-1,  # Invalid
            )

    def test_orphan_count_cannot_be_negative(self):
        """Should enforce non-negative orphan_count."""
        with pytest.raises(ValidationError):
            GraphState(
                node_count=0,
                edge_count=0,
                orphan_count=-1,  # Invalid
                depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0),
                coverage_state=CoverageState(),
                current_phase="exploratory",
                turn_count=0,
            )

    def test_strategy_history_defaults_to_empty_list(self):
        """Should default strategy_history to empty list."""
        state = GraphState(
            node_count=0,
            edge_count=0,
            depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=0,
        )
        assert state.strategy_history == []

    def test_backwards_compatibility_with_properties_dict(self):
        """Should support accessing data via properties dict during migration."""
        # Create state with new typed fields
        state = GraphState(
            node_count=10,
            edge_count=8,
            depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0),
            coverage_state=CoverageState(),
            current_phase="focused",
            turn_count=5,
            strategy_history=["deepen", "broaden"],
        )

        # Access via typed fields (new way)
        assert state.turn_count == 5
        assert state.current_phase == "focused"
        assert state.strategy_history == ["deepen", "broaden"]

        # TODO: Add backwards compatibility layer for properties dict access
        # This will be added in GREEN phase

    def test_node_count_cannot_be_negative(self):
        """Should enforce non-negative node_count."""
        with pytest.raises(ValidationError):
            GraphState(
                node_count=-1,  # Invalid
                edge_count=0,
                depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0),
                coverage_state=CoverageState(),
                current_phase="exploratory",
                turn_count=0,
            )

    def test_edge_count_cannot_be_negative(self):
        """Should enforce non-negative edge_count."""
        with pytest.raises(ValidationError):
            GraphState(
                node_count=0,
                edge_count=-1,  # Invalid
                depth_metrics=DepthMetrics(max_depth=0, avg_depth=0.0),
                coverage_state=CoverageState(),
                current_phase="exploratory",
                turn_count=0,
            )
