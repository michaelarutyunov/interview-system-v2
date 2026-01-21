"""Tests for CoverageScorer."""

import pytest
from src.services.scoring.coverage import CoverageScorer
from src.domain.models.knowledge_graph import GraphState


@pytest.mark.asyncio
async def test_coverage_complete_no_boost():
    scorer = CoverageScorer()
    graph_state = GraphState(
        properties={
            "elements_total": 5,
            "elements_seen": {"a", "b", "c", "d", "e"},
        }
    )
    output = await scorer.score(
        strategy={"id": "cover", "type_category": "coverage"},
        focus={},
        graph_state=graph_state,
        recent_nodes=[],
    )
    assert output.raw_score == 1.0


@pytest.mark.asyncio
async def test_coverage_gap_boosts_coverage_strategy():
    scorer = CoverageScorer()
    graph_state = GraphState(
        properties={"elements_total": 5, "elements_seen": {"a", "b", "c"}}
    )
    output = await scorer.score(
        strategy={"id": "cover", "type_category": "coverage"},
        focus={},
        graph_state=graph_state,
        recent_nodes=[],
    )
    assert output.raw_score == 2.0  # gap_boost


@pytest.mark.asyncio
async def test_coverage_gap_no_effect_on_depth():
    scorer = CoverageScorer()
    graph_state = GraphState(
        properties={
            "elements_total": 5,
            "elements_seen": {"a", "b", "c"},
        }
    )
    output = await scorer.score(
        strategy={"id": "deepen", "type_category": "depth"},
        focus={},
        graph_state=graph_state,
        recent_nodes=[],
    )
    assert output.raw_score == 1.0
