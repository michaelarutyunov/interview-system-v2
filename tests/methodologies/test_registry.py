"""Tests for methodology registry — node_type_priorities in StrategyConfig."""

from src.methodologies.registry import StrategyConfig


class TestStrategyConfigNodeTypePriorities:
    """Tests for node_type_priorities field on StrategyConfig."""

    def test_default_empty(self):
        """StrategyConfig defaults to empty node_type_priorities."""
        config = StrategyConfig(
            name="test",
            description="Test",
            signal_weights={"llm.engagement.high": 0.5},
        )
        assert config.node_type_priorities == {}

    def test_explicit_priorities(self):
        """StrategyConfig accepts node_type_priorities."""
        config = StrategyConfig(
            name="test",
            description="Test",
            signal_weights={},
            node_type_priorities={
                "pain_point": 0.8,
                "job_trigger": 0.7,
                "gain_point": 0.5,
            },
        )
        assert config.node_type_priorities["pain_point"] == 0.8
        assert config.node_type_priorities["job_trigger"] == 0.7
