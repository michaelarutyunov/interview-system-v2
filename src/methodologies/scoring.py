"""Strategy scoring using signal weights from YAML configs.

Scores strategies based on detected signals and strategy weights
defined in methodology YAML configs.
"""

from typing import List, Tuple, Dict, Any
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
) -> List[Tuple[StrategyConfig, float]]:
    """
    Rank all strategies by score.

    Args:
        strategy_configs: List of strategy configs from YAML
        signals: Dict of detected signals

    Returns:
        List of (strategy_config, score) sorted descending by score
    """
    scored = [
        (strategy_config, score_strategy(strategy_config, signals))
        for strategy_config in strategy_configs
    ]
    return sorted(scored, key=lambda x: x[1], reverse=True)
