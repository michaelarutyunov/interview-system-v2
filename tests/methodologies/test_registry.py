"""Tests for MethodologyRegistry and StrategyConfig."""

import pytest
from src.methodologies.registry import StrategyConfig, MethodologyRegistry


class TestStrategyConfigFocusMode:
    """Test focus_mode field on StrategyConfig."""

    def test_default_focus_mode_is_recent_node(self):
        config = StrategyConfig(
            name="test", description="test", signal_weights={}
        )
        assert config.focus_mode == "recent_node"

    def test_focus_mode_summary(self):
        config = StrategyConfig(
            name="test",
            description="test",
            signal_weights={},
            focus_mode="summary",
        )
        assert config.focus_mode == "summary"

    def test_focus_mode_topic(self):
        config = StrategyConfig(
            name="test",
            description="test",
            signal_weights={},
            focus_mode="topic",
        )
        assert config.focus_mode == "topic"


class TestRegistryFocusModeValidation:
    """Test that registry validates focus_mode values."""

    def test_invalid_focus_mode_raises(self, tmp_path):
        """Invalid focus_mode should fail validation."""
        yaml_content = """\
method:
  name: test_method
  description: test
strategies:
  - name: bad_strategy
    description: test
    signal_weights: {}
    focus_mode: invalid_value
"""
        config_file = tmp_path / "test_method.yaml"
        config_file.write_text(yaml_content)

        registry = MethodologyRegistry(config_dir=tmp_path)
        with pytest.raises(ValueError, match="invalid focus_mode"):
            registry.get_methodology("test_method")

    def test_valid_focus_modes_pass_validation(self, tmp_path):
        """All valid focus_mode values should pass."""
        yaml_content = """\
method:
  name: test_method
  description: test
strategies:
  - name: strategy_a
    description: recent node focus
    signal_weights: {}
    focus_mode: recent_node
  - name: strategy_b
    description: summary focus
    signal_weights: {}
    focus_mode: summary
  - name: strategy_c
    description: default focus
    signal_weights: {}
"""
        config_file = tmp_path / "test_method.yaml"
        config_file.write_text(yaml_content)

        registry = MethodologyRegistry(config_dir=tmp_path)
        config = registry.get_methodology("test_method")
        assert config.strategies[0].focus_mode == "recent_node"
        assert config.strategies[1].focus_mode == "summary"
        assert config.strategies[2].focus_mode == "recent_node"  # default
