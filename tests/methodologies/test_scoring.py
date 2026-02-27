"""Tests for methodology scoring module."""

import pytest

from src.methodologies.scoring import (
    _get_signal_value,
    score_strategy,
    rank_strategies,
    rank_strategy_node_pairs,
    partition_signal_weights,
    rank_nodes_for_strategy,
    ScoredCandidate,
)
from src.methodologies.registry import StrategyConfig


class TestGetSignalValue:
    """Tests for _get_signal_value function."""

    def test_direct_match(self):
        """Test direct signal key match."""
        signals = {"graph.node_count": 10, "llm.response_depth": 4}
        assert _get_signal_value("graph.node_count", signals) == 10
        assert _get_signal_value("llm.response_depth", signals) == 4

    def test_direct_match_not_found(self):
        """Test direct match returns None when key not present."""
        signals = {"graph.node_count": 10}
        assert _get_signal_value("llm.response_depth", signals) is None

    def test_threshold_low_boundary(self):
        """Test low threshold matches values <= 0.25."""
        signals = {"llm.response_depth": 0.0}
        assert _get_signal_value("llm.response_depth.low", signals) is True

        signals = {"llm.response_depth": 0.25}
        assert _get_signal_value("llm.response_depth.low", signals) is True

    def test_threshold_low_non_match(self):
        """Test low threshold does not match values > 0.25."""
        signals = {"llm.response_depth": 0.5}
        assert _get_signal_value("llm.response_depth.low", signals) is False

        signals = {"llm.response_depth": 0.75}
        assert _get_signal_value("llm.response_depth.low", signals) is False

        signals = {"llm.response_depth": 1.0}
        assert _get_signal_value("llm.response_depth.low", signals) is False

    def test_threshold_mid_boundary(self):
        """Test mid threshold matches values in (0.25, 0.75)."""
        signals = {"llm.response_depth": 0.5}
        assert _get_signal_value("llm.response_depth.mid", signals) is True

    def test_threshold_mid_non_match(self):
        """Test mid threshold does not match boundary or extreme values."""
        for value in [0.0, 0.25, 0.75, 1.0]:
            signals = {"llm.response_depth": value}
            assert _get_signal_value("llm.response_depth.mid", signals) is False

    def test_threshold_high_boundary(self):
        """Test high threshold matches values >= 0.75."""
        signals = {"llm.response_depth": 0.75}
        assert _get_signal_value("llm.response_depth.high", signals) is True

        signals = {"llm.response_depth": 1.0}
        assert _get_signal_value("llm.response_depth.high", signals) is True

    def test_threshold_high_non_match(self):
        """Test high threshold does not match values < 0.75."""
        for value in [0.0, 0.25, 0.5]:
            signals = {"llm.response_depth": value}
            assert _get_signal_value("llm.response_depth.high", signals) is False

    def test_string_compound_key_match(self):
        """Test string-based compound keys still work."""
        signals = {"llm.global_response_trend": "fatigued"}
        assert _get_signal_value("llm.global_response_trend.fatigued", signals) is True

    def test_string_compound_key_no_match(self):
        """Test string compound key returns False when values differ."""
        signals = {"llm.global_response_trend": "engaged"}
        assert _get_signal_value("llm.global_response_trend.fatigued", signals) is False

    def test_deep_compound_key_float_threshold(self):
        """Test deeply nested compound keys with float threshold binning."""
        signals = {"graph.chain_completion.ratio": 0.5}
        # The compound key "graph.chain_completion.ratio.high" has base
        # "graph.chain_completion.ratio" which is a float (0.5),
        # threshold binning applies: 0.5 < 0.75 → not high → False
        result = _get_signal_value("graph.chain_completion.ratio.high", signals)
        assert result is False  # 0.5 < 0.75, not high

    def test_bool_compound_key_true_match(self):
        """Test Python bool True matches compound key .true."""
        signals = {"graph.node.is_orphan": True}
        assert _get_signal_value("graph.node.is_orphan.true", signals) is True

    def test_bool_compound_key_true_no_match(self):
        """Test Python bool False does not match compound key .true."""
        signals = {"graph.node.is_orphan": False}
        assert _get_signal_value("graph.node.is_orphan.true", signals) is False

    def test_bool_compound_key_false_match(self):
        """Test Python bool False matches compound key .false."""
        signals = {"graph.node.exhausted": False}
        assert _get_signal_value("graph.node.exhausted.false", signals) is True

    def test_bool_compound_key_false_no_match(self):
        """Test Python bool True does not match compound key .false."""
        signals = {"graph.node.exhausted": True}
        assert _get_signal_value("graph.node.exhausted.false", signals) is False

    def test_compound_key_base_not_found(self):
        """Test compound key returns None when base signal not present."""
        signals = {"graph.node_count": 10}
        assert _get_signal_value("llm.response_depth.low", signals) is None


