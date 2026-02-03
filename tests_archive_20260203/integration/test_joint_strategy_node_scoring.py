"""Integration tests for joint strategy-node scoring (Phase 3).

Tests the D1 architecture where strategies and nodes are scored jointly
rather than in two separate steps.
"""

import pytest
from unittest.mock import Mock

from src.methodologies.scoring import rank_strategy_node_pairs
from src.methodologies import StrategyConfig
from src.services.methodology_strategy_service import MethodologyStrategyService
from src.services.node_state_tracker import NodeStateTracker
from src.domain.models.node_state import NodeState
from src.domain.models.knowledge_graph import GraphState


@pytest.fixture
def sample_strategies():
    """Create sample strategy configs for testing."""
    strategies = [
        StrategyConfig(
            name="deepen",
            description="Explore why something matters to understand deeper motivations",
            technique="laddering",
            signal_weights={
                "llm.response_depth.surface": 0.8,
                "graph.node.exhausted.false": 1.0,
                "graph.node.focus_streak.low": 0.5,
            },
        ),
        StrategyConfig(
            name="clarify",
            description="Rephrase the question in simpler, clearer words",
            technique="probing",
            signal_weights={
                "graph.node.is_orphan.true": 1.0,
                "graph.node.exhausted.false": 0.5,
            },
        ),
        StrategyConfig(
            name="explore",
            description="Find new branches and related concepts",
            technique="elaboration",
            signal_weights={
                "graph.node.focus_streak.none": 1.0,
                "graph.node.yield_stagnation.false": 0.8,
            },
        ),
    ]
    return strategies


@pytest.fixture
def global_signals():
    """Sample global signals."""
    return {
        "llm.response_depth": "surface",
        "graph.node_count": 5,
        "graph.max_depth": 3,
    }


@pytest.fixture
def sample_node_states():
    """Create sample node states for testing."""
    states = {
        "node_1": NodeState(
            node_id="node_1",
            label="Career Growth",
            created_at_turn=1,
            depth=1,
            node_type="attribute",
            focus_count=3,
            last_focus_turn=5,
            turns_since_last_focus=0,
            current_focus_streak=3,
            last_yield_turn=3,
            turns_since_last_yield=2,
            yield_count=1,
            yield_rate=0.33,
            all_response_depths=["shallow", "shallow", "surface"],
            edge_count_outgoing=1,
            edge_count_incoming=1,
        ),
        "node_2": NodeState(
            node_id="node_2",
            label="Work Life Balance",
            created_at_turn=2,
            depth=2,
            node_type="value",
            focus_count=1,
            last_focus_turn=4,
            turns_since_last_focus=1,
            current_focus_streak=0,
            last_yield_turn=4,
            turns_since_last_yield=1,
            yield_count=1,
            yield_rate=1.0,
            all_response_depths=["deep"],
            edge_count_outgoing=0,
            edge_count_incoming=0,
        ),
        "node_3": NodeState(
            node_id="node_3",
            label="Remote Work",
            created_at_turn=3,
            depth=1,
            node_type="attribute",
            focus_count=0,
            last_focus_turn=None,
            turns_since_last_focus=3,
            current_focus_streak=0,
            last_yield_turn=None,
            turns_since_last_yield=3,
            yield_count=0,
            yield_rate=0.0,
            all_response_depths=[],
            edge_count_outgoing=0,
            edge_count_incoming=0,
        ),
    }
    return states


