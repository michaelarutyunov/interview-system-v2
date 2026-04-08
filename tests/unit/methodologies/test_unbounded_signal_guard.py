"""Test that methodology registry rejects unbounded int signals in signal_weights."""

import pytest
import tempfile
from pathlib import Path
import shutil

from src.methodologies.registry import MethodologyRegistry


class TestUnboundedSignalGuard:
    """Test runtime guard against unbounded int signals in YAML signal_weights."""

    def test_rejects_graph_node_count_in_signal_weights(self):
        """graph.node_count should be rejected in signal_weights."""
        yaml_content = """
method:
  name: test
  version: "1.0"
  goal: Test

signals:
  graph:
    - graph.node_count

strategies:
  - name: test_strategy
    description: Test
    signal_weights:
      graph.node_count: 0.5  # Should be rejected!
    focus_mode: recent_node
    node_binding: required
"""
        temp_dir = tempfile.mkdtemp()
        try:
            config_dir = Path(temp_dir)
            config_file = config_dir / "test.yaml"
            config_file.write_text(yaml_content)

            registry = MethodologyRegistry(config_dir)

            with pytest.raises(ValueError, match="unbounded count signal.*graph.node_count"):
                registry.get_methodology("test")
        finally:
            shutil.rmtree(temp_dir)

    def test_rejects_graph_edge_count_in_signal_weights(self):
        """graph.edge_count should be rejected in signal_weights."""
        yaml_content = """
method:
  name: test
  version: "1.0"
  goal: Test

signals:
  graph:
    - graph.edge_count

strategies:
  - name: test_strategy
    description: Test
    signal_weights:
      graph.edge_count: 0.3  # Should be rejected!
    focus_mode: recent_node
    node_binding: required
"""
        temp_dir = tempfile.mkdtemp()
        try:
            config_dir = Path(temp_dir)
            config_file = config_dir / "test.yaml"
            config_file.write_text(yaml_content)

            registry = MethodologyRegistry(config_dir)

            with pytest.raises(ValueError, match="unbounded count signal.*graph.edge_count"):
                registry.get_methodology("test")
        finally:
            shutil.rmtree(temp_dir)

    def test_rejects_graph_orphan_count_in_signal_weights(self):
        """graph.orphan_count should be rejected in signal_weights."""
        yaml_content = """
method:
  name: test
  version: "1.0"
  goal: Test

signals:
  graph:
    - graph.orphan_count

strategies:
  - name: test_strategy
    description: Test
    signal_weights:
      graph.orphan_count.low: 0.2  # Should be rejected even with suffix!
    focus_mode: recent_node
    node_binding: required
"""
        temp_dir = tempfile.mkdtemp()
        try:
            config_dir = Path(temp_dir)
            config_file = config_dir / "test.yaml"
            config_file.write_text(yaml_content)

            registry = MethodologyRegistry(config_dir)

            with pytest.raises(ValueError, match="unbounded count signal.*graph.orphan_count"):
                registry.get_methodology("test")
        finally:
            shutil.rmtree(temp_dir)

    def test_allows_normalized_signals_in_signal_weights(self):
        """Normalized [0,1] signals should still be allowed."""
        yaml_content = """
method:
  name: test
  version: "1.0"
  goal: Test

signals:
  graph:
    - graph.max_depth

strategies:
  - name: test_strategy
    description: Test
    signal_weights:
      graph.max_depth.high: 0.5
      graph.max_depth.low: -0.3
    focus_mode: recent_node
    node_binding: required
"""
        temp_dir = tempfile.mkdtemp()
        try:
            config_dir = Path(temp_dir)
            config_file = config_dir / "test.yaml"
            config_file.write_text(yaml_content)

            registry = MethodologyRegistry(config_dir)
            config = registry.get_methodology("test")

            assert config is not None
            assert config.name == "test"
        finally:
            shutil.rmtree(temp_dir)
