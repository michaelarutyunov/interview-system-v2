"""Tests for QuestionRepetitionScorer."""

import pytest
from unittest.mock import Mock

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.tier1.question_repetition import QuestionRepetitionScorer


@pytest.fixture
def scorer():
    """Create a QuestionRepetitionScorer with default config."""
    config = {
        "enabled": True,
        "params": {
            "threshold": 3,
        },
    }
    return QuestionRepetitionScorer(config=config)


@pytest.fixture
def mock_graph_state():
    """Create a mock GraphState."""
    state = Mock(spec=GraphState)
    state.properties = {"repetition_count": 0}
    return state


@pytest.mark.asyncio
async def test_no_repetition_allows_all_strategies(scorer, mock_graph_state):
    """Test that all strategies are allowed when there's no repetition."""
    conversation_history = [
        {
            "speaker": "system",
            "text": "What comes to mind when you think about coffee?",
        },
        {"speaker": "user", "text": "I like coffee because it helps me focus"},
        {"speaker": "system", "text": "Tell me more about that"},
    ]

    strategy_broaden = {"id": "broaden", "type_category": "breadth"}
    focus = {"focus_description": "Explore coffee benefits"}

    result = await scorer.evaluate(
        strategy=strategy_broaden,
        focus=focus,
        graph_state=mock_graph_state,
        recent_nodes=[],
        conversation_history=conversation_history,
    )

    assert result.is_veto is False
    assert result.signals["current_count"] == 0
    assert result.signals["is_repetitive"] is False


@pytest.mark.asyncio
async def test_single_repetition_allows_broaden(scorer, mock_graph_state):
    """Test that broaden is allowed with only 1 repetitive question."""
    mock_graph_state.properties = {"repetition_count": 0}

    conversation_history = [
        {"speaker": "system", "text": "What do you like about coffee?"},
        {"speaker": "user", "text": "I like coffee"},
        {"speaker": "system", "text": "What else do you like?"},
    ]

    strategy_broaden = {"id": "broaden", "type_category": "breadth"}
    focus = {"focus_description": "What else matters to you about coffee?"}

    result = await scorer.evaluate(
        strategy=strategy_broaden,
        focus=focus,
        graph_state=mock_graph_state,
        recent_nodes=[],
        conversation_history=conversation_history,
    )

    assert result.is_veto is False
    assert result.signals["current_count"] == 1
    assert result.signals["is_repetitive"] is True


@pytest.mark.asyncio
async def test_threshold_repetition_vetoes_broaden(scorer, mock_graph_state):
    """Test that broaden is vetoed after 3 consecutive repetitive questions."""
    mock_graph_state.properties = {"repetition_count": 2}

    conversation_history = [
        {"speaker": "system", "text": "What else?"},
        {"speaker": "user", "text": "nothing really"},
        {"speaker": "system", "text": "What else do you like?"},
        {"speaker": "user", "text": "nothing else"},
        {"speaker": "system", "text": "What other things?"},
    ]

    strategy_broaden = {"id": "broaden", "type_category": "breadth"}
    focus = {"focus_description": "What else about coffee?"}

    result = await scorer.evaluate(
        strategy=strategy_broaden,
        focus=focus,
        graph_state=mock_graph_state,
        recent_nodes=[],
        conversation_history=conversation_history,
    )

    assert result.is_veto is True
    assert result.signals["current_count"] == 3
    assert result.signals["is_repetitive"] is True
    assert "broaden" in result.reasoning
    assert "avoid user fatigue" in result.reasoning


@pytest.mark.asyncio
async def test_threshold_repetition_vetoes_cover_element(scorer, mock_graph_state):
    """Test that cover_element is also vetoed after 3 consecutive repetitive questions."""
    mock_graph_state.properties = {"repetition_count": 2}

    conversation_history = [
        {"speaker": "system", "text": "What else?"},
        {"speaker": "user", "text": "nothing really"},
        {"speaker": "system", "text": "What else do you like?"},
        {"speaker": "user", "text": "nothing else"},
        {"speaker": "system", "text": "What other things?"},
    ]

    strategy_cover = {"id": "cover_element", "type_category": "coverage"}
    focus = {"focus_description": "What else about taste?"}

    result = await scorer.evaluate(
        strategy=strategy_cover,
        focus=focus,
        graph_state=mock_graph_state,
        recent_nodes=[],
        conversation_history=conversation_history,
    )

    assert result.is_veto is True
    assert result.signals["current_count"] == 3
    assert "cover_element" in result.reasoning or "cover" in result.reasoning


