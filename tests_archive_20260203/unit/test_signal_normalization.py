"""Unit tests for per-signal normalization in scoring.

Tests that score_strategy uses signal_norms (max_expected values)
instead of the hardcoded /10.0 heuristic for numeric signals.
"""

import pytest
from src.methodologies.registry import StrategyConfig
from src.methodologies.scoring import score_strategy


def _make_strategy(signal_weights: dict[str, float]) -> StrategyConfig:
    return StrategyConfig(
        name="test_strategy",
        description="test",
        technique="laddering",
        signal_weights=signal_weights,
    )


class TestNumericNormalizationWithSignalNorms:
    """Test that signal_norms replaces the /10.0 heuristic."""

    def test_node_count_normalized_by_max_expected(self):
        """node_count=25 with max_expected=50 should contribute weight*0.5."""
        strategy = _make_strategy({"graph.node_count": 1.0})
        signals = {"graph.node_count": 25}
        signal_norms = {"graph.node_count": 50.0}

        score = score_strategy(strategy, signals, signal_norms=signal_norms)

        assert score == pytest.approx(0.5)

    def test_node_count_clips_at_max_expected(self):
        """node_count=100 with max_expected=50 should clip to 1.0."""
        strategy = _make_strategy({"graph.node_count": 1.0})
        signals = {"graph.node_count": 100}
        signal_norms = {"graph.node_count": 50.0}

        score = score_strategy(strategy, signals, signal_norms=signal_norms)

        assert score == pytest.approx(1.0)

    def test_max_depth_normalized_by_max_expected(self):
        """max_depth=4 with max_expected=8 should contribute weight*0.5."""
        strategy = _make_strategy({"graph.max_depth": 0.7})
        signals = {"graph.max_depth": 4}
        signal_norms = {"graph.max_depth": 8.0}

        score = score_strategy(strategy, signals, signal_norms=signal_norms)

        assert score == pytest.approx(0.7 * 0.5)

    def test_orphan_count_normalized_by_max_expected(self):
        """orphan_count=10 with max_expected=20 should contribute weight*0.5."""
        strategy = _make_strategy({"graph.orphan_count": 0.5})
        signals = {"graph.orphan_count": 10}
        signal_norms = {"graph.orphan_count": 20.0}

        score = score_strategy(strategy, signals, signal_norms=signal_norms)

        assert score == pytest.approx(0.5 * 0.5)

    def test_negative_weight_with_signal_norm(self):
        """Negative weights should scale properly with signal_norms.

        broaden uses graph.node_count: -0.3
        node_count=25 with max_expected=50 → contribution = -0.3 * 0.5 = -0.15
        """
        strategy = _make_strategy({"graph.node_count": -0.3})
        signals = {"graph.node_count": 25}
        signal_norms = {"graph.node_count": 50.0}

        score = score_strategy(strategy, signals, signal_norms=signal_norms)

        assert score == pytest.approx(-0.15)

    def test_temporal_signal_with_signal_norm(self):
        """temporal.strategy_repetition_count=3 with max_expected=5 → 0.6."""
        strategy = _make_strategy({"temporal.strategy_repetition_count": 0.5})
        signals = {"temporal.strategy_repetition_count": 3}
        signal_norms = {"temporal.strategy_repetition_count": 5.0}

        score = score_strategy(strategy, signals, signal_norms=signal_norms)

        assert score == pytest.approx(0.5 * 0.6)


class TestFallbackWithoutSignalNorms:
    """Test behavior when signal_norms is not provided."""

    def test_no_signal_norms_raises_for_numeric_gt_1(self):
        """Without signal_norms, numeric values > 1 raise ValueError."""
        strategy = _make_strategy({"graph.node_count": 1.0})
        signals = {"graph.node_count": 5}

        with pytest.raises(ValueError, match="signal_norm defined"):
            score_strategy(strategy, signals)

    def test_already_normalized_signals_pass_through(self):
        """Values already in [0, 1] should not be re-normalized."""
        strategy = _make_strategy({"llm.uncertainty": 0.8})
        signals = {"llm.uncertainty": 0.6}
        signal_norms = {"graph.node_count": 50.0}  # unrelated norm

        score = score_strategy(strategy, signals, signal_norms=signal_norms)

        # 0.6 is <= 1, so it's used directly: 0.8 * 0.6 = 0.48
        assert score == pytest.approx(0.48)

    def test_boolean_signals_unaffected_by_norms(self):
        """Boolean signals should still work normally."""
        strategy = _make_strategy({"llm.response_depth.surface": 0.8})
        signals = {"llm.response_depth": "surface"}
        signal_norms = {"graph.node_count": 50.0}

        score = score_strategy(strategy, signals, signal_norms=signal_norms)

        assert score == pytest.approx(0.8)


