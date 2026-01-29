"""Unit tests for node-level signal detectors.

Tests cover:
- Exhaustion signals (exhausted, exhaustion_score, yield_stagnation)
- Engagement signals (focus_streak, is_current_focus, recency_score)
- Relationship signals (is_orphan, edge_count, has_outgoing)
- Strategy repetition signals
- Edge cases (empty tracker, multiple nodes)
"""

import pytest

from src.domain.models.node_state import NodeState
from src.services.node_state_tracker import NodeStateTracker
from src.methodologies.signals.graph.node_exhaustion import (
    NodeExhaustedSignal,
    NodeExhaustionScoreSignal,
    NodeYieldStagnationSignal,
)
from src.methodologies.signals.graph.node_engagement import (
    NodeFocusStreakSignal,
    NodeIsCurrentFocusSignal,
    NodeRecencyScoreSignal,
)
from src.methodologies.signals.graph.node_relationships import (
    NodeIsOrphanSignal,
    NodeEdgeCountSignal,
    NodeHasOutgoingSignal,
)
from src.methodologies.signals.technique.node_strategy_repetition import (
    NodeStrategyRepetitionSignal,
)


@pytest.fixture
def node_tracker():
    """Create a NodeStateTracker for testing."""
    return NodeStateTracker()


@pytest.fixture
def populated_tracker(node_tracker):
    """Create a NodeStateTracker with multiple test nodes."""
    # Node 1: Fresh node (just created)
    node_tracker.states["node1"] = NodeState(
        node_id="node1",
        label="Fresh Node",
        created_at_turn=10,
        depth=0,
    )

    # Node 2: Exhausted node (no yield, shallow responses, high streak)
    node_tracker.states["node2"] = NodeState(
        node_id="node2",
        label="Exhausted Node",
        created_at_turn=1,
        depth=1,
        focus_count=5,
        last_focus_turn=10,
        turns_since_last_focus=0,
        current_focus_streak=3,
        last_yield_turn=5,
        turns_since_last_yield=5,
        yield_count=1,
        yield_rate=0.2,
        all_response_depths=["deep", "shallow", "shallow", "surface", "shallow"],
        edge_count_outgoing=1,
        edge_count_incoming=1,
    )

    # Node 3: Active node (recent yield, deep responses)
    node_tracker.states["node3"] = NodeState(
        node_id="node3",
        label="Active Node",
        created_at_turn=2,
        depth=2,
        focus_count=3,
        last_focus_turn=10,
        turns_since_last_focus=0,
        current_focus_streak=1,
        last_yield_turn=9,
        turns_since_last_yield=1,
        yield_count=2,
        yield_rate=0.67,
        all_response_depths=["deep", "deep", "deep"],
    )

    # Node 4: Orphan node (no edges)
    node_tracker.states["node4"] = NodeState(
        node_id="node4",
        label="Orphan Node",
        created_at_turn=5,
        depth=0,
        focus_count=1,
        last_focus_turn=5,
        turns_since_last_focus=5,
        current_focus_streak=0,
        edge_count_outgoing=0,
        edge_count_incoming=0,
    )

    # Node 5: Connected node (has edges)
    node_tracker.states["node5"] = NodeState(
        node_id="node5",
        label="Connected Node",
        created_at_turn=3,
        depth=1,
        focus_count=2,
        last_focus_turn=8,
        turns_since_last_focus=2,
        current_focus_streak=0,
        edge_count_outgoing=2,
        edge_count_incoming=1,
    )

    # Node 6: High strategy repetition
    node_tracker.states["node6"] = NodeState(
        node_id="node6",
        label="Repeated Strategy Node",
        created_at_turn=1,
        depth=0,
        focus_count=6,
        last_focus_turn=10,
        turns_since_last_focus=0,
        current_focus_streak=6,
        strategy_usage_count={"explore": 6},
        last_strategy_used="explore",
        consecutive_same_strategy=6,
    )

    # Set current focus
    node_tracker.previous_focus = "node2"

    return node_tracker


class TestNodeExhaustedSignal:
    """Tests for NodeExhaustedSignal."""

    @pytest.mark.asyncio
    async def test_exhausted_node_detected(self, populated_tracker):
        """Test that exhausted node is correctly identified."""
        detector = NodeExhaustedSignal(populated_tracker)
        result = await detector.detect(None, None, "")

        assert result["node2"] == "true"  # Exhausted
        assert result["node1"] == "false"  # Never focused
        assert result["node3"] == "false"  # Recent yield

    @pytest.mark.asyncio
    async def test_exhaustion_criteria(self, node_tracker):
        """Test exhaustion criteria combinations."""
        detector = NodeExhaustedSignal(node_tracker)

        # Test: No focus count
        node_tracker.states["test"] = NodeState(
            node_id="test",
            label="Test",
            created_at_turn=1,
            depth=0,
            turns_since_last_yield=5,
            current_focus_streak=3,
        )
        result = await detector.detect(None, None, "")
        assert result["test"] == "false"

        # Test: Low turns since yield
        node_tracker.states["test2"] = NodeState(
            node_id="test2",
            label="Test2",
            created_at_turn=1,
            depth=0,
            focus_count=1,
            turns_since_last_yield=1,
            current_focus_streak=3,
            all_response_depths=["shallow", "shallow", "shallow"],
        )
        result = await detector.detect(None, None, "")
        assert result["test2"] == "false"

    @pytest.mark.asyncio
    async def test_empty_tracker(self, node_tracker):
        """Test with empty NodeStateTracker."""
        detector = NodeExhaustedSignal(node_tracker)
        result = await detector.detect(None, None, "")
        assert result == {}


