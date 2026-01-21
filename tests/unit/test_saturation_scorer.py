"""Tests for SaturationScorer."""

import pytest
from src.services.scoring.saturation import SaturationScorer
from src.domain.models.knowledge_graph import GraphState


@pytest.mark.asyncio
async def test_not_saturated_neutral():
    scorer = SaturationScorer()
    graph_state = GraphState(
        properties={
            "new_info_rate": 0.2,  # Above threshold
            "consecutive_low_info_turns": 0,
        }
    )
    output = await scorer.score(
        strategy={"id": "deepen", "type_category": "depth"},
        focus={},
        graph_state=graph_state,
        recent_nodes=[],
    )
    assert output.raw_score == 1.0
    assert "not saturated" in output.reasoning.lower()


@pytest.mark.asyncio
async def test_saturated_penalizes_depth():
    scorer = SaturationScorer()
    graph_state = GraphState(
        properties={
            "new_info_rate": 0.02,  # Below threshold
            "consecutive_low_info_turns": 3,
        }
    )
    output = await scorer.score(
        strategy={"id": "deepen", "type_category": "depth"},
        focus={},
        graph_state=graph_state,
        recent_nodes=[],
    )
    assert output.raw_score == 0.3  # saturated_penalty
    assert "saturated" in output.reasoning.lower()


@pytest.mark.asyncio
async def test_saturated_boosts_breadth():
    scorer = SaturationScorer()
    graph_state = GraphState(
        properties={
            "new_info_rate": 0.02,
            "consecutive_low_info_turns": 2,
        }
    )
    output = await scorer.score(
        strategy={"id": "broaden", "type_category": "breadth"},
        focus={},
        graph_state=graph_state,
        recent_nodes=[],
    )
    assert output.raw_score > 1.0  # boost (1/0.3 ≈ 3.3)
    assert "breadth encouraged" in output.reasoning.lower()
