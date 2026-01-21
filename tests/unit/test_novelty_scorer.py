import pytest
from src.services.scoring.novelty import NoveltyScorer
from src.domain.models.knowledge_graph import GraphState

@pytest.mark.asyncio
async def test_novel_focus_neutral():
    scorer = NoveltyScorer()
    recent_nodes = [
        {"id": "node-1", "label": "concept A"},
        {"id": "node-2", "label": "concept B"},
    ]
    output = await scorer.score(
        strategy={"id": "deepen"},
        focus={"node_id": "node-3"},  # Different node
        graph_state=GraphState(),
        recent_nodes=recent_nodes,
    )
    assert output.raw_score == 1.0
    assert "novel" in output.reasoning.lower()


@pytest.mark.asyncio
async def test_recent_focus_penalized():
    scorer = NoveltyScorer()
    recent_nodes = [
        {"id": "node-1", "label": "concept A"},
        {"id": "node-2", "label": "concept B"},
    ]
    output = await scorer.score(
        strategy={"id": "deepen"},
        focus={"node_id": "node-1"},  # Same as recent
        graph_state=GraphState(),
        recent_nodes=recent_nodes,
    )
    assert output.raw_score == 0.3  # recency_penalty
    assert "last" in output.reasoning.lower()


@pytest.mark.asyncio
async def test_none_node_id_neutral():
    scorer = NoveltyScorer()
    output = await scorer.score(
        strategy={"id": "broaden"},
        focus={"node_id": None},
        graph_state=GraphState(),
        recent_nodes=[],
    )
    assert output.raw_score == 1.0
