"""Tests for YAML methodology config validation."""

import pytest

from src.methodologies.registry import (
    MethodologyRegistry,
    _is_valid_signal_weight_key,
)
from src.methodologies.signals.registry import ComposedSignalDetector


class TestGetKnownSignalNames:
    """Test the public get_known_signal_names classmethod."""

    def test_returns_nonempty_set(self):
        names = ComposedSignalDetector.get_known_signal_names()
        assert isinstance(names, set)
        assert len(names) >= 20

    def test_contains_expected_graph_signals(self):
        names = ComposedSignalDetector.get_known_signal_names()
        assert "graph.node_count" in names
        assert "graph.max_depth" in names
        assert "graph.node.exhausted" in names

    def test_contains_expected_llm_signals(self):
        names = ComposedSignalDetector.get_known_signal_names()
        assert "llm.response_depth" in names
        assert "llm.sentiment" in names

    def test_contains_expected_meta_signals(self):
        names = ComposedSignalDetector.get_known_signal_names()
        assert "meta.interview.phase" in names
        assert "meta.interview_progress" in names

    def test_contains_node_level_signals(self):
        names = ComposedSignalDetector.get_known_signal_names()
        assert "graph.node.focus_streak" in names
        assert "meta.node.opportunity" in names
        assert "technique.node.strategy_repetition" in names


class TestCompoundKeyPrefixMatching:
    """Test _is_valid_signal_weight_key helper."""

    @pytest.fixture
    def known(self):
        return ComposedSignalDetector.get_known_signal_names()

    def test_exact_match(self, known):
        assert _is_valid_signal_weight_key("graph.node_count", known)

    def test_compound_two_part_qualifier(self, known):
        assert _is_valid_signal_weight_key("llm.response_depth.surface", known)

    def test_compound_deep_qualifier(self, known):
        assert _is_valid_signal_weight_key(
            "graph.chain_completion.has_complete_chain.false", known
        )

    def test_node_level_compound(self, known):
        assert _is_valid_signal_weight_key("graph.node.exhausted.false", known)

    def test_extra_prefix_global_response_trend(self, known):
        assert _is_valid_signal_weight_key("llm.global_response_trend.fatigued", known)

    def test_invalid_signal(self, known):
        assert not _is_valid_signal_weight_key("graph.edge_density", known)

    def test_completely_unknown(self, known):
        assert not _is_valid_signal_weight_key("foo.bar.baz", known)

    def test_empty_string(self, known):
        assert not _is_valid_signal_weight_key("", known)


class TestAllMethodologiesPassValidation:
    """Integration: all shipped YAML configs load without validation errors."""

    def test_means_end_chain(self):
        registry = MethodologyRegistry()
        config = registry.get_methodology("means_end_chain")
        assert config.name == "means_end_chain"
        assert len(config.strategies) >= 4

    def test_jobs_to_be_done(self):
        registry = MethodologyRegistry()
        config = registry.get_methodology("jobs_to_be_done")
        assert config.name == "jobs_to_be_done"

    def test_critical_incident(self):
        registry = MethodologyRegistry()
        config = registry.get_methodology("critical_incident")
        assert config.name == "critical_incident"

    def test_repertory_grid(self):
        registry = MethodologyRegistry()
        config = registry.get_methodology("repertory_grid")
        assert config.name == "repertory_grid"

    def test_customer_journey_mapping_loads_gracefully(self):
        """Incomplete config loads without errors (empty strategies)."""
        registry = MethodologyRegistry()
        config = registry.get_methodology("customer_journey_mapping")
        assert config.name == "customer_journey_mapping"
        assert len(config.strategies) == 0

    def test_all_methodologies_load(self):
        """Every YAML file in config/methodologies/ loads."""
        registry = MethodologyRegistry()
        for name in registry.list_methodologies():
            config = registry.get_methodology(name)
            assert config.name == name


