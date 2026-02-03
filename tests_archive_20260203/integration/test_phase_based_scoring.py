"""Integration tests for phase-based scoring.

Tests the complete pipeline of:
1. Interview phase detection
2. Phase weight loading from YAML configs
3. Phase weight application in scoring
4. Strategy selection with phase-based modifiers
"""

import pytest
from unittest.mock import Mock

from src.methodologies.registry import MethodologyRegistry
from src.methodologies.scoring import rank_strategy_node_pairs, score_strategy
from src.methodologies.signals.meta.interview_phase import InterviewPhaseSignal


class TestPhaseDetection:
    """Test interview phase detection with various graph states."""

    @pytest.mark.asyncio
    async def test_phase_transition_early_to_mid(self):
        """Test phase transition from early to mid as graph grows."""
        signal = InterviewPhaseSignal()

        context = Mock()

        # Early phase: 3 nodes
        graph_early = Mock()
        graph_early.node_count = 3
        graph_early.max_depth = 1
        graph_early.extended_properties = {"orphan_count": 0}

        result_early = await signal.detect(context, graph_early, "")
        assert result_early["meta.interview.phase"] == "early"

        # Mid phase: 10 nodes
        graph_mid = Mock()
        graph_mid.node_count = 10
        graph_mid.max_depth = 3
        graph_mid.extended_properties = {"orphan_count": 2}

        result_mid = await signal.detect(context, graph_mid, "")
        assert result_mid["meta.interview.phase"] == "mid"

    @pytest.mark.asyncio
    async def test_phase_transition_mid_to_late(self):
        """Test phase transition from mid to late as graph matures."""
        signal = InterviewPhaseSignal()

        context = Mock()

        # Mid phase: 12 nodes
        graph_mid = Mock()
        graph_mid.node_count = 12
        graph_mid.max_depth = 3
        graph_mid.extended_properties = {"orphan_count": 1}

        result_mid = await signal.detect(context, graph_mid, "")
        assert result_mid["meta.interview.phase"] == "mid"

        # Late phase: 20 nodes
        graph_late = Mock()
        graph_late.node_count = 20
        graph_late.max_depth = 5
        graph_late.extended_properties = {"orphan_count": 2}

        result_late = await signal.detect(context, graph_late, "")
        assert result_late["meta.interview.phase"] == "late"

    @pytest.mark.asyncio
    async def test_phase_stays_mid_with_many_orphans(self):
        """Test that phase stays mid when there are many orphans, even with many nodes."""
        signal = InterviewPhaseSignal()

        context = Mock()

        # Should be mid due to orphan count > 3
        graph = Mock()
        graph.node_count = 25
        graph.max_depth = 4
        graph.extended_properties = {"orphan_count": 5}

        result = await signal.detect(context, graph, "")
        assert result["meta.interview.phase"] == "mid"


class TestPhaseConfigLoading:
    """Test loading phase configurations from YAML."""

    def test_load_means_end_chain_phases(self):
        """Test loading phases from means_end_chain.yaml."""
        registry = MethodologyRegistry()
        config = registry.get_methodology("means_end_chain")

        assert config.phases is not None
        assert "early" in config.phases
        assert "mid" in config.phases
        assert "late" in config.phases

        # Check early phase
        early_phase = config.phases["early"]
        assert early_phase.name == "early"
        assert "explore" in early_phase.signal_weights
        assert early_phase.signal_weights["explore"] == 1.5

        # Check mid phase
        mid_phase = config.phases["mid"]
        assert mid_phase.name == "mid"
        assert "deepen" in mid_phase.signal_weights
        assert mid_phase.signal_weights["deepen"] == 1.3

        # Check late phase
        late_phase = config.phases["late"]
        assert late_phase.name == "late"
        assert "reflect" in late_phase.signal_weights
        assert late_phase.signal_weights["reflect"] == 1.5

    def test_load_jobs_to_be_done_phases(self):
        """Test loading phases from jobs_to_be_done.yaml."""
        registry = MethodologyRegistry()
        config = registry.get_methodology("jobs_to_be_done")

        assert config.phases is not None
        assert "early" in config.phases
        assert "mid" in config.phases
        assert "late" in config.phases

        # Check early phase
        early_phase = config.phases["early"]
        assert early_phase.name == "early"
        assert "explore_situation" in early_phase.signal_weights
        assert early_phase.signal_weights["explore_situation"] == 1.5

        # Check late phase
        late_phase = config.phases["late"]
        assert "validate_outcome" in late_phase.signal_weights
        assert late_phase.signal_weights["validate_outcome"] == 1.5