class TestNodeExhaustionScoreSignal:
    """Tests for NodeExhaustionScoreSignal."""

    @pytest.mark.asyncio
    async def test_exhaustion_score_calculation(self, populated_tracker):
        """Test exhaustion score calculation."""
        detector = NodeExhaustionScoreSignal(populated_tracker)
        result = await detector.detect(None, None, "")

        # Fresh node should have score 0.0
        assert result["node1"] == 0.0

        # Exhausted node should have high score
        assert result["node2"] > 0.5

        # Active node should have low score
        assert result["node3"] < 0.5

    @pytest.mark.asyncio
    async def test_score_components(self, node_tracker):
        """Test that score components are weighted correctly."""
        detector = NodeExhaustionScoreSignal(node_tracker)

        # Create node with only turns factor
        node_tracker.states["test"] = NodeState(
            node_id="test",
            label="Test",
            created_at_turn=1,
            depth=0,
            focus_count=1,
            turns_since_last_yield=10,
            current_focus_streak=0,
        )
        result = await detector.detect(None, None, "")
        # Turns max at 0.4
        assert 0.35 <= result["test"] <= 0.45

    @pytest.mark.asyncio
    async def test_empty_tracker(self, node_tracker):
        """Test with empty NodeStateTracker."""
        detector = NodeExhaustionScoreSignal(node_tracker)
        result = await detector.detect(None, None, "")
        assert result == {}


class TestNodeYieldStagnationSignal:
    """Tests for NodeYieldStagnationSignal."""

    @pytest.mark.asyncio
    async def test_yield_stagnation_detection(self, populated_tracker):
        """Test yield stagnation detection."""
        detector = NodeYieldStagnationSignal(populated_tracker)
        result = await detector.detect(None, None, "")

        # Node2 has 5 turns since yield
        assert result["node2"] == "true"

        # Node3 has 1 turn since yield
        assert result["node3"] == "false"

        # Node1 never focused
        assert result["node1"] == "false"

    @pytest.mark.asyncio
    async def test_threshold(self, node_tracker):
        """Test 3-turn threshold."""
        detector = NodeYieldStagnationSignal(node_tracker)

        # Exactly 3 turns - should be true
        node_tracker.states["test"] = NodeState(
            node_id="test",
            label="Test",
            created_at_turn=1,
            depth=0,
            focus_count=1,
            turns_since_last_yield=3,
        )
        result = await detector.detect(None, None, "")
        assert result["test"] == "true"

        # 2 turns - should be false
        node_tracker.states["test2"] = NodeState(
            node_id="test2",
            label="Test2",
            created_at_turn=1,
            depth=0,
            focus_count=1,
            turns_since_last_yield=2,
        )
        result = await detector.detect(None, None, "")
        assert result["test2"] == "false"


class TestNodeFocusStreakSignal:
    """Tests for NodeFocusStreakSignal."""

    @pytest.mark.asyncio
    async def test_streak_categorization(self, populated_tracker):
        """Test focus streak categorization."""
        detector = NodeFocusStreakSignal(populated_tracker)
        result = await detector.detect(None, None, "")

        # Node1: never focused
        assert result["node1"] == "none"

        # Node2: streak of 3
        assert result["node2"] == "medium"

        # Node3: streak of 1
        assert result["node3"] == "low"

        # Node6: streak of 6
        assert result["node6"] == "high"


class TestNodeIsCurrentFocusSignal:
    """Tests for NodeIsCurrentFocusSignal."""

    @pytest.mark.asyncio
    async def test_current_focus_detection(self, populated_tracker):
        """Test current focus detection."""
        detector = NodeIsCurrentFocusSignal(populated_tracker)
        result = await detector.detect(None, None, "")

        # Node2 is current focus
        assert result["node2"] == "true"

        # All others are not
        assert result["node1"] == "false"
        assert result["node3"] == "false"
        assert result["node4"] == "false"
        assert result["node5"] == "false"
        assert result["node6"] == "false"


