"""Unit tests for StrategyService."""

import pytest
from src.services.strategy_service import StrategyService, SelectionResult
from src.services.scoring.two_tier import create_scoring_engine
from src.domain.models.knowledge_graph import GraphState


@pytest.fixture
def strategy_service():
    """Create a StrategyService with test config."""
    engine = create_scoring_engine()
    return StrategyService(engine, config={})


@pytest.mark.asyncio
async def test_selects_strategy(strategy_service):
    graph_state = GraphState(
        properties={
            "turn_count": 5,
            "elements_total": ["a", "b", "c"],
            "elements_seen": {"a"},
            "recent_nodes": [{"id": "node-1", "label": "A"}],
        }
    )

    result = await strategy_service.select(graph_state, [{"id": "node-1", "label": "A"}])

    assert isinstance(result, SelectionResult)
    assert result.selected_strategy["id"] in ["deepen", "broaden", "cover_element"]
    assert result.final_score > 0


@pytest.mark.asyncio
async def test_returns_alternatives(strategy_service):
    graph_state = GraphState(
        properties={
            "turn_count": 5,
            "elements_total": ["a", "b"],
            "elements_seen": {"a"},
            "recent_nodes": [{"id": "node-1", "label": "A"}],
        }
    )

    result = await strategy_service.select(graph_state, [{"id": "node-1", "label": "A"}])

    assert hasattr(result, "alternative_strategies")
    assert isinstance(result.alternative_strategies, list)


@pytest.mark.asyncio
async def test_fallback_when_no_candidates(monkeypatch, strategy_service):
    """StrategyService falls back when no candidates available."""
    # Patch _get_possible_focuses to return empty
    def mock_focuses(self, strategy, graph_state):
        return []

    import src.services.strategy_service
    monkeypatch.setattr(
        src.services.strategy_service.StrategyService,
        "_get_possible_focuses",
        mock_focuses,
    )

    graph_state = GraphState(properties={"turn_count": 1})

    result = await strategy_service.select(graph_state, [])

    # Should return fallback (reflection strategy when all candidates vetoed)
    assert result.selected_strategy["id"] == "reflection"
