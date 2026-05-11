"""YAML methodology registry loader.

Loads methodology definitions from YAML configs and creates
composed signal detectors with signal pools.
"""

import re
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from src.core.logging import get_logger

if TYPE_CHECKING:
    from src.signals.signal_registry import ComposedSignalDetector

log = get_logger(__name__)

# Mirrors NODE_SIGNAL_PREFIXES in src/methodologies/scoring.py.
# Duplicated to avoid a circular import (scoring imports StrategyConfig from here).
# If you change this, update scoring.NODE_SIGNAL_PREFIXES too.
_NODE_SCOPED_PREFIXES: tuple[str, ...] = (
    "convgraph.node.",
    "canongraph.node.",
    "interview.focus.",
    "meta.node.",
)

# Signal weight prefixes that are valid but not in the main signal registry.
# These are session-scoped signals managed separately (e.g., in
# MethodologyStrategyService) rather than through ComposedSignalDetector.
EXTRA_SIGNAL_WEIGHT_PREFIXES = frozenset({"response.semantic.llm.engagement.trend"})

# Valid values for StrategyConfig.focus_mode
VALID_FOCUS_MODES = frozenset({"recent_node", "summary", "topic"})

# Valid values for StrategyConfig.node_binding
VALID_NODE_BINDINGS = frozenset({"required", "none"})

# Valid values for StrategyConfig.bridge_direction
VALID_BRIDGE_DIRECTIONS = frozenset({"forward", "backward"})

# Valid values for StrategyConfig.bridge_target
VALID_BRIDGE_TARGETS = frozenset({"most_concrete", "most_abstract", "either"})

# Valid values for StrategyConfig.extraction_mode
VALID_EXTRACTION_MODES = frozenset({"extract_new", "prefer_existing"})