class TestNodeRecencyScoreSignal:
    """Tests for NodeRecencyScoreSignal."""

    @pytest.mark.asyncio
    async def test_recency_score_calculation(self, populated_tracker):
        """Test recency score calculation."""
        detector = NodeRecencyScoreSignal(populated_tracker)
        result = await detector.detect(None, None, "")

        # Node2: focused this turn
        assert result["node2"] == 1.0

        # Node5: focused 2 turns ago
        assert 0.85 <= result["node5"] <= 0.95

        # Node4: focused 5 turns ago
        assert 0.70 <= result["node4"] <= 0.80

        # Node1: never focused
        assert result["node1"] == 0.0

    @pytest.mark.asyncio
    async def test_recency_decay(self, node_tracker):
        """Test that recency decays over 20 turns."""
        detector = NodeRecencyScoreSignal(node_tracker)

        # Create node focused 20 turns ago
        node_tracker.states["test"] = NodeState(
            node_id="test",
            label="Test",
            created_at_turn=1,
            depth=0,
            last_focus_turn=1,
            turns_since_last_focus=20,
        )
        result = await detector.detect(None, None, "")
        assert result["test"] == 0.0

        # Create node focused 10 turns ago
        node_tracker.states["test2"] = NodeState(
            node_id="test2",
            label="Test2",
            created_at_turn=1,
            depth=0,
            last_focus_turn=1,
            turns_since_last_focus=10,
        )
        result = await detector.detect(None, None, "")
        assert result["test2"] == 0.5


class TestNodeIsOrphanSignal:
    """Tests for NodeIsOrphanSignal."""

    @pytest.mark.asyncio
    async def test_orphan_detection(self, populated_tracker):
        """Test orphan detection."""
        detector = NodeIsOrphanSignal(populated_tracker)
        result = await detector.detect(None, None, "")

        # Node4 has no edges
        assert result["node4"] == "true"

        # Node5 has edges
        assert result["node5"] == "false"


class TestNodeEdgeCountSignal:
    """Tests for NodeEdgeCountSignal."""

    @pytest.mark.asyncio
    async def test_edge_count_calculation(self, populated_tracker):
        """Test edge count calculation."""
        detector = NodeEdgeCountSignal(populated_tracker)
        result = await detector.detect(None, None, "")

        # Node4: 0 edges
        assert result["node4"] == 0

        # Node5: 3 edges (2 outgoing + 1 incoming)
        assert result["node5"] == 3


class TestNodeHasOutgoingSignal:
    """Tests for NodeHasOutgoingSignal."""

    @pytest.mark.asyncio
    async def test_outgoing_detection(self, populated_tracker):
        """Test outgoing edge detection."""
        detector = NodeHasOutgoingSignal(populated_tracker)
        result = await detector.detect(None, None, "")

        # Node4 has no outgoing edges
        assert result["node4"] == "false"

        # Node5 has outgoing edges
        assert result["node5"] == "true"


class TestNodeStrategyRepetitionSignal:
    """Tests for NodeStrategyRepetitionSignal."""

    @pytest.mark.asyncio
    async def test_repetition_categorization(self, populated_tracker):
        """Test strategy repetition categorization."""
        detector = NodeStrategyRepetitionSignal(populated_tracker)
        result = await detector.detect(None, None, "")

        # Node1: never focused
        assert result["node1"] == "none"

        # Node6: 6 consecutive uses
        assert result["node6"] == "high"

        # Node2: strategy not set (0 consecutive)
        assert result["node2"] == "none"

    @pytest.mark.asyncio
    async def test_repetition_thresholds(self, node_tracker):
        """Test repetition thresholds."""
        detector = NodeStrategyRepetitionSignal(node_tracker)

        # Low: 1-2 consecutive
        for i in range(1, 3):
            node_tracker.states[f"test{i}"] = NodeState(
                node_id=f"test{i}",
                label=f"Test{i}",
                created_at_turn=1,
                depth=0,
                consecutive_same_strategy=i,
            )

        result = await detector.detect(None, None, "")
        assert result["test1"] == "low"
        assert result["test2"] == "low"

        # Medium: 3-4 consecutive
        for i in range(3, 5):
            node_tracker.states[f"test{i}"] = NodeState(
                node_id=f"test{i}",
                label=f"Test{i}",
                created_at_turn=1,
                depth=0,
                consecutive_same_strategy=i,
            )

        result = await detector.detect(None, None, "")
        assert result["test3"] == "medium"
        assert result["test4"] == "medium"


class TestSignalIntegration:
    """Integration tests for multiple signals."""

    @pytest.mark.asyncio
    async def test_multiple_signals_together(self, populated_tracker):
        """Test that multiple signals work together correctly."""
        exhausted_detector = NodeExhaustedSignal(populated_tracker)
        recency_detector = NodeRecencyScoreSignal(populated_tracker)
        orphan_detector = NodeIsOrphanSignal(populated_tracker)

        exhausted = await exhausted_detector.detect(None, None, "")
        recency = await recency_detector.detect(None, None, "")
        orphan = await orphan_detector.detect(None, None, "")

        # Node2 is exhausted and recent but not orphan
        assert exhausted["node2"] == "true"
        assert recency["node2"] == 1.0
        assert orphan["node2"] == "false"

        # Node4 is orphan but not exhausted
        assert exhausted["node4"] == "false"
        assert orphan["node4"] == "true"

    @pytest.mark.asyncio
    async def test_signal_consistency(self, populated_tracker):
        """Test that signals are consistent across multiple calls."""
        detector = NodeExhaustedSignal(populated_tracker)

        result1 = await detector.detect(None, None, "")
        result2 = await detector.detect(None, None, "")

        # Results should be identical
        assert result1 == result2
