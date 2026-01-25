"""Tests for ConsecutiveExhaustionScorer."""

import pytest
from unittest.mock import Mock

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.tier1.consecutive_exhaustion import (
    ConsecutiveExhaustionScorer,
)


@pytest.fixture
def scorer():
    """Create a ConsecutiveExhaustionScorer with default config."""
    config = {
        "enabled": True,
        "params": {
            "threshold": 3,
        },
    }
    return ConsecutiveExhaustionScorer(config=config)


@pytest.fixture
def mock_graph_state():
    """Create a mock GraphState."""
    state = Mock(spec=GraphState)
    state.properties = {}
    return state


@pytest.mark.asyncio
async def test_no_exhaustion_allows_all_strategies(scorer, mock_graph_state):
    """Test that all strategies are allowed when there's no exhaustion."""
    conversation_history = [
        {"speaker": "user", "text": "I like coffee because it helps me focus"},
        {"speaker": "system", "text": "What else?"},
        {"speaker": "user", "text": "Also the taste is great"},
    ]

    strategy_deepen = {"id": "deepen", "type_category": "depth"}
    focus = {"focus_description": "Explore coffee benefits"}

    result = await scorer.evaluate(
        strategy=strategy_deepen,
        focus=focus,
        graph_state=mock_graph_state,
        recent_nodes=[],
        conversation_history=conversation_history,
    )

    assert result.is_veto is False
    assert result.signals["consecutive_count"] == 0


@pytest.mark.asyncio
async def test_single_exhaustion_allows_deepen(scorer, mock_graph_state):
    """Test that deepen is allowed with only 1 exhaustion response."""
    conversation_history = [
        {"speaker": "user", "text": "I like coffee"},
        {"speaker": "system", "text": "What else?"},
        {"speaker": "user", "text": "nothing really"},
    ]

    strategy_deepen = {"id": "deepen", "type_category": "depth"}
    focus = {"focus_description": "Explore more"}

    result = await scorer.evaluate(
        strategy=strategy_deepen,
        focus=focus,
        graph_state=mock_graph_state,
        recent_nodes=[],
        conversation_history=conversation_history,
    )

    assert result.is_veto is False
    assert result.signals["consecutive_count"] == 1


@pytest.mark.asyncio
async def test_threshold_exhaustion_vetoes_deepen(scorer, mock_graph_state):
    """Test that deepen is vetoed after 3 consecutive exhaustion responses."""
    conversation_history = [
        {"speaker": "user", "text": "I like coffee"},
        {"speaker": "system", "text": "What else?"},
        {"speaker": "user", "text": "nothing really"},
        {"speaker": "system", "text": "What else?"},
        {"speaker": "user", "text": "nothing else"},
        {"speaker": "system", "text": "What else?"},
        {"speaker": "user", "text": "nothing"},
    ]

    strategy_deepen = {"id": "deepen", "type_category": "depth"}
    focus = {"focus_description": "Explore more"}

    result = await scorer.evaluate(
        strategy=strategy_deepen,
        focus=focus,
        graph_state=mock_graph_state,
        recent_nodes=[],
        conversation_history=conversation_history,
    )

    assert result.is_veto is True
    assert result.signals["consecutive_count"] == 3
    assert "deepen" in result.reasoning
    assert "avoid repetitive 'what else' questions" in result.reasoning


@pytest.mark.asyncio
async def test_threshold_exhaustion_allows_synthesis(scorer, mock_graph_state):
    """Test that synthesis is allowed even after 3 consecutive exhaustion responses."""
    conversation_history = [
        {"speaker": "user", "text": "I like coffee"},
        {"speaker": "system", "text": "What else?"},
        {"speaker": "user", "text": "nothing really"},
        {"speaker": "system", "text": "What else?"},
        {"speaker": "user", "text": "nothing else"},
        {"speaker": "system", "text": "What else?"},
        {"speaker": "user", "text": "nothing"},
    ]

    strategy_synthesis = {"id": "synthesis", "type_category": "transition"}
    focus = {"focus_description": "Summarize and invite extension"}

    result = await scorer.evaluate(
        strategy=strategy_synthesis,
        focus=focus,
        graph_state=mock_graph_state,
        recent_nodes=[],
        conversation_history=conversation_history,
    )

    assert result.is_veto is False
    assert result.signals["consecutive_count"] == 3
    assert "shifts conversation mode" in result.reasoning


