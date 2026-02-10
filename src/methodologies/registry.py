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

# Signal weight prefixes that are valid but not in the main signal registry.
# These are session-scoped signals managed separately (e.g., in
# MethodologyStrategyService) rather than through ComposedSignalDetector.
EXTRA_SIGNAL_WEIGHT_PREFIXES = frozenset({"llm.global_response_trend"})


def _is_valid_signal_weight_key(key: str, known_signals: set[str]) -> bool:
    """Check if a signal weight key has a valid signal prefix.

    Signal weight keys can be:
    - Exact signal name: "graph.max_depth"
    - Compound key: "llm.response_depth.surface" (base signal + value qualifier)
    - Deep compound: "graph.chain_completion.has_complete_chain.false"

    Tries progressively shorter prefixes until one matches a known signal
    or an allowed extra prefix.
    """
    if key in known_signals or key in EXTRA_SIGNAL_WEIGHT_PREFIXES:
        return True

    parts = key.split(".")
    for i in range(len(parts) - 1, 0, -1):
        prefix = ".".join(parts[:i])
        if prefix in known_signals or prefix in EXTRA_SIGNAL_WEIGHT_PREFIXES:
            return True

    return False


@dataclass
class PhaseConfig:
    """Configuration for an interview phase.

    Defines signal weight multipliers for a specific interview phase.
    These multipliers are applied on top of base strategy weights.
    """

    name: str
    description: str
    signal_weights: dict[str, float]  # strategy_name -> multiplier
    phase_bonuses: dict[str, float]  # strategy_name -> additive bonus
    phase_boundaries: dict[str, int] | None = None  # phase_boundary_key -> value


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
    signal_weights: dict[str, float]


class MethodologyRegistry:
    """Registry for loading methodology configurations from YAML.

    Loads methodology definitions from YAML configs and creates
    composed signal detectors with signal pools.

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
            ValueError: If methodology config not found or validation fails
        """
        if name in self._cache:
            return self._cache[name]

        config_path = self.config_dir / f"{name}.yaml"
        if not config_path.exists():
            raise ValueError(f"Methodology config not found: {config_path}")

        with open(config_path) as f:
            data = yaml.safe_load(f)

        method_data = data["method"]

        # Load phases if present
        phases = None
        if "phases" in data:
            phases = {}
            for phase_name, phase_data in data["phases"].items():
                phases[phase_name] = PhaseConfig(
                    name=phase_name,
                    description=phase_data.get("description", ""),
                    signal_weights=phase_data.get("signal_weights", {}),
                    phase_bonuses=phase_data.get("phase_bonuses", {}),
                    phase_boundaries=phase_data.get("phase_boundaries"),
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
                    signal_weights=s["signal_weights"],
                )
                for s in data.get("strategies", [])
            ],
            phases=phases,
            signal_norms=signal_norms,
        )

        self._validate_config(config, config_path)

        self._cache[name] = config
        return config

    def _validate_config(self, config: MethodologyConfig, config_path: Path) -> None:
        """Validate methodology config against known signals and techniques.

        Collects all errors and raises a single ValueError listing them all.
        """
        from src.methodologies.signals.registry import ComposedSignalDetector

        errors: list[str] = []
        known_signals = ComposedSignalDetector.get_known_signal_names()

        # Collect defined strategy names
        strategy_names: set[str] = set()

        # 1. Validate signals in signals: dict
        for pool_name, signal_list in config.signals.items():
            for signal_name in signal_list:
                if signal_name not in known_signals:
                    errors.append(
                        f"signals.{pool_name}: unknown signal '{signal_name}'"
                    )

        # 2. Validate strategies
        for i, strategy in enumerate(config.strategies):
            if strategy.name in strategy_names:
                errors.append(
                    f"strategies[{i}]: duplicate strategy name '{strategy.name}'"
                )
            strategy_names.add(strategy.name)

            for weight_key in strategy.signal_weights:
                if not _is_valid_signal_weight_key(weight_key, known_signals):
                    errors.append(
                        f"strategies[{i}] '{strategy.name}': "
                        f"unknown signal weight key '{weight_key}'"
                    )

        # 3. Validate phases reference defined strategies
        if config.phases:
            for phase_name, phase_config in config.phases.items():
                for key in phase_config.signal_weights:
                    if key not in strategy_names:
                        errors.append(
                            f"phases.{phase_name}.signal_weights: "
                            f"unknown strategy '{key}' "
                            f"(defined: {sorted(strategy_names)})"
                        )
                for key in phase_config.phase_bonuses:
                    if key not in strategy_names:
                        errors.append(
                            f"phases.{phase_name}.phase_bonuses: "
                            f"unknown strategy '{key}' "
                            f"(defined: {sorted(strategy_names)})"
                        )

        # 4. Validate signal_norms keys
        if config.signal_norms:
            for norm_key in config.signal_norms:
                if norm_key not in known_signals:
                    errors.append(f"signal_norms: unknown signal '{norm_key}'")

        if errors:
            error_list = "\n  - ".join(errors)
            raise ValueError(
                f"Methodology config validation failed for "
                f"'{config_path.name}':\n  - {error_list}"
            )

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