class TestSignalNormsInRanking:
    """Test that signal_norms flows through rank_strategies and rank_strategy_node_pairs."""

    def test_rank_strategies_accepts_signal_norms(self):
        """rank_strategies should pass signal_norms through to score_strategy."""
        from src.methodologies.scoring import rank_strategies

        strategies = [
            _make_strategy({"graph.node_count": 1.0}),
            _make_strategy({"graph.max_depth": 1.0}),
        ]
        strategies[0].name = "broaden"
        strategies[1].name = "deepen"

        signals = {"graph.node_count": 25, "graph.max_depth": 4}
        signal_norms = {"graph.node_count": 50.0, "graph.max_depth": 8.0}

        ranked = rank_strategies(strategies, signals, signal_norms=signal_norms)

        # Both should score 0.5 (25/50 and 4/8)
        for _, score in ranked:
            assert score == pytest.approx(0.5)

    def test_rank_strategy_node_pairs_accepts_signal_norms(self):
        """rank_strategy_node_pairs should pass signal_norms through."""
        from src.methodologies.scoring import rank_strategy_node_pairs

        strategies = [_make_strategy({"graph.node_count": 1.0})]
        strategies[0].name = "explore"

        global_signals = {"graph.node_count": 25}
        node_signals = {"node1": {}}
        signal_norms = {"graph.node_count": 50.0}

        ranked = rank_strategy_node_pairs(
            strategies,
            global_signals,
            node_signals,
            signal_norms=signal_norms,
        )

        assert len(ranked) == 1
        _, _, score = ranked[0]
        assert score == pytest.approx(0.5)


class TestSignalNormsLoadedFromYAML:
    """Test that signal_norms are loaded from methodology YAML configs."""

    def test_means_end_chain_has_signal_norms(self):
        """MEC config should define signal_norms for graph metrics."""
        from src.methodologies.registry import MethodologyRegistry

        registry = MethodologyRegistry()
        config = registry.get_methodology("means_end_chain")

        assert config.signal_norms is not None
        assert "graph.node_count" in config.signal_norms
        assert "graph.max_depth" in config.signal_norms
        assert "graph.orphan_count" in config.signal_norms
        assert config.signal_norms["graph.node_count"] == 50.0

    def test_jobs_to_be_done_has_signal_norms(self):
        """JTBD config should define signal_norms for graph metrics."""
        from src.methodologies.registry import MethodologyRegistry

        registry = MethodologyRegistry()
        config = registry.get_methodology("jobs_to_be_done")

        assert config.signal_norms is not None
        assert "graph.node_count" in config.signal_norms
        assert "graph.max_depth" in config.signal_norms

    def test_signal_norms_used_in_scoring_from_config(self):
        """End-to-end: load config, use signal_norms in scoring."""
        from src.methodologies.registry import MethodologyRegistry

        registry = MethodologyRegistry()
        config = registry.get_methodology("means_end_chain")

        # Find a strategy that uses graph.node_count
        # Use any strategy with a numeric signal weight
        deepen = next(s for s in config.strategies if s.name == "deepen")

        # Score with signal_norms from config
        signals = {"graph.max_depth": 4}
        score = score_strategy(deepen, signals, signal_norms=config.signal_norms)

        # max_depth=4, max_expected=8 → normalized=0.5
        # deepen has graph.max_depth: 0.5 weight → contribution = 0.5 * 0.5 = 0.25
        assert score == pytest.approx(0.5 * 0.5)


class TestDifferentiationImproved:
    """Test the core bug: normalization should differentiate values that /10 could not."""

    def test_node_count_10_vs_50_produces_different_scores(self):
        """The original bug: node_count=10 and node_count=50 scored identically.

        With max_expected=50: 10→0.2, 50→1.0.
        """
        strategy = _make_strategy({"graph.node_count": 1.0})
        signal_norms = {"graph.node_count": 50.0}

        score_10 = score_strategy(
            strategy, {"graph.node_count": 10}, signal_norms=signal_norms
        )
        score_50 = score_strategy(
            strategy, {"graph.node_count": 50}, signal_norms=signal_norms
        )

        assert score_10 == pytest.approx(0.2)
        assert score_50 == pytest.approx(1.0)
        assert score_10 < score_50

    def test_depth_5_vs_8_produces_different_scores(self):
        """max_depth should differentiate 5 from 8 (max_expected=8)."""
        strategy = _make_strategy({"graph.max_depth": 1.0})
        signal_norms = {"graph.max_depth": 8.0}

        score_5 = score_strategy(
            strategy, {"graph.max_depth": 5}, signal_norms=signal_norms
        )
        score_8 = score_strategy(
            strategy, {"graph.max_depth": 8}, signal_norms=signal_norms
        )

        assert score_5 == pytest.approx(0.625)
        assert score_8 == pytest.approx(1.0)
        assert score_5 < score_8