@pytest.mark.asyncio
async def test_threshold_repetition_allows_deepen(scorer, mock_graph_state):
    """Test that deepen is allowed even after 3 consecutive repetitive questions."""
    mock_graph_state.properties = {"repetition_count": 2}

    conversation_history = [
        {"speaker": "system", "text": "What else?"},
        {"speaker": "user", "text": "nothing really"},
        {"speaker": "system", "text": "What else do you like?"},
        {"speaker": "user", "text": "nothing else"},
        {"speaker": "system", "text": "What other things?"},
    ]

    strategy_deepen = {"id": "deepen", "type_category": "depth"}
    focus = {"focus_description": "What else about coffee?"}

    result = await scorer.evaluate(
        strategy=strategy_deepen,
        focus=focus,
        graph_state=mock_graph_state,
        recent_nodes=[],
        conversation_history=conversation_history,
    )

    assert result.is_veto is False
    assert result.signals["current_count"] == 3
    assert "shifts conversation mode" in result.reasoning


@pytest.mark.asyncio
async def test_threshold_repetition_allows_synthesis(scorer, mock_graph_state):
    """Test that synthesis is allowed even after 3 consecutive repetitive questions."""
    mock_graph_state.properties = {"repetition_count": 2}

    conversation_history = [
        {"speaker": "system", "text": "What else?"},
        {"speaker": "user", "text": "nothing really"},
        {"speaker": "system", "text": "What else do you like?"},
        {"speaker": "user", "text": "nothing else"},
        {"speaker": "system", "text": "What other things?"},
    ]

    strategy_synthesis = {"id": "synthesis", "type_category": "transition"}
    focus = {"focus_description": "What else about coffee?"}

    result = await scorer.evaluate(
        strategy=strategy_synthesis,
        focus=focus,
        graph_state=mock_graph_state,
        recent_nodes=[],
        conversation_history=conversation_history,
    )

    assert result.is_veto is False
    assert result.signals["current_count"] == 3
    assert "shifts conversation mode" in result.reasoning


@pytest.mark.asyncio
async def test_repetition_resets_after_different_pattern(scorer, mock_graph_state):
    """Test that repetition count resets after a different question pattern."""
    mock_graph_state.properties = {"repetition_count": 2}

    conversation_history = [
        {"speaker": "system", "text": "What else?"},
        {"speaker": "user", "text": "nothing really"},
        {"speaker": "system", "text": "What else do you like?"},
    ]

    strategy_broaden = {"id": "broaden", "type_category": "breadth"}
    focus = {
        "focus_description": "Tell me more about your coffee experience"
    }  # No "what else"

    result = await scorer.evaluate(
        strategy=strategy_broaden,
        focus=focus,
        graph_state=mock_graph_state,
        recent_nodes=[],
        conversation_history=conversation_history,
    )

    # Count should reset to 0
    assert result.is_veto is False
    assert result.signals["current_count"] == 0
    assert result.signals["previous_count"] == 2
    assert result.signals["is_repetitive"] is False


@pytest.mark.asyncio
async def test_reflection_allowed_during_repetition(scorer, mock_graph_state):
    """Test that reflection is allowed during repetition."""
    mock_graph_state.properties = {"repetition_count": 2}

    conversation_history = [
        {"speaker": "system", "text": "What else?"},
        {"speaker": "user", "text": "nothing really"},
        {"speaker": "system", "text": "What else do you like?"},
        {"speaker": "user", "text": "nothing else"},
        {"speaker": "system", "text": "What other things?"},
    ]

    strategy_reflection = {"id": "reflection", "type_category": "reflection"}
    focus = {"focus_description": "What else about coffee?"}

    result = await scorer.evaluate(
        strategy=strategy_reflection,
        focus=focus,
        graph_state=mock_graph_state,
        recent_nodes=[],
        conversation_history=conversation_history,
    )

    assert result.is_veto is False


