"""
Temporal signals (conversation history-derived).

These signals are derived from conversation history and strategy patterns.
They are refreshed per turn (cached during the turn).

Example signals:
- StrategyRepetitionCountSignal: How many times current strategy was used recently
- TurnsSinceChangeSignal: How many turns since strategy last changed
"""

from src.methodologies.signals.temporal.strategy_history import (
    StrategyRepetitionCountSignal,
    TurnsSinceChangeSignal,
)

__all__ = [
    "StrategyRepetitionCountSignal",
    "TurnsSinceChangeSignal",
]