class TestValidationCatchesBadConfigs:
    """Test that validation rejects invalid configurations."""

    def test_unknown_signal_in_signals_dict(self, tmp_path):
        yaml_content = """
method:
  name: test_bad
signals:
  graph:
    - graph.nonexistent_signal
strategies: []
"""
        (tmp_path / "test_bad.yaml").write_text(yaml_content)
        registry = MethodologyRegistry(config_dir=tmp_path)
        with pytest.raises(
            ValueError, match="unknown signal 'graph.nonexistent_signal'"
        ):
            registry.get_methodology("test_bad")

    def test_unknown_technique(self, tmp_path):
        yaml_content = """
method:
  name: test_bad_technique
signals: {}
strategies:
  - name: strat1
    technique: nonexistent_technique
    signal_weights:
      graph.node_count: 1.0
"""
        (tmp_path / "test_bad_technique.yaml").write_text(yaml_content)
        registry = MethodologyRegistry(config_dir=tmp_path)
        with pytest.raises(
            ValueError, match="unknown technique 'nonexistent_technique'"
        ):
            registry.get_methodology("test_bad_technique")

    def test_unknown_signal_weight_key(self, tmp_path):
        yaml_content = """
method:
  name: test_bad_weight
signals: {}
strategies:
  - name: strat1
    technique: probing
    signal_weights:
      grph.node_count: 1.0
"""
        (tmp_path / "test_bad_weight.yaml").write_text(yaml_content)
        registry = MethodologyRegistry(config_dir=tmp_path)
        with pytest.raises(
            ValueError, match="unknown signal weight key 'grph.node_count'"
        ):
            registry.get_methodology("test_bad_weight")

    def test_phase_references_unknown_strategy(self, tmp_path):
        yaml_content = """
method:
  name: test_bad_phase
signals: {}
strategies:
  - name: real_strategy
    technique: probing
    signal_weights:
      graph.node_count: 1.0
phases:
  early:
    description: test
    signal_weights:
      ghost_strategy: 1.5
    phase_bonuses: {}
"""
        (tmp_path / "test_bad_phase.yaml").write_text(yaml_content)
        registry = MethodologyRegistry(config_dir=tmp_path)
        with pytest.raises(ValueError, match="unknown strategy 'ghost_strategy'"):
            registry.get_methodology("test_bad_phase")

    def test_duplicate_strategy_names(self, tmp_path):
        yaml_content = """
method:
  name: test_dup
signals: {}
strategies:
  - name: strat1
    technique: probing
    signal_weights:
      graph.node_count: 1.0
  - name: strat1
    technique: laddering
    signal_weights:
      graph.max_depth: 1.0
"""
        (tmp_path / "test_dup.yaml").write_text(yaml_content)
        registry = MethodologyRegistry(config_dir=tmp_path)
        with pytest.raises(ValueError, match="duplicate strategy name 'strat1'"):
            registry.get_methodology("test_dup")

    def test_unknown_signal_norm_key(self, tmp_path):
        yaml_content = """
method:
  name: test_bad_norm
signals: {}
strategies: []
signal_norms:
  graph.fake_signal: 10.0
"""
        (tmp_path / "test_bad_norm.yaml").write_text(yaml_content)
        registry = MethodologyRegistry(config_dir=tmp_path)
        with pytest.raises(ValueError, match="unknown signal 'graph.fake_signal'"):
            registry.get_methodology("test_bad_norm")

    def test_multiple_errors_reported(self, tmp_path):
        yaml_content = """
method:
  name: test_multi_error
signals:
  graph:
    - graph.fake_signal
strategies:
  - name: strat1
    technique: fake_technique
    signal_weights:
      fake.weight: 1.0
"""
        (tmp_path / "test_multi_error.yaml").write_text(yaml_content)
        registry = MethodologyRegistry(config_dir=tmp_path)
        with pytest.raises(ValueError) as exc_info:
            registry.get_methodology("test_multi_error")
        error_msg = str(exc_info.value)
        assert "graph.fake_signal" in error_msg
        assert "fake_technique" in error_msg
        assert "fake.weight" in error_msg

    def test_valid_config_passes(self, tmp_path):
        yaml_content = """
method:
  name: test_valid
signals:
  graph:
    - graph.node_count
    - graph.max_depth
strategies:
  - name: explore
    technique: elaboration
    signal_weights:
      graph.node_count: 0.8
      llm.response_depth.surface: 0.6
phases:
  early:
    description: test
    signal_weights:
      explore: 1.2
    phase_bonuses:
      explore: 0.1
signal_norms:
  graph.node_count: 50
"""
        (tmp_path / "test_valid.yaml").write_text(yaml_content)
        registry = MethodologyRegistry(config_dir=tmp_path)
        config = registry.get_methodology("test_valid")
        assert config.name == "test_valid"
        assert len(config.strategies) == 1

    def test_numeric_signal_without_norm_allowed_at_load_time(self, tmp_path):
        """Load-time validation does NOT check norm coverage.

        Norm enforcement happens at runtime in _normalize_numeric() when
        a signal value >1 is encountered without a matching norm entry.
        This avoids false positives for signals naturally bounded to [0,1].
        """
        yaml_content = """
method:
  name: test_no_norm_coverage
signals: {}
strategies:
  - name: strat1
    technique: probing
    signal_weights:
      graph.node_count: 0.8
      graph.max_depth: 0.5
signal_norms:
  graph.node_count: 50
"""
        (tmp_path / "test_no_norm_coverage.yaml").write_text(yaml_content)
        registry = MethodologyRegistry(config_dir=tmp_path)
        config = registry.get_methodology("test_no_norm_coverage")
        assert config.name == "test_no_norm_coverage"