def test_various_repetition_patterns(scorer):
    """Test that various repetition patterns are detected."""
    patterns = [
        "What else do you like?",
        "What other things matter?",
        "What else about coffee?",
        "Anything else you want to add?",
        "What else can you tell me?",
        "What else do you notice?",
        "What else would you say?",
        "What else matters to you?",
        "What else contributes to this?",
        "What else stands out?",
        "What else is important?",
    ]

    for pattern in patterns:
        assert scorer._is_repetitive_question(pattern), (
            f"Pattern '{pattern}' should be detected as repetitive"
        )

    # Test non-repetitive questions
    non_repetitive = [
        "Tell me more about coffee",
        "Describe your experience",
        "How do you feel about this?",
        "What comes to mind?",
        "Can you elaborate?",
    ]

    for question in non_repetitive:
        assert not scorer._is_repetitive_question(question), (
            f"Question '{question}' should not be detected as repetitive"
        )


def test_count_recent_repetitive_questions(scorer):
    """Test the counting of recent repetitive questions."""
    questions = [
        "What else do you like?",  # Repetitive
        "Tell me more",  # Not repetitive
        "What other things?",  # Repetitive
        "What else about coffee?",  # Repetitive
        "How does it taste?",  # Not repetitive
    ]

    count = scorer._count_recent_repetitive_questions(questions)
    assert count == 3


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
    scorer_custom = QuestionRepetitionScorer(config=config)
    mock_graph_state.properties = {"repetition_count": 1}

    conversation_history = [
        {"speaker": "system", "text": "What else?"},
        {"speaker": "user", "text": "nothing really"},
        {"speaker": "system", "text": "What else do you like?"},
    ]

    strategy_broaden = {"id": "broaden", "type_category": "breadth"}
    focus = {"focus_description": "What else about coffee?"}

    result = await scorer_custom.evaluate(
        strategy=strategy_broaden,
        focus=focus,
        graph_state=mock_graph_state,
        recent_nodes=[],
        conversation_history=conversation_history,
    )

    # Should veto after 2 consecutive (threshold = 2)
    assert result.is_veto is True
    assert result.signals["current_count"] == 2


@pytest.mark.asyncio
async def test_no_focus_description(scorer, mock_graph_state):
    """Test behavior when focus_description is missing."""
    mock_graph_state.properties = {"repetition_count": 2}

    conversation_history = [
        {"speaker": "system", "text": "What else?"},
    ]

    strategy_broaden = {"id": "broaden", "type_category": "breadth"}
    focus = {"focus_description": ""}  # Empty description

    result = await scorer.evaluate(
        strategy=strategy_broaden,
        focus=focus,
        graph_state=mock_graph_state,
        recent_nodes=[],
        conversation_history=conversation_history,
    )

    # Should not veto when no focus_description
    assert result.is_veto is False
    assert "cannot check repetition" in result.reasoning


@pytest.mark.asyncio
async def test_case_insensitive_pattern_matching(scorer, mock_graph_state):
    """Test that pattern matching is case-insensitive."""
    mock_graph_state.properties = {"repetition_count": 0}

    variations = [
        "What Else Do You Like?",
        "WHAT ELSE ABOUT COFFEE?",
        "what other things?",
        "What Else matters?",
    ]

    for question in variations:
        assert scorer._is_repetitive_question(question), (
            f"Question '{question}' should be detected (case-insensitive)"
        )


@pytest.mark.asyncio
async def test_all_allowed_strategies(scorer, mock_graph_state):
    """Test that all allowed strategies pass through during repetition."""
    mock_graph_state.properties = {"repetition_count": 2}

    conversation_history = [
        {"speaker": "system", "text": "What else?"},
        {"speaker": "user", "text": "nothing really"},
        {"speaker": "system", "text": "What else do you like?"},
    ]

    focus = {"focus_description": "What else about coffee?"}

    allowed_strategies = [
        {"id": "deepen", "type_category": "depth"},
        {"id": "synthesis", "type_category": "transition"},
        {"id": "reflection", "type_category": "reflection"},
        {"id": "laddering", "type_category": "depth"},
        {"id": "ease", "type_category": "interaction"},
        {"id": "bridge", "type_category": "peripheral"},
        {"id": "closing", "type_category": "closing"},
        {"id": "contrast", "type_category": "contrast"},
    ]

    for strategy in allowed_strategies:
        result = await scorer.evaluate(
            strategy=strategy,
            focus=focus,
            graph_state=mock_graph_state,
            recent_nodes=[],
            conversation_history=conversation_history,
        )

        assert result.is_veto is False, (
            f"Strategy {strategy['id']} should be allowed during repetition"
        )
