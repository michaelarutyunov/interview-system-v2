"""Tests for SaturationMetrics population in SaturationScorer (ADR-010 Phase 2).

RED Phase: Write failing tests first.
Tests that SaturationScorer populates GraphState.saturation_metrics field.
"""

import pytest
from src.domain.models.knowledge_graph import (
    GraphState,
    SaturationMetrics,
    DepthMetrics,
    CoverageState,
)
from src.services.scoring.tier2.saturation import SaturationScorer


class TestSaturationMetricsPopulation:
    """Tests for SaturationMetrics population by SaturationScorer."""

    @pytest.mark.asyncio
    async def test_scorer_populates_saturation_metrics(self):
        """SaturationScorer should populate GraphState.saturation_metrics field."""
        scorer = SaturationScorer()

        # Create a graph state without saturation_metrics
        state = GraphState(
            node_count=10,
            edge_count=15,
            nodes_by_type={"attribute": 5, "consequence": 3, "value": 2},
            depth_metrics=DepthMetrics(
                max_depth=3,
                avg_depth=1.5,
                deep_chain_count=1,
                deepest_chain_path=["node1", "node2", "node3"],
            ),
            coverage_state=CoverageState(
                covered_elements=[1, 2, 3],
                uncovered_elements=[4, 5],
                coverage_ratio=0.6,
                shallow_elements=[1],
            ),
        )

        strategy = {"id": "deepen", "type_category": "depth"}
        focus = {"focus_description": "Test focus"}
        recent_nodes = [
            {"node_type": "attribute", "id": "n1"},
            {"node_type": "attribute", "id": "n2"},
            {"node_type": "consequence", "id": "n3"},
        ]
        conversation_history = []

        # Score should populate saturation_metrics
        result = await scorer.score(
            strategy=strategy,
            focus=focus,
            graph_state=state,
            recent_nodes=recent_nodes,
            conversation_history=conversation_history,
        )

        # Verify saturation_metrics was populated
        assert state.saturation_metrics is not None
        assert isinstance(state.saturation_metrics, SaturationMetrics)
        assert hasattr(state.saturation_metrics, "chao1_ratio")
        assert hasattr(state.saturation_metrics, "new_info_rate")
        assert hasattr(state.saturation_metrics, "consecutive_low_info")
        assert hasattr(state.saturation_metrics, "is_saturated")

        # Verify values match signals
        assert state.saturation_metrics.chao1_ratio == result.signals["chao1_ratio"]
        assert state.saturation_metrics.is_saturated == result.signals["is_saturated"]

    @pytest.mark.asyncio
    async def test_scorer_updates_existing_saturation_metrics(self):
        """SaturationScorer should update existing saturation_metrics."""
        scorer = SaturationScorer()

        # Create a graph state with existing saturation_metrics
        state = GraphState(
            node_count=10,
            edge_count=15,
            nodes_by_type={"attribute": 5, "consequence": 3, "value": 2},
            depth_metrics=DepthMetrics(
                max_depth=3,
                avg_depth=1.5,
                deep_chain_count=1,
                deepest_chain_path=["node1", "node2", "node3"],
            ),
            coverage_state=CoverageState(
                covered_elements=[1, 2, 3],
                uncovered_elements=[4, 5],
                coverage_ratio=0.6,
                shallow_elements=[1],
            ),
            saturation_metrics=SaturationMetrics(
                chao1_ratio=0.5,  # Old value
                new_info_rate=0.8,
                consecutive_low_info=0,
                is_saturated=False,
            ),
        )

        strategy = {"id": "broaden", "type_category": "breadth"}
        focus = {"focus_description": "Test focus"}
        recent_nodes = []
        conversation_history = []

        # Score should update saturation_metrics
        result = await scorer.score(
            strategy=strategy,
            focus=focus,
            graph_state=state,
            recent_nodes=recent_nodes,
            conversation_history=conversation_history,
        )

        # Verify saturation_metrics was updated
        assert state.saturation_metrics is not None
        # The chao1_ratio should be recalculated based on current state
        assert state.saturation_metrics.chao1_ratio == result.signals["chao1_ratio"]
