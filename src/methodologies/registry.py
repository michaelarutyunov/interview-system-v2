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
class PhaseConfig:
    """Configuration for an interview phase.

    Defines signal weight multipliers for a specific interview phase.
    These multipliers are applied on top of base strategy weights.
    """

    name: str
    description: str
    signal_weights: dict[str, float]  # strategy_name -> multiplier


@dataclass
class MethodologyConfig:
    """Loaded methodology configuration."""

    name: str
    description: str
    signals: dict[str, list[str]]  # graph, llm, temporal, meta
    strategies: list["StrategyConfig"]  # List of strategy definitions
    phases: dict[str, PhaseConfig] | None = None  # phase_name -> config
    signal_norms: dict[str, float] | None = None  # signal_key -> max_expected


@dataclass
class StrategyConfig:
    """Strategy configuration from YAML."""

    name: str
    description: str
    technique: str
    signal_weights: dict[str, float]


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
            config_dir: Path to YAML config directory (default: config/methodologies)
        """
        if config_dir is None:
            # Default to config/methodologies relative to project root
            this_file = Path(__file__)
            project_root = this_file.parent.parent.parent
            config_dir = project_root / "config" / "methodologies"

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

        # Handle both new unified format and legacy format
        # New format has 'method' key at top level
        # Legacy format has 'methodology' key at top level
        if "method" in data:
            # New unified format
            method_data = data["method"]
        elif "methodology" in data:
            # Legacy format
            method_data = data["methodology"]
        else:
            raise ValueError(
                f"Invalid methodology config format: {config_path}. "
                "Expected 'method' or 'methodology' key."
            )

        # Load phases if present
        phases = None
        if "phases" in data:
            phases = {}
            for phase_name, phase_data in data["phases"].items():
                phases[phase_name] = PhaseConfig(
                    name=phase_name,
                    description=phase_data.get("description", ""),
                    signal_weights=phase_data.get("signal_weights", {}),
                )

        # Load signal_norms if present
        raw_norms = data.get("signal_norms", None)
        signal_norms = (
            {k: float(v) for k, v in raw_norms.items()} if raw_norms else None
        )

        config = MethodologyConfig(
            name=method_data["name"],
            description=method_data.get("description", ""),
            signals=data.get("signals", {}),
            strategies=[
                StrategyConfig(
                    name=s["name"],
                    description=s.get("description", ""),
                    technique=s["technique"],
                    signal_weights=s["signal_weights"],
                )
                for s in data.get("strategies", [])
            ],
            phases=phases,
            signal_norms=signal_norms,
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