class TestScoreStrategy:
    """Tests for score_strategy function."""

    def test_score_with_boolean_match(self):
        """Test scoring with boolean signal match."""
        strategy = StrategyConfig(
            name="test",
            description="Test strategy",
            signal_weights={"llm.response_depth.low": 0.8},
        )
        signals = {"llm.response_depth": 0.25}  # Normalized: low (<= 0.25)
        score = score_strategy(strategy, signals)
        assert score == 0.8

    def test_score_with_boolean_no_match(self):
        """Test scoring with boolean signal no match."""
        strategy = StrategyConfig(
            name="test",
            description="Test strategy",
            signal_weights={"llm.response_depth.low": 0.8},
        )
        signals = {"llm.response_depth": 0.75}  # Normalized: high (>= 0.75)
        score = score_strategy(strategy, signals)
        assert score == 0.0

    def test_score_with_numeric_normalized(self):
        """Test scoring with numeric signal already in [0,1]."""
        strategy = StrategyConfig(
            name="test",
            description="Test strategy",
            signal_weights={"graph.node_count": 0.5},
        )
        signals = {"graph.node_count": 0.5}  # Pre-normalized to [0,1]
        score = score_strategy(strategy, signals)
        assert score == 0.25  # 0.5 * 0.5

    def test_score_with_multiple_signals(self):
        """Test scoring with multiple signal weights."""
        strategy = StrategyConfig(
            name="test",
            description="Test strategy",
            signal_weights={
                "llm.response_depth.high": 0.7,
                "llm.valence.high": 0.3,
            },
        )
        signals = {
            "llm.response_depth": 1.0,  # Normalized: high (>= 0.75)
            "llm.valence": 0.75,  # Normalized: high (>= 0.75)
        }
        score = score_strategy(strategy, signals)
        assert score == pytest.approx(1.0)  # 0.7 + 0.3

    def test_score_with_missing_signal(self):
        """Test scoring ignores missing signals."""
        strategy = StrategyConfig(
            name="test",
            description="Test strategy",
            signal_weights={
                "llm.response_depth.high": 0.7,
                "missing.signal": 0.5,
            },
        )
        signals = {"llm.response_depth": 1.0}  # Normalized: high (>= 0.75)
        score = score_strategy(strategy, signals)
        assert score == 0.7  # Only counts the matching signal

    def test_score_negative_weight(self):
        """Test scoring with negative weight (penalty)."""
        strategy = StrategyConfig(
            name="test",
            description="Test strategy",
            signal_weights={"llm.response_depth.low": -0.5},
        )
        signals = {"llm.response_depth": 0.0}  # Normalized: low (<= 0.25)
        score = score_strategy(strategy, signals)
        assert score == -0.5


class TestRankStrategies:
    """Tests for rank_strategies function."""

    def test_rank_by_score_descending(self):
        """Test strategies are ranked by score in descending order."""
        strategies = [
            StrategyConfig(
                name="low",
                description="Low score",
                signal_weights={"llm.response_depth.low": 0.3},
            ),
            StrategyConfig(
                name="high",
                description="High score",
                signal_weights={"llm.response_depth.high": 0.8},
            ),
            StrategyConfig(
                name="mid",
                description="Mid score",
                signal_weights={"llm.response_depth.high": 0.5},
            ),
        ]
        signals = {"llm.response_depth": 1.0}  # Normalized: high (>= 0.75)
        ranked = rank_strategies(strategies, signals)

        assert len(ranked) == 3
        assert ranked[0][0].name == "high"  # 0.8
        assert ranked[1][0].name == "mid"  # 0.5
        assert ranked[2][0].name == "low"  # 0.0 (low threshold doesn't match 1.0)

    def test_rank_with_phase_weights(self):
        """Test phase weights are applied as multipliers."""
        strategy = StrategyConfig(
            name="test",
            description="Test strategy",
            signal_weights={"llm.response_depth.high": 0.5},
        )
        signals = {"llm.response_depth": 1.0, "meta.interview.phase": "explore"}  # high
        ranked = rank_strategies(
            [strategy],
            signals,
            phase_weights={"test": 2.0},
        )

        assert ranked[0][1] == 1.0  # 0.5 * 2.0

    def test_rank_with_phase_bonuses(self):
        """Test phase bonuses are applied additively."""
        strategy = StrategyConfig(
            name="test",
            description="Test strategy",
            signal_weights={"llm.response_depth.high": 0.5},
        )
        signals = {"llm.response_depth": 1.0}  # high
        ranked = rank_strategies(
            [strategy],
            signals,
            phase_bonuses={"test": 0.3},
        )

        assert ranked[0][1] == 0.8  # 0.5 + 0.3

    def test_rank_with_phase_weights_and_bonuses(self):
        """Test both phase weights and bonuses are applied."""
        strategy = StrategyConfig(
            name="test",
            description="Test strategy",
            signal_weights={"llm.response_depth.high": 0.5},
        )
        signals = {"llm.response_depth": 1.0}  # high
        ranked = rank_strategies(
            [strategy],
            signals,
            phase_weights={"test": 2.0},
            phase_bonuses={"test": 0.3},
        )

        # Final score = (base * multiplier) + bonus
        assert ranked[0][1] == 1.3  # (0.5 * 2.0) + 0.3


