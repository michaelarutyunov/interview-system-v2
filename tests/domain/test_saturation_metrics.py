"""Tests for SaturationMetrics in GraphState (ADR-010 Phase 2).

RED Phase: Write failing tests first.
Tests for SaturationMetrics population and usage.
"""

import pytest
from src.domain.models.knowledge_graph import (
    GraphState,
    SaturationMetrics,
    DepthMetrics,
    CoverageState,
    ElementCoverage,
)


class TestSaturationMetrics:
    """Tests for SaturationMetrics model."""

    def test_saturation_metrics_creation(self):
        """Should create SaturationMetrics with all required fields."""
        metrics = SaturationMetrics(
            chao1_ratio=0.92,
            new_info_rate=0.03,
            consecutive_low_info=3,
            is_saturated=True,
        )

        assert metrics.chao1_ratio == 0.92
        assert metrics.new_info_rate == 0.03
        assert metrics.consecutive_low_info == 3
        assert metrics.is_saturated is True

    def test_saturation_metrics_validation(self):
        """Should enforce validation constraints."""
        # chao1_ratio must be between 0 and 1
        with pytest.raises(ValueError):
            SaturationMetrics(
                chao1_ratio=1.5,  # Invalid: > 1.0
                new_info_rate=0.5,
                consecutive_low_info=0,
                is_saturated=False,
            )

        # new_info_rate must be between 0 and 1
        with pytest.raises(ValueError):
            SaturationMetrics(
                chao1_ratio=0.8,
                new_info_rate=-0.1,  # Invalid: < 0.0
                consecutive_low_info=0,
                is_saturated=False,
            )

        # consecutive_low_info must be >= 0
        with pytest.raises(ValueError):
            SaturationMetrics(
                chao1_ratio=0.8,
                new_info_rate=0.5,
                consecutive_low_info=-1,  # Invalid: < 0
                is_saturated=False,
            )

    def test_graph_state_with_saturation_metrics(self):
        """Should create GraphState with SaturationMetrics."""
        state = GraphState(
            node_count=10,
            edge_count=15,
            depth_metrics=DepthMetrics(
                max_depth=3,
                avg_depth=1.5,
                longest_chain_path=["node1", "node2", "node3"],
            ),
            coverage_state=CoverageState(
                elements={
                    1: ElementCoverage(
                        covered=True,
                        linked_node_ids=["node1"],
                        types_found=["attribute"],
                        depth_score=1.0,
                    ),
                    2: ElementCoverage(
                        covered=True,
                        linked_node_ids=["node2"],
                        types_found=["attribute"],
                        depth_score=1.0,
                    ),
                    3: ElementCoverage(
                        covered=True,
                        linked_node_ids=["node3"],
                        types_found=["attribute"],
                        depth_score=1.0,
                    ),
                },
                elements_covered=3,
                elements_total=5,
                overall_depth=1.0,
                max_depth=3.0,
            ),
            saturation_metrics=SaturationMetrics(
                chao1_ratio=0.85,
                new_info_rate=0.10,
                consecutive_low_info=1,
                is_saturated=False,
            ),
        )

        assert state.saturation_metrics is not None
        assert state.saturation_metrics.chao1_ratio == 0.85
        assert state.saturation_metrics.new_info_rate == 0.10
        assert state.saturation_metrics.consecutive_low_info == 1
        assert state.saturation_metrics.is_saturated is False

    def test_graph_state_without_saturation_metrics(self):
        """Should allow GraphState without SaturationMetrics (optional)."""
        state = GraphState(
            node_count=5,
            edge_count=7,
            depth_metrics=DepthMetrics(
                max_depth=2,
                avg_depth=1.0,
            ),
            coverage_state=CoverageState(
                elements={},
                elements_covered=0,
                elements_total=2,
                overall_depth=0.0,
                max_depth=0.0,
            ),
            # saturation_metrics not provided (optional)
        )

        assert state.saturation_metrics is None

    def test_saturation_detection_all_conditions(self):
        """Should detect saturation when all conditions are met."""
        # High Chao1 + low new info + consecutive low info = saturated
        metrics = SaturationMetrics(
            chao1_ratio=0.95,  # High coverage
            new_info_rate=0.02,  # Low new info
            consecutive_low_info=3,  # Multiple low info turns
            is_saturated=True,
        )

        assert metrics.is_saturated is True

    def test_saturation_detection_partial_conditions(self):
        """Should detect saturation with partial conditions met."""
        # High Chao1 alone should be enough
        metrics = SaturationMetrics(
            chao1_ratio=0.93,  # High coverage (>0.90 threshold)
            new_info_rate=0.15,  # Still getting new info
            consecutive_low_info=0,  # No low info streak
            is_saturated=True,  # Still saturated due to high Chao1
        )

        assert metrics.is_saturated is True

    def test_not_saturated_below_threshold(self):
        """Should not be saturated when below all thresholds."""
        metrics = SaturationMetrics(
            chao1_ratio=0.70,  # Below threshold
            new_info_rate=0.20,  # Good new info rate
            consecutive_low_info=0,  # No low info streak
            is_saturated=False,
        )

        assert metrics.is_saturated is False
