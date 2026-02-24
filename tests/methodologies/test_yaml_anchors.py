"""Smoke tests for YAML anchor merge functionality.

Tests that YAML anchors resolve correctly into flat dicts that can be
validated by Pydantic models. Per bead x0hm acceptance criteria #6.
"""

import yaml


def test_single_anchor_merge():
    """Test single anchor merge resolves to flat dict."""
    yaml_str = """
_profiles: &gate
  llm.engagement.high: 0.5
  llm.engagement.low: -0.5
strategies:
  - name: test
    signal_weights:
      <<: *gate
      llm.depth: 0.3
"""
    result = yaml.safe_load(yaml_str)
    assert result["strategies"][0]["signal_weights"]["llm.engagement.high"] == 0.5
    assert result["strategies"][0]["signal_weights"]["llm.engagement.low"] == -0.5
    assert result["strategies"][0]["signal_weights"]["llm.depth"] == 0.3


def test_multi_anchor_merge():
    """Test multiple anchor merge resolves to flat dict."""
    yaml_str = """
_profiles:
  gate: &gate
    llm.engagement.high: 0.5
    llm.engagement.low: -0.5
  freshness: &freshness
    graph.node.exhaustion_score.low: 1.0
strategies:
  - name: test
    signal_weights:
      <<: [*gate, *freshness]
      llm.depth: 0.7
"""
    result = yaml.safe_load(yaml_str)
    weights = result["strategies"][0]["signal_weights"]
    assert weights["llm.engagement.high"] == 0.5
    assert weights["llm.engagement.low"] == -0.5
    assert weights["graph.node.exhaustion_score.low"] == 1.0
    assert weights["llm.depth"] == 0.7


def test_anchor_override():
    """Test local values override anchor values."""
    yaml_str = """
_profiles: &gate
  llm.engagement.high: 0.5
  llm.engagement.low: -0.5
strategies:
  - name: test
    signal_weights:
      <<: *gate
      llm.engagement.high: 0.8  # Override
"""
    result = yaml.safe_load(yaml_str)
    weights = result["strategies"][0]["signal_weights"]
    # Local override should win
    assert weights["llm.engagement.high"] == 0.8
    assert weights["llm.engagement.low"] == -0.5


def test_phase_profile_inline_dict():
    """Test phase_profile with inline dicts parses correctly."""
    yaml_str = """
strategies:
  - name: test
    phase_profile:
      early:  { multiplier: 1.5, bonus: 0.2 }
      mid:    { multiplier: 0.6 }
      late:   { multiplier: 0.3 }
"""
    result = yaml.safe_load(yaml_str)
    profile = result["strategies"][0]["phase_profile"]
    assert profile["early"]["multiplier"] == 1.5
    assert profile["early"]["bonus"] == 0.2
    assert profile["mid"]["multiplier"] == 0.6
    assert profile["late"]["multiplier"] == 0.3