class TestRankStrategyNodePairs:
    """Tests for rank_strategy_node_pairs function."""

    def test_rank_pairs_with_node_signals(self):
        """Test joint scoring with node-specific signals."""
        strategies = [
            StrategyConfig(
                name="explore_high",
                description="High depth",
                signal_weights={"llm.response_depth.high": 1.0},
            ),
        ]
        global_signals = {"meta.interview.phase": "explore"}
        node_signals = {
            "node_1": {"llm.response_depth": 0.25},  # Not high (low)
            "node_2": {"llm.response_depth": 1.0},  # High
        }

        ranked, decomposition = rank_strategy_node_pairs(
            strategies, global_signals, node_signals
        )

        assert len(ranked) == 2
        # node_2 should rank higher (response_depth=5 matches high threshold)
        assert ranked[0][1] == "node_2"
        assert ranked[0][2] == 1.0
        assert ranked[1][1] == "node_1"
        assert ranked[1][2] == 0.0

    def test_rank_pairs_global_signal_fallback(self):
        """Test global signals used when node signal not present."""
        strategies = [
            StrategyConfig(
                name="test",
                description="Test",
                signal_weights={"llm.response_depth.high": 1.0},
            ),
        ]
        global_signals = {"llm.response_depth": 1.0}  # High (>= 0.75)
        node_signals = {
            "node_1": {},  # No override, uses global
        }

        ranked, _ = rank_strategy_node_pairs(strategies, global_signals, node_signals)

        assert ranked[0][2] == 1.0  # Uses global signal value

    def test_rank_pairs_node_signal_override(self):
        """Test node signals override global signals."""
        strategies = [
            StrategyConfig(
                name="test",
                description="Test",
                signal_weights={"llm.response_depth.high": 1.0},
            ),
        ]
        global_signals = {"llm.response_depth": 1.0}  # High (>= 0.75)
        node_signals = {
            "node_1": {"llm.response_depth": 0.25},  # Override to low
        }

        ranked, _ = rank_strategy_node_pairs(strategies, global_signals, node_signals)

        assert ranked[0][2] == 0.0  # Uses node signal value (not high)

    def test_rank_pairs_with_phase_modifiers(self):
        """Test phase weights and bonuses apply to pairs."""
        strategies = [
            StrategyConfig(
                name="test",
                description="Test",
                signal_weights={"llm.response_depth.high": 0.5},
            ),
        ]
        global_signals = {"llm.response_depth": 1.0}  # High (>= 0.75)
        node_signals = {"node_1": {}}

        ranked, _ = rank_strategy_node_pairs(
            strategies,
            global_signals,
            node_signals,
            phase_weights={"test": 2.0},
            phase_bonuses={"test": 0.3},
        )

        # Final score = (0.5 * 2.0) + 0.3 = 1.3
        assert ranked[0][2] == pytest.approx(1.3)

    def test_rank_strategy_node_pairs_returns_decomposition(self):
        """rank_strategy_node_pairs should return ScoredCandidate list alongside ranked pairs."""
        strategy = StrategyConfig(
            name="dig_motivation",
            description="Dig motivation",
            signal_weights={
                "llm.engagement.high": 0.5,
                "llm.response_depth.deep": 0.3,
            },
        )
        global_signals = {
            "llm.engagement": 0.75,  # >= 0.75 → "high" → True
            "llm.response_depth": "deep",
        }
        node_signals = {"node-1": {}}

        ranked, decomposition = rank_strategy_node_pairs(
            strategies=[strategy],
            global_signals=global_signals,
            node_signals=node_signals,
        )

        assert len(decomposition) == 1
        candidate = decomposition[0]
        assert candidate.strategy == "dig_motivation"
        assert candidate.node_id == "node-1"
        assert candidate.selected is True
        assert candidate.rank == 1
        # engagement.high fired: 0.5 contribution; response_depth.deep fired: 0.3
        assert abs(candidate.base_score - 0.8) < 0.001
        assert len(candidate.signal_contributions) == 2


