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


import tempfile
import os
import yaml


class TestRegistryLoadsNodeTypePriorities:
    """Test that MethodologyRegistry loads node_type_priorities from YAML."""

    def test_loads_priorities_from_yaml(self, tmp_path):
        """Registry loads node_type_priorities from strategy definition."""
        yaml_content = {
            "method": {"name": "test_method", "description": "Test"},
            "signals": {},
            "strategies": [
                {
                    "name": "explore",
                    "description": "Explore",
                    "signal_weights": {},
                    "node_type_priorities": {
                        "pain_point": 0.8,
                        "job_trigger": 0.7,
                    },
                }
            ],
        }
        config_dir = tmp_path / "methodologies"
        config_dir.mkdir()
        config_file = config_dir / "test_method.yaml"
        config_file.write_text(yaml.dump(yaml_content))

        from src.methodologies.registry import MethodologyRegistry

        registry = MethodologyRegistry(config_dir=config_dir)
        config = registry.get_methodology("test_method")

        assert config.strategies[0].node_type_priorities == {
            "pain_point": 0.8,
            "job_trigger": 0.7,
        }

    def test_defaults_to_empty_when_absent(self, tmp_path):
        """Registry defaults node_type_priorities to {} when not in YAML."""
        yaml_content = {
            "method": {"name": "test_method2", "description": "Test"},
            "signals": {},
            "strategies": [
                {
                    "name": "explore",
                    "description": "Explore",
                    "signal_weights": {},
                }
            ],
        }
        config_dir = tmp_path / "methodologies"
        config_dir.mkdir()
        config_file = config_dir / "test_method2.yaml"
        config_file.write_text(yaml.dump(yaml_content))

        from src.methodologies.registry import MethodologyRegistry

        registry = MethodologyRegistry(config_dir=config_dir)
        config = registry.get_methodology("test_method2")

        assert config.strategies[0].node_type_priorities == {}
