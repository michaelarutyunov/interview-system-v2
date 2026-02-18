"""Tests for methodology scoring module."""

import pytest

from src.methodologies.scoring import (
    _get_signal_value,
    score_strategy,
    rank_strategies,
    rank_strategy_node_pairs,
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

        ranked = rank_strategy_node_pairs(strategies, global_signals, node_signals)

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

        ranked = rank_strategy_node_pairs(strategies, global_signals, node_signals)

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

        ranked = rank_strategy_node_pairs(strategies, global_signals, node_signals)

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

        ranked = rank_strategy_node_pairs(
            strategies,
            global_signals,
            node_signals,
            phase_weights={"test": 2.0},
            phase_bonuses={"test": 0.3},
        )

        # Final score = (0.5 * 2.0) + 0.3 = 1.3
        assert ranked[0][2] == pytest.approx(1.3)


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
                f"Failed for {key} with value {signal_value}: "
                f"expected {expected}, got {result}"
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