class TestLLMSignalThresholdsIntegration:
    """Integration tests for LLM signal threshold binning."""

    @pytest.mark.parametrize(
        "signal_value,qualifier,expected",
        [
            # Low threshold (<= 0.25)
            (0.0, "low", True),
            (0.25, "low", True),
            (0.5, "low", False),
            (0.75, "low", False),
            (1.0, "low", False),
            # Mid threshold (0.25 < x < 0.75)
            (0.0, "mid", False),
            (0.25, "mid", False),
            (0.5, "mid", True),
            (0.75, "mid", False),
            (1.0, "mid", False),
            # High threshold (>= 0.75)
            (0.0, "high", False),
            (0.25, "high", False),
            (0.5, "high", False),
            (0.75, "high", True),
            (1.0, "high", True),
        ],
    )
    def test_all_llm_signals_threshold_combinations(
        self, signal_value, qualifier, expected
    ):
        """Test all LLM signals use consistent threshold binning."""
        signals = {
            "llm.response_depth": signal_value,
            "llm.valence": signal_value,
            "llm.certainty": signal_value,
            "llm.specificity": signal_value,
            "llm.engagement": signal_value,
        }

        for signal_name in signals:
            if signal_name == "llm.response_depth":
                continue  # Skip, we use it as the key
            key = f"llm.response_depth.{qualifier}"
            result = _get_signal_value(key, signals)
            assert result == expected, (
                f"Failed for {key} with value {signal_value}: expected {expected}, got {result}"
            )

    def test_new_llm_signal_names_in_strategy(self):
        """Test scoring with new LLM signal names (post-migration)."""
        strategy = StrategyConfig(
            name="explore_emotions",
            description="Explore emotional content",
            signal_weights={
                "llm.valence.low": 0.6,
                "llm.valence.high": 0.6,
                "llm.certainty.low": 0.4,
                "llm.engagement.high": 0.8,
            },
        )

        # Test low valence (negative sentiment)
        signals = {"llm.valence": 0.0}  # Normalized: low (<= 0.25)
        score = score_strategy(strategy, signals)
        assert score == pytest.approx(0.6)

        # Test high valence (positive sentiment)
        signals = {"llm.valence": 1.0}  # Normalized: high (>= 0.75)
        score = score_strategy(strategy, signals)
        assert score == pytest.approx(0.6)

        # Test high engagement
        signals = {"llm.engagement": 1.0}  # Normalized: high (>= 0.75)
        score = score_strategy(strategy, signals)
        assert score == pytest.approx(0.8)

        # Test low certainty (previously high uncertainty/hedging)
        signals = {"llm.certainty": 0.0}  # Normalized: low (<= 0.25)
        score = score_strategy(strategy, signals)
        assert score == pytest.approx(0.4)


class TestStrategyConfigNodeBinding:
    """Tests for StrategyConfig node_binding field."""

    def test_default_node_binding_is_required(self):
        config = StrategyConfig(
            name="test",
            description="Test",
            signal_weights={"llm.engagement.high": 0.5},
        )
        assert config.node_binding == "required"

    def test_node_binding_none(self):
        config = StrategyConfig(
            name="reflect",
            description="Reflect",
            signal_weights={"meta.interview_progress": 0.5},
            node_binding="none",
        )
        assert config.node_binding == "none"


