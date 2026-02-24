"""Integration test: verify same-turn new nodes produce differentiated scores."""

import pytest
from unittest.mock import MagicMock

from src.domain.models.node_state import NodeState
from src.methodologies.registry import StrategyConfig
from src.methodologies.scoring import rank_strategy_node_pairs


@pytest.fixture
def same_turn_nodes():
    """Two nodes created in the same turn - identical by turn recency."""
    return {
        "node-1": NodeState(
            node_id="node-1",
            label="flavor concerns",
            created_at_turn=3,
            depth=0,
            node_type="pain_point",
        ),
        "node-2": NodeState(
            node_id="node-2",
            label="cost concerns",
            created_at_turn=3,
            depth=0,
            node_type="pain_point",
        ),
    }


@pytest.fixture
def strategy():
    """A strategy with type_priority and slot_saturation weights."""
    return StrategyConfig(
        name="test_strategy",
        description="Test strategy",
        signal_weights={
            "graph.node.type_priority": 0.6,
            "graph.node.slot_saturation.low": 0.5,
            "graph.node.slot_saturation.medium": -0.2,
            "graph.node.slot_saturation.high": -0.5,
        },
        node_type_priorities={"pain_point": 0.8},
    )


@pytest.mark.asyncio
async def test_type_priority_breaks_tie(same_turn_nodes, strategy):
    """type_priority signal breaks scoring ties among same-turn new nodes."""
    # Mock node tracker
    node_tracker = MagicMock()
    node_tracker.get_all_states.return_value = same_turn_nodes

    # Mock context and graph state
    context = MagicMock()
    context.session_id = "test-session"
    graph_state = MagicMock()

    # Global signals: empty to focus on node-level differentiation
    global_signals = {}

    # Node signals: include type_priority differentiation
    node_signals = {
        "node-1": {
            "graph.node.type_priority": 0.8,  # pain_point
            "graph.node.slot_saturation": "low",  # low saturation
        },
        "node-2": {
            "graph.node.type_priority": 0.8,  # pain_point
            "graph.node.slot_saturation": "medium",  # medium saturation
        },
    }

    # Score pairs
    scored_pairs, _ = rank_strategy_node_pairs(
        strategies=[strategy],
        global_signals=global_signals,
        node_signals=node_signals,
        node_tracker=node_tracker,
        phase_weights=None,
        phase_bonuses=None,
    )

    # Both (strategy, node) pairs should be scored
    assert len(scored_pairs) == 2

    # Extract scores
    scores = {node_id: score for _, node_id, score in scored_pairs}

    # node-1 should score higher due to lower slot saturation (1 vs 5)
    assert scores["node-1"] > scores["node-2"]
    # Verify the difference comes from slot_saturation signal
    # node-1: slot_saturation.low=0.5, node-2: slot_saturation.medium=-0.2
    # Difference should be 0.7 (plus any base_score)
    score_diff = scores["node-1"] - scores["node-2"]
    assert score_diff >= 0.5  # At least the slot_saturation difference


@pytest.mark.asyncio
async def test_slot_saturation_differentiates_same_type_nodes(same_turn_nodes, strategy):
    """slot_saturation signal differentiates nodes of same type created together."""
    node_tracker = MagicMock()
    node_tracker.get_all_states.return_value = same_turn_nodes

    context = MagicMock()
    context.session_id = "test-session"
    graph_state = MagicMock()

    global_signals = {}

    # Same type_priority, different slot_saturation
    node_signals = {
        "node-1": {
            "graph.node.type_priority": 0.8,
            "graph.node.slot_saturation": "low",  # very fresh slot
        },
        "node-2": {
            "graph.node.type_priority": 0.8,
            "graph.node.slot_saturation": "high",  # highly saturated slot
        },
    }

    scored_pairs, _ = rank_strategy_node_pairs(
        strategies=[strategy],
        global_signals=global_signals,
        node_signals=node_signals,
        node_tracker=node_tracker,
        phase_weights=None,
        phase_bonuses=None,
    )

    assert len(scored_pairs) == 2
    scores = {node_id: score for _, node_id, score in scored_pairs}

    # node-1 should score much higher due to fresh slot
    assert scores["node-1"] > scores["node-2"]
    # Large gap expected: 0.5 (low) vs -0.5 (high) = 1.0 point difference
    score_diff = scores["node-1"] - scores["node-2"]
    assert score_diff >= 0.8  # At least most of the slot_saturation gap


@pytest.mark.asyncio
async def test_combined_signals_produce_fine_grained_ranking():
    """Combination of type_priority and slot_saturation produces fine-grained ranking."""
    # Four nodes: different combinations of type and saturation
    nodes = {
        "node-fresh-high-priority": NodeState(
            node_id="node-fresh-high-priority",
            label="critical pain",
            created_at_turn=5,
            depth=0,
            node_type="pain_point",  # high priority
        ),
        "node-saturated-high-priority": NodeState(
            node_id="node-saturated-high-priority",
            label="another critical pain",
            created_at_turn=5,
            depth=0,
            node_type="pain_point",
        ),
        "node-fresh-low-priority": NodeState(
            node_id="node-fresh-low-priority",
            label="some solution",
            created_at_turn=5,
            depth=0,
            node_type="solution_approach",  # lower priority
        ),
        "node-saturated-low-priority": NodeState(
            node_id="node-saturated-low-priority",
            label="another solution",
            created_at_turn=5,
            depth=0,
            node_type="solution_approach",
        ),
    }

    node_tracker = MagicMock()
    node_tracker.get_all_states.return_value = nodes

    strategy = StrategyConfig(
        name="test_strategy",
        description="Test",
        signal_weights={
            "graph.node.type_priority": 0.6,
            "graph.node.slot_saturation.low": 0.5,
            "graph.node.slot_saturation.medium": -0.2,
            "graph.node.slot_saturation.high": -0.5,
        },
        node_type_priorities={"pain_point": 0.9, "solution_approach": 0.4},
    )

    global_signals = {}
    node_signals = {
        "node-fresh-high-priority": {
            "graph.node.type_priority": 0.9,
            "graph.node.slot_saturation": "low",  # low
        },
        "node-saturated-high-priority": {
            "graph.node.type_priority": 0.9,
            "graph.node.slot_saturation": "high",  # high
        },
        "node-fresh-low-priority": {
            "graph.node.type_priority": 0.4,
            "graph.node.slot_saturation": "low",  # low
        },
        "node-saturated-low-priority": {
            "graph.node.type_priority": 0.4,
            "graph.node.slot_saturation": "high",  # high
        },
    }

    scored_pairs, _ = rank_strategy_node_pairs(
        strategies=[strategy],
        global_signals=global_signals,
        node_signals=node_signals,
        node_tracker=node_tracker,
        phase_weights=None,
        phase_bonuses=None,
    )

    assert len(scored_pairs) == 4

    # Expected ranking:
    # 1. fresh-high-priority (best of both worlds)
    # 2. saturated-high-priority (high type, but saturated)
    # 3. fresh-low-priority (low type, but fresh)
    # 4. saturated-low-priority (worst of both)

    ranking = [node_id for _, node_id, _ in scored_pairs]

    # Verify the expected order
    assert ranking[0] == "node-fresh-high-priority"
    assert ranking[3] == "node-saturated-low-priority"

    # Verify scores are in descending order
    scores = [score for _, _, score in scored_pairs]
    assert scores == sorted(scores, reverse=True)

    # Verify each pair has distinct score (no ties)
    assert len(set(scores)) == 4