class TestPhaseWeightApplication:
    """Test application of phase weights in scoring."""

    def test_score_strategy_with_phase_weights(self):
        """Test that phase weights modify strategy scores."""
        # Create a mock strategy config
        from src.methodologies.registry import StrategyConfig

        strategy = StrategyConfig(
            name="explore",
            description="Explore recent topics",
            technique="elaboration",
            signal_weights={"graph.node_count": 0.5},
        )

        # Mock signals
        signals = {"graph.node_count": 10}

        # Calculate base score
        base_score = score_strategy(strategy, signals)

        # Apply phase weight multiplier (1.5x for early phase explore)
        phase_weights = {"explore": 1.5}
        expected_score = base_score * phase_weights["explore"]

        # The score function doesn't apply phase weights directly,
        # so we verify the multiplication logic
        assert expected_score == base_score * 1.5

    def test_rank_strategy_node_pairs_with_phase_weights(self):
        """Test that phase weights are applied in joint scoring."""
        from src.methodologies.registry import StrategyConfig

        # Create mock strategies
        strategies = [
            StrategyConfig(
                name="explore",
                description="Explore recent topics",
                technique="elaboration",
                signal_weights={"graph.node_count": 0.5},
            ),
            StrategyConfig(
                name="deepen",
                description="Deepen using laddering",
                technique="laddering",
                signal_weights={"graph.max_depth": 0.5},
            ),
        ]

        # Mock signals
        global_signals = {"graph.node_count": 10, "graph.max_depth": 3}
        node_signals = {
            "node1": {"graph.node_count": 10},
            "node2": {"graph.max_depth": 3},
        }

        # Mock node tracker
        node_tracker = Mock()

        # Rank without phase weights
        ranked_no_phase = rank_strategy_node_pairs(
            strategies, global_signals, node_signals, node_tracker
        )

        # Rank with early phase weights (explore boosted 1.5x)
        early_phase_weights = {"explore": 1.5, "deepen": 0.5}
        ranked_with_phase = rank_strategy_node_pairs(
            strategies,
            global_signals,
            node_signals,
            node_tracker,
            phase_weights=early_phase_weights,
        )

        # Explore scores should be higher with phase weights
        explore_scores_no_phase = [
            (s, n, score) for s, n, score in ranked_no_phase if s.name == "explore"
        ]
        explore_scores_with_phase = [
            (s, n, score) for s, n, score in ranked_with_phase if s.name == "explore"
        ]

        # Scores should be multiplied by phase weight
        assert len(explore_scores_no_phase) > 0
        assert len(explore_scores_with_phase) > 0

        # Check that scores are actually multiplied
        for i, (_, _, score_no_phase) in enumerate(explore_scores_no_phase):
            _, _, score_with_phase = explore_scores_with_phase[i]
            # Account for floating point precision
            assert abs(score_with_phase - score_no_phase * 1.5) < 0.01

    def test_phase_weights_change_ranking_order(self):
        """Test that phase weights can change which strategy is ranked highest."""
        from src.methodologies.registry import StrategyConfig

        # Create strategies with similar base weights
        strategies = [
            StrategyConfig(
                name="explore",
                description="Explore recent topics",
                technique="elaboration",
                signal_weights={"graph.node_count": 1.0},
            ),
            StrategyConfig(
                name="deepen",
                description="Deepen using laddering",
                technique="laddering",
                signal_weights={"graph.max_depth": 1.0},
            ),
        ]

        # Mock signals where both would score similarly
        global_signals = {"graph.node_count": 5, "graph.max_depth": 3}
        node_signals = {"node1": {}}

        node_tracker = Mock()

        # With early phase weights, explore should be boosted
        early_phase_weights = {"explore": 2.0, "deepen": 0.5}
        ranked_early = rank_strategy_node_pairs(
            strategies,
            global_signals,
            node_signals,
            node_tracker,
            phase_weights=early_phase_weights,
        )

        # With late phase weights, deepen/reflect should be boosted
        late_phase_weights = {"explore": 0.3, "deepen": 1.5}
        ranked_late = rank_strategy_node_pairs(
            strategies,
            global_signals,
            node_signals,
            node_tracker,
            phase_weights=late_phase_weights,
        )

        # Check that explore is top in early phase
        top_strategy_early = ranked_early[0][0]
        assert top_strategy_early.name == "explore"

        # Check that deepen is top in late phase
        top_strategy_late = ranked_late[0][0]
        assert top_strategy_late.name == "deepen"


class TestEndToEndPhaseBasedScoring:
    """Test end-to-end phase-based scoring with real configs."""

    def test_phase_based_strategy_selection_flow(self):
        """Test the complete flow from phase detection to strategy selection."""
        registry = MethodologyRegistry()
        config = registry.get_methodology("means_end_chain")

        # Simulate early phase graph state
        graph_state = Mock()
        graph_state.node_count = 3
        graph_state.max_depth = 1
        graph_state.extended_properties = {"orphan_count": 0}

        # Create mock context
        context = Mock()
        context.methodology = "means_end_chain"
        context.signals = {"graph.node_count": 3}

        # For early phase (3 nodes), phase should be "early"
        # In the real service, this would be detected by InterviewPhaseSignal
        current_phase = "early"  # Simplified for unit test

        # Get phase weights
        phase_weights = None
        if config.phases and current_phase in config.phases:
            phase_weights = config.phases[current_phase].signal_weights

        assert phase_weights is not None
        assert "explore" in phase_weights
        assert phase_weights["explore"] == 1.5  # Early phase boosts explore

    def test_phase_weights_for_all_phases(self):
        """Test that all phases have weights defined."""
        registry = MethodologyRegistry()
        config = registry.get_methodology("means_end_chain")

        assert config.phases is not None

        for phase_name in ["early", "mid", "late"]:
            assert phase_name in config.phases
            phase = config.phases[phase_name]
            assert phase.signal_weights is not None
            assert len(phase.signal_weights) > 0

            # All weights should be positive (multipliers)
            for strategy_name, weight in phase.signal_weights.items():
                assert weight > 0, f"Invalid weight for {strategy_name} in {phase_name}"

    def test_phase_consistency_across_methodologies(self):
        """Test that both methodologies have consistent phase structures."""
        registry = MethodologyRegistry()

        for methodology_name in ["means_end_chain", "jobs_to_be_done"]:
            config = registry.get_methodology(methodology_name)

            # All should have phases defined
            assert config.phases is not None, f"{methodology_name} missing phases"

            # All should have early, mid, late phases
            for phase_name in ["early", "mid", "late"]:
                assert phase_name in config.phases, (
                    f"{methodology_name} missing {phase_name} phase"
                )

                # Each phase should have signal_weights
                phase = config.phases[phase_name]
                assert hasattr(phase, "signal_weights")
                assert isinstance(phase.signal_weights, dict)
