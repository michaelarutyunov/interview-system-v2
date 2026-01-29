"""Strategy scoring using signal weights from YAML configs.

Scores strategies based on detected signals and strategy weights
defined in methodology YAML configs.
"""

from typing import List, Tuple, Dict, Any, Optional
from src.methodologies.registry import StrategyConfig


def score_strategy(
    strategy_config: StrategyConfig,
    signals: Dict[str, Any],
) -> float:
    """
    Score a strategy based on current signals using YAML weights.

    Args:
        strategy_config: Strategy config with signal_weights from YAML
        signals: Dict of detected signals (namespaced)

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
            # For counts/ratios, normalize if likely > 1
            # Heuristic: if value > 1, normalize by assuming max of 10
            if abs(signal_value) > 1:
                normalized = min(max(signal_value / 10.0, 0.0), 1.0)
                contribution = weight * normalized
            else:
                contribution = weight * signal_value
        else:
            contribution = 0.0

        score += contribution

    # Return raw score (can be negative or > 1 depending on weights)
    # The comparison matters more than absolute value
    return score


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
) -> List[Tuple[StrategyConfig, float]]:
    """
    Rank all strategies by score.

    Args:
        strategy_configs: List of strategy configs from YAML
        signals: Dict of detected signals
        phase_weights: Optional dict of phase-based weight multipliers (e.g., {"deepen": 1.5, "reflect": 0.5})

    Returns:
        List of (strategy_config, score) sorted descending by score
    """
    import structlog
    log = structlog.get_logger(__name__)

    scored = []
    for strategy_config in strategy_configs:
        # Score strategy using signal weights
        base_score = score_strategy(strategy_config, signals)

        # Apply phase weight multiplier if available
        if phase_weights and strategy_config.name in phase_weights:
            multiplier = phase_weights[strategy_config.name]
            final_score = base_score * multiplier
        else:
            multiplier = 1.0
            final_score = base_score

        scored.append((strategy_config, final_score))

    # Log scores for debugging
    log.info(
        "strategies_ranked",
        phase=signals.get("meta.interview.phase", "unknown"),
        phase_weights=phase_weights,
        ranked=[(s.name, score) for s, score in scored],
    )

    return scored


def rank_strategy_node_pairs(
    strategies: List[StrategyConfig],
    global_signals: Dict[str, Any],
    node_signals: Dict[str, Dict[str, Any]],
    node_tracker=None,
    phase_weights: Optional[Dict[str, float]] = None,
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
            score = score_strategy(strategy, combined_signals)

            # Apply phase weight multiplier if available
            if phase_weights and strategy.name in phase_weights:
                multiplier = phase_weights[strategy.name]
                score *= multiplier

            scored_pairs.append((strategy, node_id, score))

    # Sort by score descending
    return sorted(scored_pairs, key=lambda x: x[2], reverse=True)
