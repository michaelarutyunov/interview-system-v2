"""Integration tests for QuestionRepetitionScorer based on real session data."""

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
def graph_state():
    """Create a GraphState for tracking."""
    state = Mock(spec=GraphState)
    state.properties = {}
    return state


@pytest.mark.asyncio
async def test_session_05a609ac_scenario_repetitive_questions(scorer, graph_state):
    """
    Test scenario based on session_05a609ac.json where the system asked
    10 variations of "what else" questions causing user fatigue.

    This test simulates the repetitive pattern that occurred in that session.
    """
    # Simulate the repetitive "what else" pattern from the session
    questions_asked = [
        "What else do you notice about oat milk when you use it?",
        "What other things do you notice about oat milk compared to regular milk?",
        "What other alternatives have you considered besides oat milk?",
        "What else do you look for when choosing what to add to your coffee?",
        "What else matters to you about your coffee experience beyond the milk froth?",
        "What else about your coffee experience is important to you besides the flavour, strength, and milk froth?",
        "What other aspects of your coffee ritual or routine matter to you?",
        "What else contributes to making your coffee experience feel right for you?",
        "What else stands out to you or make it meaningful?",
        "What else matters to you when you think about your coffee experience?",
    ]

    # Initialize counter
    graph_state.properties = {"repetition_count": 0}

    # Test first few questions - should not veto
    for i in range(2):
        focus = {"focus_description": questions_asked[i]}
        strategy = {"id": "broaden", "type_category": "breadth"}

        result = await scorer.evaluate(
            strategy=strategy,
            focus=focus,
            graph_state=graph_state,
            recent_nodes=[],
            conversation_history=[],
        )

        # First 2 questions should not trigger veto
        assert result.is_veto is False, f"Question {i + 1} should not be vetoed"
        # Update the counter in graph_state
        graph_state.properties["repetition_count"] = result.signals["current_count"]

    # Third question should trigger veto for broaden
    focus = {"focus_description": questions_asked[2]}
    strategy = {"id": "broaden", "type_category": "breadth"}

    result = await scorer.evaluate(
        strategy=strategy,
        focus=focus,
        graph_state=graph_state,
        recent_nodes=[],
        conversation_history=[],
    )

    # Should veto broaden after 3rd repetitive question
    assert result.is_veto is True, "Should veto broaden after 3rd 'what else' question"
    assert result.signals["current_count"] == 3
    assert "avoid user fatigue" in result.reasoning


@pytest.mark.asyncio
async def test_session_05a609ac_scenario_deepen_allowed(scorer, graph_state):
    """
    Test that deepen strategy is allowed even with repetitive questions,
    as it shifts the conversation mode.
    """
    # Simulate having asked several "what else" questions
    graph_state.properties = {"repetition_count": 2}

    # Even with repetitive count, deepen should be allowed
    focus = {"focus_description": "What else contributes to this?"}
    strategy = {"id": "deepen", "type_category": "depth"}

    result = await scorer.evaluate(
        strategy=strategy,
        focus=focus,
        graph_state=graph_state,
        recent_nodes=[],
        conversation_history=[],
    )

    # Deepen should be allowed even at threshold
    assert result.is_veto is False, "Deepen should be allowed during repetition"
    assert result.signals["current_count"] == 3
    assert "shifts conversation mode" in result.reasoning


@pytest.mark.asyncio
async def test_session_05a609ac_scenario_synthesis_breaks_cycle(scorer, graph_state):
    """
    Test that using synthesis strategy breaks the repetitive cycle.
    """
    # Start with repetitive pattern
    graph_state.properties = {"repetition_count": 2}

    # Use synthesis instead of broaden
    focus = {"focus_description": "Summarize what we've discussed and invite extension"}
    strategy = {"id": "synthesis", "type_category": "transition"}

    result = await scorer.evaluate(
        strategy=strategy,
        focus=focus,
        graph_state=graph_state,
        recent_nodes=[],
        conversation_history=[],
    )

    # Synthesis should be allowed
    assert result.is_veto is False, "Synthesis should be allowed"

    # The next question (non-repetitive) should reset the counter
    focus2 = {"focus_description": "Tell me more about your experience"}
    strategy2 = {"id": "broaden", "type_category": "breadth"}

    result2 = await scorer.evaluate(
        strategy=strategy2,
        focus=focus2,
        graph_state=graph_state,
        recent_nodes=[],
        conversation_history=[],
    )

    # Counter should reset
    assert result2.is_veto is False, "Non-repetitive question should not be vetoed"
    assert result2.signals["current_count"] == 0, (
        "Counter should reset after non-repetitive question"
    )


@pytest.mark.asyncio
async def test_session_05a609ac_scenario_cover_element_also_vetoed(scorer, graph_state):
    """
    Test that cover_element strategy is also vetoed during repetition,
    as it also asks for "more" content.
    """
    # Simulate having asked several "what else" questions
    graph_state.properties = {"repetition_count": 2}

    # cover_element should also be vetoed
    focus = {"focus_description": "What else about the taste?"}
    strategy = {"id": "cover_element", "type_category": "coverage"}

    result = await scorer.evaluate(
        strategy=strategy,
        focus=focus,
        graph_state=graph_state,
        recent_nodes=[],
        conversation_history=[],
    )

    # cover_element should be vetoed
    assert result.is_veto is True, "cover_element should be vetoed during repetition"
    assert result.signals["current_count"] == 3


@pytest.mark.asyncio
async def test_richness_and_momentum_decline_prevention(scorer, graph_state):
    """
    Test that the scorer prevents the richness_score and momentum decline
    observed in session_05a609ac.json (0.33 -> 0.10, 50 -> 15).

    By vetoing repetitive broaden/cover_element strategies and allowing
    deepen/synthesis/reflection, the system maintains engagement.
    """
    # Simulate mid-session with several repetitive questions
    graph_state.properties = {"repetition_count": 2}

    # Try to use broaden - should be vetoed
    focus = {"focus_description": "What else about your coffee?"}
    strategy = {"id": "broaden", "type_category": "breadth"}

    result = await scorer.evaluate(
        strategy=strategy,
        focus=focus,
        graph_state=graph_state,
        recent_nodes=[],
        conversation_history=[],
    )

    # Should veto to prevent fatigue
    assert result.is_veto is True, "Should veto broaden to prevent user fatigue"

    # Recommended strategies should include alternatives
    recommended = result.signals.get("recommended_strategies", [])
    assert "deepen" in recommended, "Should recommend deepen as alternative"
    assert "synthesis" in recommended, "Should recommend synthesis as alternative"
    assert "reflection" in recommended, "Should recommend reflection as alternative"
