import pytest
from src.services.scoring.richness import RichnessScorer
from src.domain.models.knowledge_graph import GraphState

@pytest.mark.asyncio
async def test_low_engagement_penalizes_depth():
    scorer = RichnessScorer()
    graph_state = GraphState(properties={"avg_response_length": 30})  # Below low_threshold
    output = await scorer.score(
        strategy={"id": "deepen", "type_category": "depth"},
        focus={},
        graph_state=graph_state,
        recent_nodes=[],
    )
    assert output.raw_score == 0.6  # low_penalty
    assert "low" in output.reasoning.lower()


@pytest.mark.asyncio
async def test_low_engagement_boosts_breadth():
    scorer = RichnessScorer()
    graph_state = GraphState(properties={"avg_response_length": 30})
    output = await scorer.score(
        strategy={"id": "broaden", "type_category": "breadth"},
        focus={},
        graph_state=graph_state,
        recent_nodes=[],
    )
    assert output.raw_score > 1.0  # boost (1/0.6 ≈ 1.67)


@pytest.mark.asyncio
async def test_high_engagement_boosts_depth():
    scorer = RichnessScorer()
    graph_state = GraphState(properties={"avg_response_length": 250})  # Above high_threshold
    output = await scorer.score(
        strategy={"id": "deepen", "type_category": "depth"},
        focus={},
        graph_state=graph_state,
        recent_nodes=[],
    )
    assert output.raw_score == 1.4  # high_boost


@pytest.mark.asyncio
async def test_medium_engagement_neutral():
    scorer = RichnessScorer()
    graph_state = GraphState(properties={"avg_response_length": 100})
    output = await scorer.score(
        strategy={"id": "deepen", "type_category": "depth"},
        focus={},
        graph_state=graph_state,
        recent_nodes=[],
    )
    assert output.raw_score == 1.0
    assert "medium" in output.reasoning.lower()