def _is_valid_signal_weight_key(key: str, known_signals: set[str]) -> bool:
    """Check if a signal weight key has a valid signal prefix.

    Signal weight keys can be:
    - Exact signal name: "convgraph.state.max_depth"
    - Compound key: "response.semantic.llm.response_depth.surface" (base signal + value qualifier)
    - Deep compound: "convgraph.chain.completion.has_complete.false"

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

    Note: Phase boundaries are now automatically calculated from max_turns
    in InterviewPhaseSignal, not configured per-phase in YAML.
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
    signals: dict[str, list[str]]  # graph, llm, temporal, meta
    strategies: list["StrategyConfig"]  # List of strategy definitions
    phases: dict[str, PhaseConfig] | None = None  # phase_name -> config
    chain_completion: dict[str, Any] | None = None  # Chain completion config


@dataclass
class StrategyConfig:
    """Strategy configuration from YAML."""

    name: str
    description: str
    signal_weights: dict[str, float]
    generates_closing_question: bool = False
    focus_mode: str = "recent_node"
    node_binding: str = "required"
    valid_when: str | None = (
        None  # Signal name that must be True for strategy to be scored
    )
    bridge_direction: str = "forward"  # forward: focus→answer, backward: answer→focus
    bridge_target: str = "most_concrete"  # most_concrete, most_abstract, either
    extraction_mode: str = "extract_new"  # extract_new, prefer_existing
    level_guidance: dict[str, str] = field(default_factory=dict)
    probe_guidance: str = ""  # Strategy-specific question generation instruction
    history_includes_last_system_utterance: bool = (
        False  # Prepend last system utterance to history window
    )
    prompt_overrides: dict[str, str] = field(default_factory=dict)


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
                )

        # Parse chain_completion section
        chain_completion = data.get("chain_completion")

        config = MethodologyConfig(
            name=method_data["name"],
            description=method_data.get("description", ""),
            signals=data.get("signals", {}),
            strategies=[
                StrategyConfig(
                    name=s["name"],
                    description=s.get("description", ""),
                    signal_weights=s["signal_weights"],
                    generates_closing_question=s.get(
                        "generates_closing_question", False
                    ),
                    focus_mode=s.get("focus_mode", "recent_node"),
                    node_binding=s.get("node_binding", "required"),
                    valid_when=s.get("valid_when"),
                    bridge_direction=s.get("bridge_direction", "forward"),
                    bridge_target=s.get("bridge_target", "most_concrete"),
                    extraction_mode=s.get("extraction_mode", "extract_new"),
                    level_guidance=s.get("level_guidance", {}),
                    probe_guidance=s.get("probe_guidance", ""),
                    history_includes_last_system_utterance=s.get(
                        "history_includes_last_system_utterance", False
                    ),
                    prompt_overrides=s.get("prompt_overrides", {}),
                )
                for s in data.get("strategies", [])
            ],
            phases=phases,
            chain_completion=chain_completion,
        )

        self._validate_config(config, config_path)

        self._cache[name] = config
        return config

    def _validate_config(self, config: MethodologyConfig, config_path: Path) -> None:
        """Validate methodology config against known signals and techniques.

        Collects all errors and raises a single ValueError listing them all.
        """
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

            if strategy.node_binding not in VALID_NODE_BINDINGS:
                errors.append(
                    f"strategies[{i}] '{strategy.name}': "
                    f"invalid node_binding '{strategy.node_binding}' "
                    f"(valid: {sorted(VALID_NODE_BINDINGS)})"
                )

            if strategy.focus_mode not in VALID_FOCUS_MODES:
                errors.append(
                    f"strategies[{i}] '{strategy.name}': "
                    f"invalid focus_mode '{strategy.focus_mode}' "
                    f"(valid: {sorted(VALID_FOCUS_MODES)})"
                )

            if strategy.bridge_direction not in VALID_BRIDGE_DIRECTIONS:
                errors.append(
                    f"strategies[{i}] '{strategy.name}': "
                    f"invalid bridge_direction '{strategy.bridge_direction}' "
                    f"(valid: {sorted(VALID_BRIDGE_DIRECTIONS)})"
                )

            if strategy.bridge_target not in VALID_BRIDGE_TARGETS:
                errors.append(
                    f"strategies[{i}] '{strategy.name}': "
                    f"invalid bridge_target '{strategy.bridge_target}' "
                    f"(valid: {sorted(VALID_BRIDGE_TARGETS)})"
                )

            if strategy.extraction_mode not in VALID_EXTRACTION_MODES:
                errors.append(
                    f"strategies[{i}] '{strategy.name}': "
                    f"invalid extraction_mode '{strategy.extraction_mode}' "
                    f"(valid: {sorted(VALID_EXTRACTION_MODES)})"
                )

            # Validate valid_when if set
            if strategy.valid_when is not None:
                # valid_when must reference a known signal
                if strategy.valid_when not in known_signals:
                    errors.append(
                        f"strategies[{i}] '{strategy.name}': "
                        f"valid_when references unknown signal '{strategy.valid_when}' "
                        f"(known signals: {sorted(known_signals)})"
                    )
                # valid_with should only be set for node_binding='required' strategies
                if strategy.node_binding == "none":
                    errors.append(
                        f"strategies[{i}] '{strategy.name}': "
                        f"valid_when cannot be set for node_binding='none' strategies "
                        f"(they don't bind to nodes)"
                    )

            # Preventative: warn if a node_binding=none strategy has node-scoped weights.
            # partition_signal_weights() routes those to node_weights, which Stage 1
            # (global scoring) discards — the strategy then competes with reduced mass
            # and appears to "never fire". See CLAUDE.md known failure: "Node binding
            # mismatch silently strips weights".
            if strategy.node_binding == "none":
                stripped = {
                    k: v
                    for k, v in strategy.signal_weights.items()
                    if any(k.startswith(p) for p in _NODE_SCOPED_PREFIXES)
                }
                if stripped:
                    total_mass = sum(abs(v) for v in strategy.signal_weights.values())
                    stripped_mass = sum(abs(v) for v in stripped.values())
                    log.warning(
                        "strategy_weight_routing_mismatch",
                        methodology=config.name,
                        strategy=strategy.name,
                        node_binding=strategy.node_binding,
                        stripped_weight_keys=sorted(stripped.keys()),
                        stripped_mass=round(stripped_mass, 4),
                        total_mass=round(total_mass, 4),
                        stripped_fraction=(
                            round(stripped_mass / total_mass, 4) if total_mass else None
                        ),
                        hint=(
                            "node-scoped weights on node_binding=none strategies are "
                            "discarded; flip node_binding to 'required' or move keys "
                            "to global namespaces."
                        ),
                    )

            for weight_key in strategy.signal_weights:
                if not _is_valid_signal_weight_key(weight_key, known_signals):
                    errors.append(
                        f"strategies[{i}] '{strategy.name}': "
                        f"unknown signal weight key '{weight_key}'"
                    )

                # Guard against unbounded int signals in signal_weights
                # These return raw counts (node_count, edge_count, orphan_count)
                # which can wildly miscalibrate scoring when multiplied by weights
                unbounded_signals = {
                    "convgraph.state.node.count",
                    "convgraph.state.edge.count",
                    "convgraph.state.node.orphan_count",
                }
                # Check if the weight key is or extends an unbounded signal.
                # With deep namespacing (e.g., convgraph.state.node.count),
                # simple 2-component splitting no longer works — use prefix matching.
                is_unbounded = any(
                    weight_key == u or weight_key.startswith(u + ".")
                    for u in unbounded_signals
                )

                if is_unbounded:
                    errors.append(
                        f"strategies[{i}] '{strategy.name}': "
                        f"unbounded count signal '{weight_key}' not allowed in signal_weights. "
                        f"Raw integer counts can't be safely multiplied by weights. "
                        f"Use normalized signals or remove this weight key."
                    )

        # Validate prompt_overrides
        _VALID_OVERRIDE_KEYS = frozenset({"focus_framing", "final_instruction"})
        _VALID_OVERRIDE_VARS = frozenset(
            {
                "focus_concept",
                "focus_node_type",
                "level_info",
                "focus_source_quote",
                "topic",
            }
        )
        for i, strategy in enumerate(config.strategies):
            for key, value in strategy.prompt_overrides.items():
                if key not in _VALID_OVERRIDE_KEYS:
                    errors.append(
                        f"strategies[{i}] '{strategy.name}': "
                        f"prompt_overrides has unknown key '{key}' "
                        f"(valid keys: {sorted(_VALID_OVERRIDE_KEYS)})"
                    )
                var_names = re.findall(r"\{([a-zA-Z_]+)\}", value)
                for var in var_names:
                    if var not in _VALID_OVERRIDE_VARS:
                        errors.append(
                            f"strategies[{i}] '{strategy.name}': "
                            f"prompt_overrides['{key}'] references unknown substitution "
                            f"variable '{{{var}}}' "
                            f"(valid variables: {sorted(_VALID_OVERRIDE_VARS)})"
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
                f"Methodology config validation failed for '{config_path.name}':\n  - {error_list}"
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
        from src.signals.signal_registry import ComposedSignalDetector

        # Collect all signal names from all pools
        signal_names: list[str] = []
        for pool_signals in config.signals.values():
            signal_names.extend(pool_signals)

        return ComposedSignalDetector(signal_names)