@pytest.mark.asyncio
async def test_exhaustion_resets_after_substantive_response(scorer, mock_graph_state):
    """Test that exhaustion count resets after a substantive response."""
    conversation_history = [
        {"speaker": "user", "text": "nothing really"},
        {"speaker": "system", "text": "What else?"},
        {"speaker": "user", "text": "nothing else"},
        {"speaker": "system", "text": "What else?"},
        {"speaker": "user", "text": "I also like tea"},  # Substantive response
        {"speaker": "system", "text": "What else?"},
        {"speaker": "user", "text": "nothing"},
    ]

    strategy_deepen = {"id": "deepen", "type_category": "depth"}
    focus = {"focus_description": "Explore more"}

    result = await scorer.evaluate(
        strategy=strategy_deepen,
        focus=focus,
        graph_state=mock_graph_state,
        recent_nodes=[],
        conversation_history=conversation_history,
    )

    # Count should be 1 (only the last "nothing"), not 4
    assert result.is_veto is False
    assert result.signals["consecutive_count"] == 1


@pytest.mark.asyncio
async def test_broaden_also_vetoed(scorer, mock_graph_state):
    """Test that broaden is also vetoed during exhaustion."""
    conversation_history = [
        {"speaker": "user", "text": "nothing really"},
        {"speaker": "system", "text": "What else?"},
        {"speaker": "user", "text": "nothing else"},
        {"speaker": "system", "text": "What else?"},
        {"speaker": "user", "text": "nothing"},
    ]

    strategy_broaden = {"id": "broaden", "type_category": "breadth"}
    focus = {"focus_description": "Explore related areas"}

    result = await scorer.evaluate(
        strategy=strategy_broaden,
        focus=focus,
        graph_state=mock_graph_state,
        recent_nodes=[],
        conversation_history=conversation_history,
    )

    assert result.is_veto is True


@pytest.mark.asyncio
async def test_reflection_allowed_during_exhaustion(scorer, mock_graph_state):
    """Test that reflection is allowed during exhaustion."""
    conversation_history = [
        {"speaker": "user", "text": "nothing really"},
        {"speaker": "system", "text": "What else?"},
        {"speaker": "user", "text": "nothing else"},
        {"speaker": "system", "text": "What else?"},
        {"speaker": "user", "text": "nothing"},
    ]

    strategy_reflection = {"id": "reflection", "type_category": "reflection"}
    focus = {"focus_description": "Meta-question"}

    result = await scorer.evaluate(
        strategy=strategy_reflection,
        focus=focus,
        graph_state=mock_graph_state,
        recent_nodes=[],
        conversation_history=conversation_history,
    )

    assert result.is_veto is False


def test_various_exhaustion_patterns(scorer):
    """Test that various exhaustion patterns are detected."""
    patterns = [
        "nothing",
        "nothing else",
        "nothing really",
        "nothing more",
        "don't know",
        "can't think of anything",
        "that's it",
        "that's all",
    ]

    for pattern in patterns:
        assert scorer._is_exhaustion_response(pattern), (
            f"Pattern '{pattern}' should be detected as exhaustion"
        )

    # Test non-exhaustion responses
    non_exhaustion = [
        "I like coffee",
        "It helps me focus",
        "The taste is great",
        "I prefer tea",
    ]

    for response in non_exhaustion:
        assert not scorer._is_exhaustion_response(response), (
            f"Response '{response}' should not be detected as exhaustion"
        )


def test_calculate_consecutive_exhaustion(scorer):
    """Test the consecutive exhaustion calculation logic."""
    # 3 consecutive exhaustion responses
    history = [
        {"speaker": "user", "text": "nothing"},
        {"speaker": "system", "text": "What?"},
        {"speaker": "user", "text": "nothing else"},
        {"speaker": "system", "text": "What?"},
        {"speaker": "user", "text": "nothing really"},
    ]

    count = scorer._calculate_consecutive_exhaustion(history)
    assert count == 3

    # Reset after substantive response
    history2 = [
        {"speaker": "user", "text": "nothing"},
        {"speaker": "user", "text": "nothing else"},
        {"speaker": "user", "text": "I like coffee"},  # Resets count
        {"speaker": "user", "text": "nothing really"},  # Count = 1
    ]

    count2 = scorer._calculate_consecutive_exhaustion(history2)
    assert count2 == 1


@pytest.mark.asyncio
async def test_custom_threshold(scorer, mock_graph_state):
    """Test that custom threshold works correctly."""
    # Create scorer with threshold of 2
    config = {
        "enabled": True,
        "params": {
            "threshold": 2,
        },
    }
    scorer_custom = ConsecutiveExhaustionScorer(config=config)

    conversation_history = [
        {"speaker": "user", "text": "nothing really"},
        {"speaker": "system", "text": "What else?"},
        {"speaker": "user", "text": "nothing else"},
    ]

    strategy_deepen = {"id": "deepen", "type_category": "depth"}
    focus = {"focus_description": "Explore more"}

    result = await scorer_custom.evaluate(
        strategy=strategy_deepen,
        focus=focus,
        graph_state=mock_graph_state,
        recent_nodes=[],
        conversation_history=conversation_history,
    )

    # Should veto after 2 consecutive (threshold = 2)
    assert result.is_veto is True
    assert result.signals["consecutive_count"] == 2
    assert result.signals["threshold"] == 2
