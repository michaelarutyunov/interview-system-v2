import pytest
from src.services.scoring.depth import DepthScorer
from src.domain.models.knowledge_graph import GraphState


@pytest.mark.asyncio
async def test_early_phase_boosts_breadth():
    scorer = DepthScorer()
    graph_state = GraphState(properties={"turn_count": 3}, max_depth=1)
    output = await scorer.score(
        strategy={"id": "broaden", "type_category": "breadth"},
        focus={},
        graph_state=graph_state,
        recent_nodes=[],
    )
    assert output.raw_score == 1.5  # early_breadth_boost


@pytest.mark.asyncio
async def test_late_phase_boosts_depth():
    scorer = DepthScorer()
    graph_state = GraphState(properties={"turn_count": 16}, max_depth=2)
    output = await scorer.score(
        strategy={"id": "deepen", "type_category": "depth"},
        focus={},
        graph_state=graph_state,
        recent_nodes=[],
    )
    assert output.raw_score == 1.4  # late_depth_boost


@pytest.mark.asyncio
async def test_middle_phase_neutral():
    scorer = DepthScorer()
    graph_state = GraphState(properties={"turn_count": 10}, max_depth=2)
    output = await scorer.score(
        strategy={"id": "deepen", "type_category": "depth"},
        focus={},
        graph_state=graph_state,
        recent_nodes=[],
    )
    assert output.raw_score == 1.0
    assert "middle" in output.reasoning.lower()
