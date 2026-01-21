import pytest
from src.services.scoring.arbitration import ArbitrationEngine
from src.services.scoring.coverage import CoverageScorer
from src.services.scoring.depth import DepthScorer
from src.domain.models.knowledge_graph import GraphState


@pytest.mark.asyncio
async def test_multiplies_scores():
    scorers = [
        CoverageScorer(config={"weight": 1.0}),
        DepthScorer(config={"weight": 1.0}),
    ]
    engine = ArbitrationEngine(scorers)

    graph_state = GraphState(
        properties={
            "turn_count": 3,  # Early phase -> depth boosts breadth
            "elements_total": 5,
            "elements_seen": {"a", "b"},  # Gaps -> coverage boosted
        }
    )

    score, outputs, reasoning = await engine.score(
        strategy={
            "id": "broaden",
            "type_category": "breadth",
            "priority_base": 1.0,
        },
        focus={},
        graph_state=graph_state,
        recent_nodes=[],
    )

    # Both scorers should boost breadth: 2.0 (coverage) × 1.5 (depth early phase) = 3.0
    assert score > 1.0
    assert len(outputs) == 2
    assert len(reasoning) == 3  # Base + 2 scorers


@pytest.mark.asyncio
async def test_veto_threshold():
    scorer = CoverageScorer(config={
        "params": {"gap_boost": 0.05},  # Very low boost
        "veto_threshold": 0.1,
    })
    engine = ArbitrationEngine([scorer])

    graph_state = GraphState(
        properties={
            "elements_total": 5,
            "elements_seen": {"a"},  # Gaps but low boost
        }
    )

    score, outputs, reasoning = await engine.score(
        strategy={
            "id": "cover",
            "type_category": "coverage",
            "priority_base": 0.5,  # Base below veto
        },
        focus={},
        graph_state=graph_state,
        recent_nodes=[],
    )

    # Score should be very low
    assert score < 0.1
    assert any("VETOED" in r or "ERROR" in r for r in reasoning)


@pytest.mark.asyncio
async def test_disabled_scorer_not_used():
    scorer = CoverageScorer(config={"enabled": False})
    engine = ArbitrationEngine([scorer])

    graph_state = GraphState()

    score, outputs, reasoning = await engine.score(
        strategy={"id": "test", "priority_base": 1.0},
        focus={},
        graph_state=graph_state,
        recent_nodes=[],
    )

    assert len(outputs) == 0
    assert score == 1.0  # Just base
