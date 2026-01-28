"""YAML methodology registry loader.

Loads methodology definitions from YAML configs and creates
composed signal detectors with signal pools.
"""

import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.methodologies.signals.registry import ComposedSignalDetector


@dataclass
class MethodologyConfig:
    """Loaded methodology configuration."""

    name: str
    description: str
    signals: dict[str, list[str]]  # graph, llm, temporal, meta
    strategies: list["StrategyConfig"]  # List of strategy definitions


@dataclass
class StrategyConfig:
    """Strategy configuration from YAML."""

    name: str
    technique: str
    signal_weights: dict[str, float]
    focus_preference: str


class MethodologyRegistry:
    """Registry for loading methodology configurations from YAML.

    Replaces the old folder-per-methodology approach with:
    - YAML configs for methodology definitions
    - Composed signal detectors from shared pools
    - Technique instances referenced by name

    Example:
        registry = MethodologyRegistry()
        config = registry.get_methodology("means_end_chain")
        signal_detector = registry.create_signal_detector(config)
    """

    def __init__(self, config_dir: str | Path | None = None):
        """Initialize registry with config directory.

        Args:
            config_dir: Path to YAML config directory (default: src/methodologies/config)
        """
        if config_dir is None:
            # Default to src/methodologies/config relative to this file
            this_file = Path(__file__)
            config_dir = this_file.parent / "config"

        self.config_dir = Path(config_dir)
        self._cache: dict[str, MethodologyConfig] = {}

    def get_methodology(self, name: str) -> MethodologyConfig:
        """Get methodology configuration by name.

        Args:
            name: Methodology name (e.g., "means_end_chain")

        Returns:
            MethodologyConfig with signals and strategies

        Raises:
            ValueError: If methodology config not found
        """
        if name in self._cache:
            return self._cache[name]

        config_path = self.config_dir / f"{name}.yaml"
        if not config_path.exists():
            raise ValueError(f"Methodology config not found: {config_path}")

        with open(config_path) as f:
            data = yaml.safe_load(f)

        config = MethodologyConfig(
            name=data["methodology"]["name"],
            description=data["methodology"]["description"],
            signals=data["methodology"]["signals"],
            strategies=[
                StrategyConfig(
                    name=s["name"],
                    technique=s["technique"],
                    signal_weights=s["signal_weights"],
                    focus_preference=s["focus_preference"],
                )
                for s in data["methodology"]["strategies"]
            ],
        )

        self._cache[name] = config
        return config

    def list_methodologies(self) -> list[str]:
        """List all available methodology names."""
        yaml_files = list(self.config_dir.glob("*.yaml"))
        return [f.stem for f in yaml_files if f.stem != "schema"]

    def create_signal_detector(
        self, config: MethodologyConfig
    ) -> "ComposedSignalDetector":
        """Create a composed signal detector for a methodology.

        Instantiates all signal detectors from the methodology config.

        Args:
            config: MethodologyConfig loaded from YAML

        Returns:
            ComposedSignalDetector that detects all methodology signals
        """
        from src.methodologies.signals.registry import ComposedSignalDetector

        # Collect all signal names from all pools
        signal_names: list[str] = []
        for pool_signals in config.signals.values():
            signal_names.extend(pool_signals)

        return ComposedSignalDetector(signal_names)

    def get_technique(self, technique_name: str):
        """Get a technique instance by name.

        Args:
            technique_name: Name of technique (e.g., "laddering")

        Returns:
            Technique instance

        Raises:
            ValueError: If technique not found
        """
        from src.methodologies.techniques import (
            LadderingTechnique,
            ElaborationTechnique,
            ProbingTechnique,
            ValidationTechnique,
        )

        techniques = {
            "laddering": LadderingTechnique,
            "elaboration": ElaborationTechnique,
            "probing": ProbingTechnique,
            "validation": ValidationTechnique,
        }

        technique_class = techniques.get(technique_name)
        if not technique_class:
            raise ValueError(f"Unknown technique: {technique_name}")

        return technique_class()
