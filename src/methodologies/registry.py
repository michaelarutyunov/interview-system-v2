"""YAML methodology registry loader.

Loads methodology definitions from YAML configs and creates
composed signal detectors with signal pools.
"""

import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.signals.signal_registry import ComposedSignalDetector

# Signal weight prefixes that are valid but not in the main signal registry.
# These are session-scoped signals managed separately (e.g., in
# MethodologyStrategyService) rather than through ComposedSignalDetector.
EXTRA_SIGNAL_WEIGHT_PREFIXES = frozenset({"llm.global_response_trend"})


def _is_valid_signal_weight_key(key: str, known_signals: set[str]) -> bool:
    """Check if a signal weight key has a valid signal prefix.

    Signal weight keys can be:
    - Exact signal name: "graph.max_depth"
    - Compound key: "llm.response_depth.surface" (base signal + value qualifier)
    - Deep compound: "graph.chain_completion.has_complete.false"

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


@dataclass
class MethodologyConfig:
    """Loaded methodology configuration."""

    name: str
    description: str
    strategies: list["StrategyConfig"]  # List of strategy definitions
    phases: dict[str, PhaseConfig]  # phase_name -> config (built from phase_profile)
    phase_boundaries: dict[str, int]  # phase_name -> max_turns


@dataclass
class StrategyConfig:
    """Strategy configuration from YAML."""

    name: str
    description: str
    signal_weights: dict[str, float]
    generates_closing_question: bool = False
    node_type_priorities: dict[str, float] = field(default_factory=dict)
    phase_profile: dict[str, dict[str, float]] | None = None  # phase_name -> {multiplier, bonus}


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

        # Load phase_boundaries
        phase_boundaries_data = data.get("phase_boundaries", {})
        phase_boundaries: dict[str, int] = {}

        # First, try new phase_boundaries format
        for phase_name, boundary_dict in phase_boundaries_data.items():
            if isinstance(boundary_dict, dict):
                # Extract max_turns from nested dict
                for key, value in boundary_dict.items():
                    if "max_turns" in key:
                        phase_boundaries[phase_name] = value
            elif isinstance(boundary_dict, int):
                phase_boundaries[phase_name] = boundary_dict

        # Fallback: extract from old phases section (migration compatibility)
        if not phase_boundaries and "phases" in data:
            for phase_name, phase_data in data["phases"].items():
                if "phase_boundaries" in phase_data:
                    boundaries = phase_data["phase_boundaries"]
                    if isinstance(boundaries, dict):
                        for key, value in boundaries.items():
                            if "max_turns" in key:
                                phase_boundaries[phase_name] = value

        # Load strategies with phase_profile
        strategies = [
            StrategyConfig(
                name=s["name"],
                description=s.get("description", ""),
                signal_weights=s["signal_weights"],
                generates_closing_question=s.get(
                    "generates_closing_question", False
                ),
                node_type_priorities=s.get("node_type_priorities", {}),
                phase_profile=s.get("phase_profile"),
            )
            for s in data.get("strategies", [])
        ]

        # Build phases from strategy phase_profile entries
        phases = self._build_phase_configs_from_strategies(
            strategies, phase_boundaries, data.get("phases", {})
        )

        config = MethodologyConfig(
            name=method_data["name"],
            description=method_data.get("description", ""),
            strategies=strategies,
            phases=phases,
            phase_boundaries=phase_boundaries,
        )

        self._validate_config(config, config_path)

        self._cache[name] = config
        return config

    def _build_phase_configs_from_strategies(
        self,
        strategies: list[StrategyConfig],
        phase_boundaries: dict[str, int],
        phases_fallback: dict,
    ) -> dict[str, PhaseConfig]:
        """Build per-phase configs from per-strategy phase_profile entries.

        Inverts the data from:
          strategies[].phase_profile[phase] = {multiplier, bonus}
        To:
          phases[phase].signal_weights[strategy] = multiplier
          phases[phase].phase_bonuses[strategy] = bonus

        Args:
            strategies: List of strategies with phase_profile entries
            phase_boundaries: Phase name -> max_turns mapping
            phases_fallback: Fallback phases dict for description/migration

        Returns:
            Dict mapping phase_name -> PhaseConfig
        """
        phases: dict[str, PhaseConfig] = {}

        # Collect all unique phase names from strategy phase_profile entries
        phase_names: set[str] = set()
        for strategy in strategies:
            if strategy.phase_profile:
                phase_names.update(strategy.phase_profile.keys())

        # If no phase_profile found, fall back to old phases section
        if not phase_names and phases_fallback:
            for phase_name, phase_data in phases_fallback.items():
                phases[phase_name] = PhaseConfig(
                    name=phase_name,
                    description=phase_data.get("description", ""),
                    signal_weights=phase_data.get("signal_weights", {}),
                    phase_bonuses=phase_data.get("phase_bonuses", {}),
                )
            return phases

        # Build phases from strategy phase_profile entries
        for phase_name in phase_names:
            signal_weights: dict[str, float] = {}
            phase_bonuses: dict[str, float] = {}

            for strategy in strategies:
                if strategy.phase_profile and phase_name in strategy.phase_profile:
                    profile_entry = strategy.phase_profile[phase_name]
                    multiplier = profile_entry.get("multiplier", 1.0)
                    bonus = profile_entry.get("bonus", 0.0)

                    if multiplier != 1.0:
                        signal_weights[strategy.name] = multiplier
                    if bonus != 0.0:
                        phase_bonuses[strategy.name] = bonus

            # Get description from fallback if available
            description = ""
            if phase_name in phases_fallback:
                description = phases_fallback[phase_name].get("description", "")

            phases[phase_name] = PhaseConfig(
                name=phase_name,
                description=description,
                signal_weights=signal_weights,
                phase_bonuses=phase_bonuses,
            )

        return phases

    def _validate_config(self, config: MethodologyConfig, config_path: Path) -> None:
        """Validate methodology config against known signals and techniques.

        Collects all errors and raises a single ValueError listing them all.
        """
        from src.signals.signal_registry import ComposedSignalDetector

        errors: list[str] = []
        known_signals = ComposedSignalDetector.get_known_signal_names()

        # Collect defined strategy names
        strategy_names: set[str] = set()

        # 1. Validate strategies
        for i, strategy in enumerate(config.strategies):
            if strategy.name in strategy_names:
                errors.append(
                    f"strategies[{i}]: duplicate strategy name '{strategy.name}'"
                )
            strategy_names.add(strategy.name)

            for weight_key in strategy.signal_weights:
                if not _is_valid_signal_weight_key(weight_key, known_signals):
                    # Enhance error with available signals for discoverability
                    available = ", ".join(sorted(known_signals)[:10])
                    if len(known_signals) > 10:
                        available += f", ... ({len(known_signals)} total)"
                    errors.append(
                        f"strategies[{i}] '{strategy.name}': "
                        f"unknown signal weight key '{weight_key}' "
                        f"(available: {available})"
                    )

        # 2. Validate phase_profile phase names against phase_boundaries
        for i, strategy in enumerate(config.strategies):
            if strategy.phase_profile:
                for phase_name in strategy.phase_profile:
                    if phase_name not in config.phase_boundaries:
                        errors.append(
                            f"strategies[{i}] '{strategy.name}': "
                            f"phase_profile references unknown phase '{phase_name}' "
                            f"(defined phases: {sorted(config.phase_boundaries.keys())})"
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

        Collects signal names from strategy signal_weights.

        Args:
            config: MethodologyConfig loaded from YAML

        Returns:
            ComposedSignalDetector that detects all methodology signals
        """
        from src.signals.signal_registry import ComposedSignalDetector

        # Collect all signal names from strategy signal_weights
        # Extract the base signal name from compound keys like "llm.response_depth.surface"
        signal_names: set[str] = set()
        for strategy in config.strategies:
            for weight_key in strategy.signal_weights:
                # Extract base signal name by progressively shortening the key
                parts = weight_key.split(".")
                for i in range(len(parts), 0, -1):
                    prefix = ".".join(parts[:i])
                    # Check if this is a known signal (will validate below)
                    # For now, collect all potential prefixes
                    signal_names.add(prefix)

        # Filter to only known global signals (exclude node-level signals that
        # require NodeStateTracker — those are handled by NodeSignalDetectionService)
        from src.signals.signal_base import SignalDetector

        known_signals = ComposedSignalDetector.get_known_signal_names()
        valid_signals = [
            s
            for s in signal_names
            if s in known_signals
            and not getattr(SignalDetector.get_signal_class(s), "requires_node_tracker", False)
        ]

        return ComposedSignalDetector(valid_signals)
