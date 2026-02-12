"""
Temporal signals (conversation history-derived).

These signals are derived from conversation history and strategy patterns.
They are refreshed per turn (cached during the turn).

Example signals:
- StrategyRepetitionCountSignal: How many times current strategy was used recently
- TurnsSinceChangeSignal: How many turns since strategy last changed
- NodeStrategyRepetitionSignal: How many times same strategy used on a node consecutively
- GlobalResponseTrendSignal: Trend in response quality over the session
"""

from src.signals.session.strategy_history import (
    StrategyRepetitionCountSignal,
    TurnsSinceChangeSignal,
)
from src.signals.session.node_strategy_repetition import (
    NodeStrategyRepetitionSignal,
)
from src.signals.session.llm_response_trend import (
    GlobalResponseTrendSignal,
)

__all__ = [
    "StrategyRepetitionCountSignal",
    "TurnsSinceChangeSignal",
    "NodeStrategyRepetitionSignal",
    "GlobalResponseTrendSignal",
]
