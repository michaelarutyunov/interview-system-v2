"""Tests for methodology scoring module."""

import pytest

from src.methodologies.scoring import (
    _get_signal_value,
    _normalize_numeric,
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

    def test_integer_threshold_low_boundary(self):
        """Test low threshold matches values 1 and 2."""
        signals = {"llm.response_depth": 1}
        assert _get_signal_value("llm.response_depth.low", signals) is True

        signals = {"llm.response_depth": 2}
        assert _get_signal_value("llm.response_depth.low", signals) is True

    def test_integer_threshold_low_non_match(self):
        """Test low threshold does not match values 3, 4, 5."""
        signals = {"llm.response_depth": 3}
        assert _get_signal_value("llm.response_depth.low", signals) is False

        signals = {"llm.response_depth": 4}
        assert _get_signal_value("llm.response_depth.low", signals) is False

        signals = {"llm.response_depth": 5}
        assert _get_signal_value("llm.response_depth.low", signals) is False

    def test_integer_threshold_mid_boundary(self):
        """Test mid threshold matches value 3 only."""
        signals = {"llm.response_depth": 3}
        assert _get_signal_value("llm.response_depth.mid", signals) is True

    def test_integer_threshold_mid_non_match(self):
        """Test mid threshold does not match values 1, 2, 4, 5."""
        for value in [1, 2, 4, 5]:
            signals = {"llm.response_depth": value}
            assert _get_signal_value("llm.response_depth.mid", signals) is False

    def test_integer_threshold_high_boundary(self):
        """Test high threshold matches values 4 and 5."""
        signals = {"llm.response_depth": 4}
        assert _get_signal_value("llm.response_depth.high", signals) is True

        signals = {"llm.response_depth": 5}
        assert _get_signal_value("llm.response_depth.high", signals) is True

    def test_integer_threshold_high_non_match(self):
        """Test high threshold does not match values 1, 2, 3."""
        for value in [1, 2, 3]:
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

    def test_deep_compound_key_not_found(self):
        """Test deeply nested compound keys when base signal not found."""
        signals = {"graph.chain_completion": {"has_complete_chain": True}}
        # The compound key "graph.chain_completion.has_complete_chain.true" has base
        # "graph.chain_completion.has_complete_chain" which is not in signals
        result = _get_signal_value(
            "graph.chain_completion.has_complete_chain.true", signals
        )
        assert result is None  # Base signal not found

    def test_compound_key_base_not_found(self):
        """Test compound key returns None when base signal not present."""
        signals = {"graph.node_count": 10}
        assert _get_signal_value("llm.response_depth.low", signals) is None


class TestNormalizeNumeric:
    """Tests for _normalize_numeric function."""

    def test_value_already_normalized(self):
        """Test values in [0, 1] range pass through."""
        assert _normalize_numeric("test", 0.5, None) == 0.5
        assert _normalize_numeric("test", 0.0, None) == 0.0
        assert _normalize_numeric("test", 1.0, None) == 1.0

    def test_value_already_normalized_negative(self):
        """Test negative values in [-1, 0] range pass through."""
        assert _normalize_numeric("test", -0.5, None) == -0.5
        assert _normalize_numeric("test", -1.0, None) == -1.0

    def test_normalization_with_norm(self):
        """Test normalization using signal_norms."""
        norms = {"graph.node_count": 50.0}
        assert _normalize_numeric("graph.node_count", 25, norms) == 0.5
        assert _normalize_numeric("graph.node_count", 50, norms) == 1.0

    def test_normalization_clamped(self):
        """Test normalized values are clamped to [0, 1]."""
        norms = {"graph.node_count": 50.0}
        assert _normalize_numeric("graph.node_count", 100, norms) == 1.0

    def test_missing_norm_raises(self):
        """Test ValueError raised when norm missing for value > 1."""
        with pytest.raises(ValueError) as exc_info:
            _normalize_numeric("unknown.signal", 5, None)
        assert "no signal_norm defined" in str(exc_info.value)


class TestScoreStrategy:
    """Tests for score_strategy function."""

    def test_score_with_boolean_match(self):
        """Test scoring with boolean signal match."""
        strategy = StrategyConfig(
            name="test",
            description="Test strategy",
            signal_weights={"llm.response_depth.low": 0.8},
        )
        signals = {"llm.response_depth": 2}
        score = score_strategy(strategy, signals)
        assert score == 0.8

    def test_score_with_boolean_no_match(self):
        """Test scoring with boolean signal no match."""
        strategy = StrategyConfig(
            name="test",
            description="Test strategy",
            signal_weights={"llm.response_depth.low": 0.8},
        )
        signals = {"llm.response_depth": 4}
        score = score_strategy(strategy, signals)
        assert score == 0.0

    def test_score_with_numeric_normalized(self):
        """Test scoring with numeric signal using normalization."""
        strategy = StrategyConfig(
            name="test",
            description="Test strategy",
            signal_weights={"graph.node_count": 0.5},
        )
        signals = {"graph.node_count": 25}
        norms = {"graph.node_count": 50.0}
        score = score_strategy(strategy, signals, signal_norms=norms)
        assert score == 0.25  # 0.5 * (25/50)

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
            "llm.response_depth": 5,
            "llm.valence": 4,
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
        signals = {"llm.response_depth": 5}
        score = score_strategy(strategy, signals)
        assert score == 0.7  # Only counts the matching signal

    def test_score_negative_weight(self):
        """Test scoring with negative weight (penalty)."""
        strategy = StrategyConfig(
            name="test",
            description="Test strategy",
            signal_weights={"llm.response_depth.low": -0.5},
        )
        signals = {"llm.response_depth": 1}
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
        signals = {"llm.response_depth": 5}
        ranked = rank_strategies(strategies, signals)

        assert len(ranked) == 3
        assert ranked[0][0].name == "high"  # 0.8
        assert ranked[1][0].name == "mid"  # 0.5
        assert ranked[2][0].name == "low"  # 0.0 (low threshold doesn't match 5)

    def test_rank_with_phase_weights(self):
        """Test phase weights are applied as multipliers."""
        strategy = StrategyConfig(
            name="test",
            description="Test strategy",
            signal_weights={"llm.response_depth.high": 0.5},
        )
        signals = {"llm.response_depth": 5, "meta.interview.phase": "explore"}
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
        signals = {"llm.response_depth": 5}
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
        signals = {"llm.response_depth": 5}
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
            "node_1": {"llm.response_depth": 2},  # Not high
            "node_2": {"llm.response_depth": 5},  # High
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
        global_signals = {"llm.response_depth": 5}  # High
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
        global_signals = {"llm.response_depth": 5}  # High
        node_signals = {
            "node_1": {"llm.response_depth": 2},  # Override to low
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
        global_signals = {"llm.response_depth": 5}
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
            # Low threshold (1-2)
            (1, "low", True),
            (2, "low", True),
            (3, "low", False),
            (4, "low", False),
            (5, "low", False),
            # Mid threshold (3)
            (1, "mid", False),
            (2, "mid", False),
            (3, "mid", True),
            (4, "mid", False),
            (5, "mid", False),
            # High threshold (4-5)
            (1, "high", False),
            (2, "high", False),
            (3, "high", False),
            (4, "high", True),
            (5, "high", True),
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
        signals = {"llm.valence": 1}
        score = score_strategy(strategy, signals)
        assert score == pytest.approx(0.6)

        # Test high valence (positive sentiment)
        signals = {"llm.valence": 5}
        score = score_strategy(strategy, signals)
        assert score == pytest.approx(0.6)

        # Test high engagement
        signals = {"llm.engagement": 5}
        score = score_strategy(strategy, signals)
        assert score == pytest.approx(0.8)

        # Test low certainty (previously high uncertainty/hedging)
        signals = {"llm.certainty": 1}
        score = score_strategy(strategy, signals)
        assert score == pytest.approx(0.4)