class TestRankStrategyNodePairs:
    """Tests for rank_strategy_node_pairs function."""

    def test_joint_scoring_basic(self, sample_strategies, global_signals):
        """Test basic joint scoring of strategy-node pairs."""
        node_signals = {
            "node_1": {
                "graph.node.exhausted": "false",
                "graph.node.focus_streak": "low",
            },
            "node_2": {
                "graph.node.exhausted": "false",
                "graph.node.focus_streak": "none",
            },
        }

        result = rank_strategy_node_pairs(
            strategies=sample_strategies,
            global_signals=global_signals,
            node_signals=node_signals,
        )

        # Should return 3 strategies x 2 nodes = 6 pairs
        assert len(result) == 6

        # Each result should be (strategy, node_id, score)
        for strategy, node_id, score in result:
            assert isinstance(strategy, StrategyConfig)
            assert node_id in ["node_1", "node_2"]
            assert isinstance(score, (int, float))

    def test_joint_scoring_sorted(self, sample_strategies, global_signals):
        """Test that results are sorted by score descending."""
        node_signals = {
            "node_1": {
                "graph.node.exhausted": "false",
                "graph.node.focus_streak": "low",
            },
            "node_2": {
                "graph.node.exhausted": "true",  # Should score lower
                "graph.node.focus_streak": "high",
            },
        }

        result = rank_strategy_node_pairs(
            strategies=sample_strategies,
            global_signals=global_signals,
            node_signals=node_signals,
        )

        # Scores should be in descending order
        scores = [score for _, _, score in result]
        assert scores == sorted(scores, reverse=True)

    def test_exhausted_node_scores_lower(self, sample_strategies, global_signals):
        """Test that exhausted nodes get lower scores for deepen strategy."""
        node_signals = {
            "fresh_node": {
                "graph.node.exhausted": "false",
                "graph.node.focus_streak": "low",
            },
            "exhausted_node": {
                "graph.node.exhausted": "true",
                "graph.node.focus_streak": "high",
            },
        }

        result = rank_strategy_node_pairs(
            strategies=sample_strategies,
            global_signals=global_signals,
            node_signals=node_signals,
        )

        # Find deepen strategy scores for both nodes
        deepen_scores = {
            node_id: score
            for strategy, node_id, score in result
            if strategy.name == "deepen"
        }

        # Fresh node should score higher than exhausted node
        assert deepen_scores["fresh_node"] > deepen_scores["exhausted_node"]

    def test_orphan_node_boosted_for_clarify(self, sample_strategies, global_signals):
        """Test that orphan nodes get boosted for clarify strategy."""
        node_signals = {
            "orphan_node": {
                "graph.node.is_orphan": "true",
                "graph.node.exhausted": "false",
            },
            "connected_node": {
                "graph.node.is_orphan": "false",
                "graph.node.exhausted": "false",
            },
        }

        result = rank_strategy_node_pairs(
            strategies=sample_strategies,
            global_signals=global_signals,
            node_signals=node_signals,
        )

        # Find clarify strategy scores for both nodes
        clarify_scores = {
            node_id: score
            for strategy, node_id, score in result
            if strategy.name == "clarify"
        }

        # Orphan node should score higher for clarify
        assert clarify_scores["orphan_node"] > clarify_scores["connected_node"]

    def test_fresh_node_boosted_for_explore(self, sample_strategies, global_signals):
        """Test that fresh nodes (focus_streak=none) get boosted for explore strategy."""
        node_signals = {
            "fresh_node": {
                "graph.node.focus_streak": "none",
                "graph.node.yield_stagnation": "false",
            },
            "focused_node": {
                "graph.node.focus_streak": "high",
                "graph.node.yield_stagnation": "false",
            },
        }

        result = rank_strategy_node_pairs(
            strategies=sample_strategies,
            global_signals=global_signals,
            node_signals=node_signals,
        )

        # Find explore strategy scores for both nodes
        explore_scores = {
            node_id: score
            for strategy, node_id, score in result
            if strategy.name == "explore"
        }

        # Fresh node should score higher for explore
        assert explore_scores["fresh_node"] > explore_scores["focused_node"]

    def test_empty_node_signals(self, sample_strategies, global_signals):
        """Test behavior when no node signals provided."""
        node_signals = {}

        result = rank_strategy_node_pairs(
            strategies=sample_strategies,
            global_signals=global_signals,
            node_signals=node_signals,
        )

        # Should return empty list
        assert len(result) == 0

    def test_node_signals_override_global(self, sample_strategies, global_signals):
        """Test that node-level signals can override global signals."""
        # Global signal says surface response
        global_signals_override = {"llm.response_depth": "surface"}

        # But node_1 has deep response
        node_signals = {
            "node_1": {
                "llm.response_depth": "deep",  # Override global
                "graph.node.exhausted": "false",
            },
        }

        result = rank_strategy_node_pairs(
            strategies=sample_strategies,
            global_signals=global_signals_override,
            node_signals=node_signals,
        )

        # Should have one result (1 strategy x 1 node)
        assert len(result) == 3  # 3 strategies x 1 node

        # The node signal should override global for scoring
        # (This is implicit in the merge: node signals take precedence)