class TestPartitionSignalWeights:
    """Tests for auto-partitioning signal weights by namespace."""

    def test_separates_node_signals(self):
        weights = {
            "llm.response_depth.low": 0.8,
            "llm.engagement.high": 0.7,
            "graph.node.exhaustion_score.low": 1.0,
            "graph.node.focus_streak.high": -0.8,
            "technique.node.strategy_repetition.low": 0.3,
        }
        strategy_weights, node_weights = partition_signal_weights(weights)
        assert strategy_weights == {
            "llm.response_depth.low": 0.8,
            "llm.engagement.high": 0.7,
        }
        assert node_weights == {
            "graph.node.exhaustion_score.low": 1.0,
            "graph.node.focus_streak.high": -0.8,
            "technique.node.strategy_repetition.low": 0.3,
        }

    def test_all_global(self):
        weights = {"llm.engagement.high": 0.5, "meta.interview_progress": 0.3}
        strategy_weights, node_weights = partition_signal_weights(weights)
        assert strategy_weights == weights
        assert node_weights == {}

    def test_all_node(self):
        weights = {"graph.node.exhaustion_score.low": 1.0}
        strategy_weights, node_weights = partition_signal_weights(weights)
        assert strategy_weights == {}
        assert node_weights == weights

    def test_empty_weights(self):
        strategy_weights, node_weights = partition_signal_weights({})
        assert strategy_weights == {}
        assert node_weights == {}

    def test_meta_node_goes_to_node_weights(self):
        weights = {"meta.node.opportunity.fresh": 0.6}
        strategy_weights, node_weights = partition_signal_weights(weights)
        assert strategy_weights == {}
        assert node_weights == {"meta.node.opportunity.fresh": 0.6}


class TestRankStrategiesExcludesNodeSignals:
    """Test that rank_strategies only uses global signal weights."""

    def test_node_signals_excluded_from_strategy_scoring(self):
        strategy_a = StrategyConfig(
            name="deepen",
            description="Deepen",
            signal_weights={
                "llm.response_depth.low": 0.8,
                "graph.node.exhaustion_score.low": 5.0,  # node → must be excluded
            },
        )
        strategy_b = StrategyConfig(
            name="explore",
            description="Explore",
            signal_weights={
                "llm.response_depth.low": 0.9,
            },
        )
        # Include graph.node.exhaustion_score in global signals to simulate
        # a scenario where node signal bleeds into strategy scoring
        signals = {
            "llm.response_depth": 0.1,  # low
            "graph.node.exhaustion_score": 0.1,  # low — node signal in global dict
        }

        ranked = rank_strategies([strategy_a, strategy_b], signals)

        # Without node exclusion: deepen=0.8+5.0=5.8, explore=0.9 → deepen wins (wrong)
        # With node exclusion: deepen=0.8, explore=0.9 → explore wins (correct)
        assert ranked[0][0].name == "explore"
        assert ranked[0][1] == pytest.approx(0.9)
        assert ranked[1][0].name == "deepen"
        assert ranked[1][1] == pytest.approx(0.8)


class TestRankNodesForStrategy:
    """Tests for node ranking within a selected strategy."""

    def test_ranks_nodes_by_node_signal_score(self):
        strategy = StrategyConfig(
            name="deepen",
            description="Deepen",
            signal_weights={
                "llm.response_depth.low": 0.8,
                "graph.node.exhaustion_score.low": 1.0,
                "graph.node.focus_streak.high": -0.8,
            },
        )
        node_signals = {
            "node_a": {
                "graph.node.exhaustion_score": 0.1,
                "graph.node.focus_streak": 0.9,
            },
            "node_b": {
                "graph.node.exhaustion_score": 0.1,
                "graph.node.focus_streak": 0.1,
            },
        }
        ranked, candidates = rank_nodes_for_strategy(strategy, node_signals)
        assert len(ranked) == 2
        # node_b wins: exh.low=True(+1.0), streak.high=False(0) = 1.0
        # node_a: exh.low=True(+1.0), streak.high=True(-0.8) = 0.2
        assert ranked[0][0] == "node_b"
        assert ranked[1][0] == "node_a"
        assert ranked[0][1] > ranked[1][1]

    def test_returns_empty_for_no_nodes(self):
        strategy = StrategyConfig(
            name="deepen",
            description="Deepen",
            signal_weights={"graph.node.exhaustion_score.low": 1.0},
        )
        ranked, candidates = rank_nodes_for_strategy(strategy, {})
        assert ranked == []
        assert candidates == []

    def test_only_uses_node_weights(self):
        strategy = StrategyConfig(
            name="deepen",
            description="Deepen",
            signal_weights={
                "llm.response_depth.low": 0.8,
                "graph.node.exhaustion_score.low": 1.0,
            },
        )
        node_signals = {"node_a": {"graph.node.exhaustion_score": 0.1}}
        ranked, _ = rank_nodes_for_strategy(strategy, node_signals)
        assert ranked[0][1] == pytest.approx(1.0)  # Only node weight, not global

    def test_returns_scored_candidates(self):
        strategy = StrategyConfig(
            name="deepen",
            description="Deepen",
            signal_weights={"graph.node.exhaustion_score.low": 1.0},
        )
        node_signals = {"node_a": {"graph.node.exhaustion_score": 0.1}}
        _, candidates = rank_nodes_for_strategy(strategy, node_signals)
        assert len(candidates) == 1
        assert candidates[0].strategy == "deepen"
        assert candidates[0].node_id == "node_a"
        assert len(candidates[0].signal_contributions) == 1
        assert (
            candidates[0].signal_contributions[0].name
            == "graph.node.exhaustion_score.low"
        )


