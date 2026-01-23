"""Unit tests for TwoTierScoringEngine error handling.

Tests the fail-fast behavior when scorers raise exceptions.
"""

import pytest
from src.services.scoring.two_tier.engine import TwoTierScoringEngine
from src.services.scoring.two_tier.base import Tier1Scorer, Tier1Output, Tier2Scorer
from src.domain.models.knowledge_graph import GraphState
from src.core.exceptions import ScorerFailureError


class FailingTier1Scorer(Tier1Scorer):
    """Test scorer that always raises an exception."""

    async def evaluate(
        self, strategy, focus, graph_state, recent_nodes, conversation_history
    ):
        raise ValueError("Tier 1 scorer intentionally failed")


class PassingTier1Scorer(Tier1Scorer):
    """Test scorer that always passes."""

    async def evaluate(
        self, strategy, focus, graph_state, recent_nodes, conversation_history
    ):
        return Tier1Output(
            scorer_id=self.scorer_id,
            is_veto=False,
            reasoning="Passing for test",
            signals={},
        )


class FailingTier2Scorer(Tier2Scorer):
    """Test scorer that always raises an exception."""

    async def score(
        self, strategy, focus, graph_state, recent_nodes, conversation_history
    ):
        raise ValueError("Tier 2 scorer intentionally failed")


class PassingTier2Scorer(Tier2Scorer):
    """Test scorer that returns a valid score."""

    async def score(
        self, strategy, focus, graph_state, recent_nodes, conversation_history
    ):
        return self.make_output(
            raw_score=1.5,
            signals={},
            reasoning="Passing for test",
        )


@pytest.fixture
def test_strategy():
    """Sample strategy for testing."""
    return {
        "id": "test_strategy",
        "name": "Test Strategy",
        "type_category": "depth",
    }


@pytest.fixture
def test_focus():
    """Sample focus for testing."""
    return {
        "focus_type": "node",
        "focus_description": "Test focus",
        "node_id": "node-1",
        "properties": {},
    }


@pytest.fixture
def test_graph_state():
    """Sample graph state for testing."""
    return GraphState(
        properties={
            "turn_count": 5,
            "elements_total": ["a", "b"],
            "elements_seen": {"a"},
            "recent_nodes": [],
        }
    )


@pytest.mark.asyncio
async def test_tier1_scorer_failure_raises_scorer_failure_error(
    test_strategy, test_focus, test_graph_state
):
    """When a Tier 1 scorer fails, should raise ScorerFailureError."""
    engine = TwoTierScoringEngine(
        tier1_scorers=[FailingTier1Scorer()],
        tier2_scorers=[PassingTier2Scorer()],
    )

    with pytest.raises(ScorerFailureError) as exc_info:
        await engine.score_candidate(
            strategy=test_strategy,
            focus=test_focus,
            graph_state=test_graph_state,
            recent_nodes=[],
            conversation_history=[],
        )

    # Verify error message contains scorer ID
    assert "FailingTier1Scorer" in str(exc_info.value)
    assert "Tier 1 scorer intentionally failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_tier2_scorer_failure_raises_scorer_failure_error(
    test_strategy, test_focus, test_graph_state
):
    """When a Tier 2 scorer fails, should raise ScorerFailureError."""
    engine = TwoTierScoringEngine(
        tier1_scorers=[PassingTier1Scorer()],
        tier2_scorers=[FailingTier2Scorer()],
    )

    with pytest.raises(ScorerFailureError) as exc_info:
        await engine.score_candidate(
            strategy=test_strategy,
            focus=test_focus,
            graph_state=test_graph_state,
            recent_nodes=[],
            conversation_history=[],
        )

    # Verify error message contains scorer ID
    assert "FailingTier2Scorer" in str(exc_info.value)
    assert "Tier 2 scorer intentionally failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_tier1_failure_prevents_tier2_execution(
    test_strategy, test_focus, test_graph_state
):
    """When Tier 1 fails, Tier 2 scorers should not be executed."""
    tier2_executed = False

    class TrackedTier2Scorer(Tier2Scorer):
        async def score(
            self, strategy, focus, graph_state, recent_nodes, conversation_history
        ):
            nonlocal tier2_executed
            tier2_executed = True
            return self.make_output(
                raw_score=1.0, signals={}, reasoning="Should not execute"
            )

    engine = TwoTierScoringEngine(
        tier1_scorers=[FailingTier1Scorer()],
        tier2_scorers=[TrackedTier2Scorer()],
    )

    with pytest.raises(ScorerFailureError):
        await engine.score_candidate(
            strategy=test_strategy,
            focus=test_focus,
            graph_state=test_graph_state,
            recent_nodes=[],
            conversation_history=[],
        )

    assert not tier2_executed, "Tier 2 scorer should not execute after Tier 1 failure"


@pytest.mark.asyncio
async def test_multiple_tier2_scorers_one_fails(
    test_strategy, test_focus, test_graph_state
):
    """When one of multiple Tier 2 scorers fails, should raise immediately."""
    engine = TwoTierScoringEngine(
        tier1_scorers=[PassingTier1Scorer()],
        tier2_scorers=[
            PassingTier2Scorer(config={"weight": 0.5}),
            FailingTier2Scorer(config={"weight": 0.5}),
        ],
    )

    with pytest.raises(ScorerFailureError) as exc_info:
        await engine.score_candidate(
            strategy=test_strategy,
            focus=test_focus,
            graph_state=test_graph_state,
            recent_nodes=[],
            conversation_history=[],
        )

    assert "FailingTier2Scorer" in str(exc_info.value)