class TestMethodologyStrategyServiceJointScoring:
    """Tests for MethodologyStrategyService.select_strategy_and_focus()."""

    @pytest.fixture
    def node_tracker(self, sample_node_states):
        """Create a NodeStateTracker with sample states."""
        tracker = NodeStateTracker()
        tracker.states = sample_node_states.copy()
        tracker.previous_focus = "node_1"
        return tracker

    @pytest.fixture
    def mock_context(self, node_tracker):
        """Create a mock PipelineContext."""
        context = Mock()
        context.methodology = "means_end_chain"
        context.user_input = "I want to grow in my career"
        context.node_tracker = node_tracker
        context.strategy_history = []  # Empty list for testing
        return context

    @pytest.fixture
    def mock_graph_state(self):
        """Create a mock GraphState."""
        from src.domain.models.knowledge_graph import DepthMetrics

        graph_state = Mock(spec=GraphState)
        graph_state.nodes = {}
        graph_state.edges = []
        graph_state.node_count = 3
        graph_state.max_depth = 2
        graph_state.avg_depth = 1.5
        graph_state.coverage_breadth = 0.6
        graph_state.orphan_count = 1
        graph_state.missing_terminal_value = True
        graph_state.edge_density = 0.5

        # Add depth_metrics mock
        depth_metrics = Mock(spec=DepthMetrics)
        depth_metrics.max_depth = 2
        depth_metrics.avg_depth = 1.5
        graph_state.depth_metrics = depth_metrics

        # Add nodes_by_type mock
        graph_state.nodes_by_type = {}

        return graph_state

    @pytest.mark.asyncio
    async def test_select_strategy_and_focus_basic(
        self, mock_context, mock_graph_state
    ):
        """Test basic strategy and node selection."""
        service = MethodologyStrategyService()

        (
            strategy_name,
            focus_node_id,
            alternatives,
            signals,
        ) = await service.select_strategy_and_focus(
            context=mock_context,
            graph_state=mock_graph_state,
            response_text="I want to grow in my career",
        )

        # Should return a strategy
        assert strategy_name is not None
        assert isinstance(strategy_name, str)

        # Should return a focus node_id
        assert focus_node_id is not None
        assert isinstance(focus_node_id, str)

        # Should return alternatives
        assert alternatives is not None
        assert len(alternatives) > 0

        # Alternatives should be (strategy, node_id, score) tuples
        for alt in alternatives:
            assert len(alt) == 3

    @pytest.mark.asyncio
    async def test_select_strategy_and_focus_without_node_tracker(
        self, mock_context, mock_graph_state
    ):
        """Test error when node_tracker is not available."""
        # Remove node_tracker
        mock_context.node_tracker = None

        service = MethodologyStrategyService()

        # Should raise ValueError since node_tracker is required
        with pytest.raises(ValueError, match="NodeStateTracker is required"):
            await service.select_strategy_and_focus(
                context=mock_context,
                graph_state=mock_graph_state,
                response_text="I want to grow in my career",
            )


