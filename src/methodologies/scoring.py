"""Strategy scoring using signal weights from YAML configs.

Scores strategies based on detected signals and strategy weights
defined in methodology YAML configs.
"""

from typing import List, Tuple, Dict, Any, Optional
from src.methodologies.registry import StrategyConfig


def score_strategy(
    strategy_config: StrategyConfig,
    signals: Dict[str, Any],
    signal_norms: Optional[Dict[str, float]] = None,
) -> float:
    """
    Score a strategy based on current signals using YAML weights.

    Args:
        strategy_config: Strategy config with signal_weights from YAML
        signals: Dict of detected signals (namespaced)
        signal_norms: Optional dict of signal_key -> max_expected value
                     for normalizing numeric signals. E.g.,
                     {"graph.node_count": 50, "graph.max_depth": 8}

    Returns:
        Score in range [0, 1] (unbounded if multiple weights add up > 1)
    """
    weights = strategy_config.signal_weights
    score = 0.0

    for signal_key, weight in weights.items():
        # Parse signal key (e.g., "llm.response_depth.surface")
        # and match against detected signals
        signal_value = _get_signal_value(signal_key, signals)

        if signal_value is None:
            continue

        if isinstance(signal_value, bool):
            contribution = weight if signal_value else 0.0
        elif isinstance(signal_value, (int, float)):
            normalized = _normalize_numeric(signal_key, signal_value, signal_norms)
            contribution = weight * normalized
        else:
            contribution = 0.0

        score += contribution

    # Return raw score (can be negative or > 1 depending on weights)
    # The comparison matters more than absolute value
    return score


def _normalize_numeric(
    signal_key: str,
    value: float,
    signal_norms: Optional[Dict[str, float]],
) -> float:
    """Normalize a numeric signal value to [0, 1].

    Uses signal_norms max_expected if available, otherwise falls back
    to the legacy /10.0 heuristic for values > 1.
    """
    # Already in [0, 1] range — pass through
    if abs(value) <= 1:
        return value

    # Use per-signal max_expected if available
    if signal_norms and signal_key in signal_norms:
        max_expected = signal_norms[signal_key]
        return min(max(value / max_expected, 0.0), 1.0)

    # Legacy fallback: divide by 10 and clip
    return min(max(value / 10.0, 0.0), 1.0)


def _get_signal_value(signal_key: str, signals: Dict[str, Any]) -> Any:
    """Get signal value by key, handling compound keys.

    Examples:
        - "graph.max_depth" -> signals.get("graph.max_depth")
        - "llm.response_depth.surface" -> Check if signals["llm.response_depth"] == "surface"
    """
    # Direct match
    if signal_key in signals:
        return signals[signal_key]

    # Compound key (e.g., "llm.response_depth.surface")
    # This means: signal "llm.response_depth" should have value "surface"
    if "." in signal_key:
        parts = signal_key.split(".")
        base_signal = ".".join(parts[:-1])  # e.g., "llm.response_depth"
        expected_value = parts[-1]  # e.g., "surface"

        if base_signal in signals:
            actual_value = signals[base_signal]
            # Return True if values match (for boolean scoring)
            return actual_value == expected_value

    return None


def rank_strategies(
    strategy_configs: List[StrategyConfig],
    signals: Dict[str, Any],
    phase_weights: Optional[Dict[str, float]] = None,
    phase_bonuses: Optional[Dict[str, float]] = None,
    signal_norms: Optional[Dict[str, float]] = None,
) -> List[Tuple[StrategyConfig, float]]:
    """
    Rank all strategies by score.

    Args:
        strategy_configs: List of strategy configs from YAML
        signals: Dict of detected signals
        phase_weights: Optional dict of phase-based weight multipliers (e.g., {"deepen": 1.5, "reflect": 0.5})
        phase_bonuses: Optional dict of phase-based additive bonuses (e.g., {"reflect": 0.3})
                        Applied additively: final_score = (base_score * multiplier) + bonus

    Returns:
        List of (strategy_config, score) sorted descending by score
    """
    import structlog

    log = structlog.get_logger(__name__)

    scored = []
    for strategy_config in strategy_configs:
        # Score strategy using signal weights
        base_score = score_strategy(strategy_config, signals, signal_norms=signal_norms)

        # Apply phase weight multiplier if available
        if phase_weights and strategy_config.name in phase_weights:
            multiplier = phase_weights[strategy_config.name]
        else:
            multiplier = 1.0

        # Apply phase bonus additively if available
        bonus = 0.0
        if phase_bonuses and strategy_config.name in phase_bonuses:
            bonus = phase_bonuses[strategy_config.name]

        # Final score: (base_score * multiplier) + bonus
        final_score = (base_score * multiplier) + bonus

        scored.append((strategy_config, final_score))

    # Log scores for debugging
    log.info(
        "strategies_ranked",
        phase=signals.get("meta.interview.phase", "unknown"),
        phase_weights=phase_weights,
        phase_bonuses=phase_bonuses,
        ranked=[(s.name, score) for s, score in scored],
    )

    return scored


def rank_strategy_node_pairs(
    strategies: List[StrategyConfig],
    global_signals: Dict[str, Any],
    node_signals: Dict[str, Dict[str, Any]],
    node_tracker=None,
    phase_weights: Optional[Dict[str, float]] = None,
    phase_bonuses: Optional[Dict[str, float]] = None,
    signal_norms: Optional[Dict[str, float]] = None,
) -> List[Tuple[StrategyConfig, str, float]]:
    """
    Rank (strategy, node) pairs by joint score.

    This function implements the D1 architecture for joint strategy-node
    scoring. It scores each strategy for each node, combining global signals
    with node-specific signals.

    Args:
        strategies: List of strategy configs from YAML
        global_signals: Dict of global detected signals
        node_signals: Dict mapping node_id to node-specific signals
                     {node_id: {signal_name: value}}
        node_tracker: Optional NodeStateTracker for future use
        phase_weights: Optional dict of phase-based weight multipliers
                      {strategy_name: multiplier}
        phase_bonuses: Optional dict of phase-based additive bonuses
                      {strategy_name: bonus}
                      Applied additively: final_score = (base_score * multiplier) + bonus

    Returns:
        List of (strategy_config, node_id, score) sorted descending by score
    """
    scored_pairs: List[Tuple[StrategyConfig, str, float]] = []

    for strategy in strategies:
        for node_id, node_signal_dict in node_signals.items():
            # Merge global + node signals
            # Node signals take precedence when keys overlap
            combined_signals = {**global_signals, **node_signal_dict}

            # Score strategy for this specific node
            base_score = score_strategy(
                strategy, combined_signals, signal_norms=signal_norms
            )

            # Apply phase weight multiplier if available
            multiplier = 1.0
            if phase_weights and strategy.name in phase_weights:
                multiplier = phase_weights[strategy.name]

            # Apply phase bonus additively if available
            bonus = 0.0
            if phase_bonuses and strategy.name in phase_bonuses:
                bonus = phase_bonuses[strategy.name]

            # Final score: (base_score * multiplier) + bonus
            final_score = (base_score * multiplier) + bonus

            scored_pairs.append((strategy, node_id, final_score))

    # Sort by score descending
    return sorted(scored_pairs, key=lambda x: x[2], reverse=True)
