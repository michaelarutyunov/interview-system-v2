"""Unit tests for StrategyDiversityScorer.

Tests that strategy history is correctly tracked and used for scoring.
"""

import pytest
from src.services.scoring.tier2.strategy_diversity import StrategyDiversityScorer
from src.domain.models.knowledge_graph import GraphState


@pytest.fixture
def scorer():
    """Create a StrategyDiversityScorer with test config."""
    return StrategyDiversityScorer(config={"weight": 0.15})


@pytest.fixture
def strategy():
    """Sample strategy for testing."""
    return {
        "id": "broaden",
        "name": "Broaden",
        "type_category": "breadth",
    }


@pytest.fixture
def focus():
    """Sample focus for testing."""
    return {
        "focus_type": "open",
        "focus_description": "Explore new aspects",
    }


@pytest.mark.asyncio
async def test_no_penalty_for_first_use(scorer, strategy, focus):
    """First use of a strategy should have no penalty."""
    state = GraphState(properties={"turn_count": 1})

    result = await scorer.score(
        strategy=strategy,
        focus=focus,
        graph_state=state,
        recent_nodes=[],
        conversation_history=[],
    )

    assert result.raw_score == 1.0
    assert result.signals["recent_uses"] == 0
    assert "not used recently" in result.reasoning


@pytest.mark.asyncio
async def test_no_penalty_for_second_use(scorer, strategy, focus):
    """Second use of a strategy should have no penalty."""
    state = GraphState(properties={"turn_count": 2, "strategy_history": ["broaden"]})

    result = await scorer.score(
        strategy=strategy,
        focus=focus,
        graph_state=state,
        recent_nodes=[],
        conversation_history=[],
    )

    assert result.raw_score == 1.0
    assert result.signals["recent_uses"] == 1


@pytest.mark.asyncio
async def test_moderate_penalty_for_third_use(scorer, strategy, focus):
    """Third use of a strategy should get moderate penalty."""
    state = GraphState(
        properties={"turn_count": 3, "strategy_history": ["broaden", "broaden"]}
    )

    result = await scorer.score(
        strategy=strategy,
        focus=focus,
        graph_state=state,
        recent_nodes=[],
        conversation_history=[],
    )

    assert result.raw_score == 0.8  # moderate_penalty
    assert result.signals["recent_uses"] == 2
    assert "moderate penalty" in result.reasoning


@pytest.mark.asyncio
async def test_strong_penalty_for_fourth_use(scorer, strategy, focus):
    """Fourth use of a strategy should get strong penalty."""
    state = GraphState(
        properties={
            "turn_count": 4,
            "strategy_history": ["broaden", "broaden", "broaden"],
        }
    )

    result = await scorer.score(
        strategy=strategy,
        focus=focus,
        graph_state=state,
        recent_nodes=[],
        conversation_history=[],
    )

    assert result.raw_score == 0.6  # overuse_penalty
    assert result.signals["recent_uses"] == 3
    assert "strong penalty" in result.reasoning


@pytest.mark.asyncio
async def test_different_strategy_has_no_penalty(scorer, strategy, focus):
    """Different strategy should not be penalized by 'broaden' history."""
    state = GraphState(
        properties={
            "turn_count": 4,
            "strategy_history": ["broaden", "broaden", "broaden"],
        }
    )

    different_strategy = {"id": "deepen", "name": "Deepen", "type_category": "depth"}

    result = await scorer.score(
        strategy=different_strategy,
        focus=focus,
        graph_state=state,
        recent_nodes=[],
        conversation_history=[],
    )

    assert result.raw_score == 1.0  # No penalty for different strategy
    assert result.signals["recent_uses"] == 0


@pytest.mark.asyncio
async def test_lookback_window_limits_count(scorer, strategy, focus):
    """Only recent strategies within lookback window should count."""
    state = GraphState(
        properties={
            "turn_count": 10,
            # History with 7 entries (more than default lookback of 5)
            "strategy_history": [
                "deepen",  # Outside lookback (index 0)
                "deepen",  # Outside lookback (index 1)
                "broaden",  # Index 2 - first in lookback
                "broaden",  # Index 3
                "broaden",  # Index 4
                "deepen",  # Index 5
                "broaden",  # Index 6 - last
            ],
        }
    )

    result = await scorer.score(
        strategy=strategy,
        focus=focus,
        graph_state=state,
        recent_nodes=[],
        conversation_history=[],
    )

    # Should only count the last 5: [broaden, broaden, broaden, deepen, broaden] = 4 broadens
    assert result.signals["recent_uses"] == 4
    assert result.raw_score == 0.6  # strong penalty for 4+ uses


@pytest.mark.asyncio
async def test_empty_history_defaults_to_no_penalty(scorer, strategy, focus):
    """Empty strategy history should default to no penalty."""
    state = GraphState(properties={"turn_count": 1, "strategy_history": []})

    result = await scorer.score(
        strategy=strategy,
        focus=focus,
        graph_state=state,
        recent_nodes=[],
        conversation_history=[],
    )

    assert result.raw_score == 1.0
    assert result.signals["recent_uses"] == 0