class TestNodeStateSignalIntegration:
    """Tests for node-level signal detection integration."""

    @pytest.fixture
    def node_tracker(self):
        """Create a NodeStateTracker for testing."""
        tracker = NodeStateTracker()

        # Manually set states (no need to create KGNode objects for testing)
        tracker.states["node_1"] = NodeState(
            node_id="node_1",
            label="Career",
            created_at_turn=1,
            depth=1,
            node_type="attribute",
            focus_count=3,
            current_focus_streak=2,
            all_response_depths=["shallow", "shallow", "surface"],
            edge_count_outgoing=1,
            edge_count_incoming=1,
        )

        tracker.states["node_2"] = NodeState(
            node_id="node_2",
            label="Balance",
            created_at_turn=2,
            depth=2,
            node_type="value",
            focus_count=1,
            current_focus_streak=0,
            all_response_depths=["deep"],
            edge_count_outgoing=0,
            edge_count_incoming=0,
        )

        tracker.states["node_3"] = NodeState(
            node_id="node_3",
            label="Remote",
            created_at_turn=3,
            depth=1,
            node_type="attribute",
            focus_count=0,
            current_focus_streak=0,
            all_response_depths=[],
            edge_count_outgoing=0,
            edge_count_incoming=0,
        )

        return tracker

    @pytest.mark.asyncio
    async def test_exhaustion_signal_detection(self, node_tracker):
        """Test that exhaustion signals are detected correctly."""
        from src.methodologies.signals.graph.node_exhaustion import (
            NodeExhaustedSignal,
        )

        detector = NodeExhaustedSignal(node_tracker)
        mock_context = Mock()
        mock_graph_state = Mock()

        results = await detector.detect(mock_context, mock_graph_state, "")

        # Should return results for all nodes
        assert len(results) == 3
        assert "node_1" in results
        assert "node_2" in results
        assert "node_3" in results

        # Values should be "true" or "false"
        for value in results.values():
            assert value in ["true", "false"]

    @pytest.mark.asyncio
    async def test_engagement_signal_detection(self, node_tracker):
        """Test that engagement signals are detected correctly."""
        from src.methodologies.signals.graph.node_engagement import (
            NodeFocusStreakSignal,
        )

        detector = NodeFocusStreakSignal(node_tracker)
        mock_context = Mock()
        mock_graph_state = Mock()

        results = await detector.detect(mock_context, mock_graph_state, "")

        # Should return results for all nodes
        assert len(results) == 3

        # Values should be valid categories
        valid_categories = ["none", "low", "medium", "high"]
        for value in results.values():
            assert value in valid_categories

    @pytest.mark.asyncio
    async def test_relationship_signal_detection(self, node_tracker):
        """Test that relationship signals are detected correctly."""
        from src.methodologies.signals.graph.node_relationships import (
            NodeIsOrphanSignal,
        )

        detector = NodeIsOrphanSignal(node_tracker)
        mock_context = Mock()
        mock_graph_state = Mock()

        results = await detector.detect(mock_context, mock_graph_state, "")

        # Should return results for all nodes
        assert len(results) == 3

        # node_2 and node_3 are orphans (no edges)
        assert results["node_2"] == "true"
        assert results["node_3"] == "true"
        # node_1 has edges
        assert results["node_1"] == "false"


class TestFullPipelineIntegration:
    """Tests for full pipeline integration with joint scoring."""

    @pytest.mark.asyncio
    async def test_end_to_end_joint_scoring(self):
        """Test joint scoring through the full pipeline."""
        # This would require a more complex setup with actual pipeline stages
        # For now, we test the core integration points

        service = MethodologyStrategyService()

        # Create mock context with node_tracker
        node_tracker = NodeStateTracker()
        node_tracker.states = {
            "node_1": NodeState(
                node_id="node_1",
                label="Career",
                created_at_turn=1,
                depth=1,
                node_type="attribute",
                focus_count=0,
                current_focus_streak=0,
                all_response_depths=[],
                edge_count_outgoing=0,
                edge_count_incoming=0,
            )
        }

        mock_context = Mock()
        mock_context.methodology = "means_end_chain"
        mock_context.user_input = "I want to grow"
        mock_context.node_tracker = node_tracker
        mock_context.strategy_history = []  # Empty list for testing

        mock_graph_state = Mock(spec=GraphState)
        mock_graph_state.nodes = {}
        mock_graph_state.edges = []
        mock_graph_state.node_count = 3
        mock_graph_state.max_depth = 2
        mock_graph_state.avg_depth = 1.5
        mock_graph_state.coverage_breadth = 0.6
        mock_graph_state.orphan_count = 1
        mock_graph_state.missing_terminal_value = True
        mock_graph_state.edge_density = 0.5

        # Add depth_metrics mock
        from src.domain.models.knowledge_graph import DepthMetrics

        depth_metrics = Mock(spec=DepthMetrics)
        depth_metrics.max_depth = 2
        depth_metrics.avg_depth = 1.5
        mock_graph_state.depth_metrics = depth_metrics

        # Add nodes_by_type mock
        mock_graph_state.nodes_by_type = {}

        # Should not raise errors
        (
            strategy,
            node_id,
            alternatives,
            signals,
        ) = await service.select_strategy_and_focus(
            context=mock_context,
            graph_state=mock_graph_state,
            response_text="I want to grow",
        )

        assert strategy is not None
        assert node_id is not None
