from typing import List, Tuple
from src.methodologies.base import BaseStrategy, SignalState


def score_strategy(
    strategy_class: type[BaseStrategy],
    signals: SignalState,
) -> float:
    """
    Score a strategy based on current signals.

    Returns score in range [0, 1].
    """
    weights = strategy_class.score_signals()
    score = 0.0

    for signal_name, weight in weights.items():
        signal_value = getattr(signals, signal_name, 0.0)

        if isinstance(signal_value, bool):
            contribution = weight if signal_value else 0.0
        elif isinstance(signal_value, (int, float)):
            # Normalize contribution
            contribution = weight * min(max(signal_value, 0.0), 1.0)
        else:
            contribution = 0.0

        score += contribution

    # Clamp to [0, 1]
    return max(0.0, min(1.0, score))


def rank_strategies(
    strategies: List[type[BaseStrategy]],
    signals: SignalState,
) -> List[Tuple[type[BaseStrategy], float]]:
    """
    Rank all strategies by score.

    Returns list of (strategy_class, score) sorted descending.
    """
    scored = [(s, score_strategy(s, signals)) for s in strategies]
    return sorted(scored, key=lambda x: x[1], reverse=True)
