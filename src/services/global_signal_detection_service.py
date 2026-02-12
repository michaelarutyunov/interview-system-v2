"""YAML methodology registry loader."""

import structlog
from pathlib import Path
from typing import Any, Dict, List

from src.core.exceptions import ConfigurationError
from src.signals.signal_registry import ComposedSignalDetector


log = structlog.get_logger(__name__)


class MethodologyRegistry:
    """Registry for loading methodology configurations from YAML."""

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
        self._cache: Dict[str, Any] = {}

    def get_methodology(self, name: str) -> Any:
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

    def list_methodologies(self) -> List[str]:
        """List all available methodology names."""
        yaml_files = list(self.config_dir.glob("*.yaml"))
        return [f.stem for f in yaml_files if f.stem != "schema"]

    def _validate_config(self, config: MethodologyConfig, config_path: Path) -> None:
        """Validate methodology config against known signals and techniques."""
        from src.signals.signal_registry import ComposedSignalDetector

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
            raise ConfigurationError(
                f"Methodology config validation failed for "
                f"'{config_path.name}':\n  - {error_list}"
            )

    def create_signal_detector(
        self, config: MethodologyConfig, llm_client: Optional[Any] = None
    ) -> ComposedSignalDetector:
        """Create a composed signal detector for a methodology.

        Instantiates all signal detectors from methodology config.

        Args:
            config: MethodologyConfig loaded from YAML
            llm_client: Optional LLM client for batch LLM signal detection

        Returns:
            ComposedSignalDetector that detects all methodology signals,
            with LLM client configured for batch signal detection if provided.
        """
        return ComposedSignalDetector(config, llm_client=llm_client)