class TestRankStrategiesDecomposition:
    """Tests for Stage 1 strategy score decomposition."""

    def test_returns_decomposition_when_requested(self):
        """rank_strategies should return (ranked, decomposition) when return_decomposition=True."""
        strategies = [
            StrategyConfig(
                name="deepen",
                description="D",
                signal_weights={
                    "llm.response_depth.low": 0.8,
                    "llm.engagement.high": 0.7,
                },
            ),
            StrategyConfig(
                name="explore",
                description="E",
                signal_weights={"llm.response_depth.low": 0.5},
            ),
        ]
        signals = {"llm.response_depth": 0.1, "llm.engagement": 0.9}
        phase_weights = {"deepen": 1.3}
        phase_bonuses = {"deepen": 0.2}

        result = rank_strategies(
            strategies, signals, phase_weights, phase_bonuses, return_decomposition=True
        )

        # Should return tuple of (ranked_strategies, decomposition)
        assert isinstance(result, tuple)
        assert len(result) == 2

        ranked, decomposition = result

        # Verify ranked strategies (existing behavior)
        assert len(ranked) == 2
        assert ranked[0][0].name == "deepen"
        assert ranked[0][1] > 0  # Should have phase-applied score

        # Verify decomposition exists
        assert len(decomposition) == 2
        assert all(isinstance(c, ScoredCandidate) for c in decomposition)

        # Verify deepen has phase multipliers
        deepen_decomp = next(c for c in decomposition if c.strategy == "deepen")
        assert deepen_decomp.phase_multiplier == 1.3
        assert deepen_decomp.phase_bonus == 0.2
        assert deepen_decomp.final_score == deepen_decomp.base_score * 1.3 + 0.2

        # Verify signal contributions are captured
        assert len(deepen_decomp.signal_contributions) == 2
        contrib_names = {c.name for c in deepen_decomp.signal_contributions}
        assert "llm.response_depth.low" in contrib_names
        assert "llm.engagement.high" in contrib_names

    def test_backward_compatible_when_not_requested(self):
        """rank_strategies should return only ranked list when return_decomposition=False (default)."""
        strategies = [
            StrategyConfig(
                name="test",
                description="T",
                signal_weights={"llm.engagement.high": 0.5},
            ),
        ]
        signals = {"llm.engagement": 0.8}

        # Default behavior (return_decomposition=False)
        result = rank_strategies(strategies, signals)

        # Should return list, not tuple
        assert isinstance(result, list)
        assert not isinstance(result, tuple)
        assert len(result) == 1
        assert result[0][0].name == "test"

    def test_decomposition_includes_rank_and_selected(self):
        """Decomposition should mark best strategy as selected with rank=1."""
        strategies = [
            StrategyConfig(name="low", description="L", signal_weights={"x": 0.1}),
            StrategyConfig(name="high", description="H", signal_weights={"x": 1.0}),
        ]
        signals = {"x": 1.0}

        ranked, decomposition = rank_strategies(
            strategies, signals, return_decomposition=True
        )

        # High score strategy should be selected
        high_decomp = next(c for c in decomposition if c.strategy == "high")
        assert high_decomp.selected == True
        assert high_decomp.rank == 1

        # Low score strategy should not be selected
        low_decomp = next(c for c in decomposition if c.strategy == "low")
        assert low_decomp.selected == False
        assert low_decomp.rank == 2

    def test_strategy_decomposition_has_empty_node_id(self):
        """Strategy-level decomposition should have empty node_id to distinguish from node decomposition."""
        strategies = [
            StrategyConfig(name="test", description="T", signal_weights={"x": 1.0}),
        ]
        signals = {"x": 1.0}

        ranked, decomposition = rank_strategies(
            strategies, signals, return_decomposition=True
        )

        assert len(decomposition) == 1
        assert decomposition[0].node_id == ""  # Empty for strategy-level
        assert decomposition[0].strategy == "test"
