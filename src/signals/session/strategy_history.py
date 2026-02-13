"""Strategy history signals - repetition count, turns since change."""

from src.signals.signal_base import SignalDetector


class StrategyRepetitionCountSignal(SignalDetector):
    """Count how many times current strategy was used recently.

    Namespaced signal: temporal.strategy_repetition_count

    Returns count of how many times the current strategy appears
    in the last 5 entries of strategy history.

    Used for: Avoiding strategy overuse, forcing variety.
    """

    signal_name = "temporal.strategy_repetition_count"
    description = "How many times the current strategy was used in the last 5 turns. High counts (3+) suggest strategy overuse and need to switch strategies for variety."

    async def detect(self, context, graph_state, response_text):
        """Count strategy repetitions in recent history."""
        strategy_history = []

        # Try to get strategy_history from context
        if hasattr(context, "strategy_history") and context.strategy_history:
            strategy_history = context.strategy_history

        if not strategy_history:
            return {self.signal_name: 0}

        # Get current strategy (most recent)
        current = strategy_history[-1] if strategy_history else None
        if not current:
            return {self.signal_name: 0}

        # Count occurrences in last 5 entries (window size = 5)
        window_size = 5
        recent_history = strategy_history[-window_size:]
        repetition_count = sum(1 for s in recent_history if s == current)

        # Normalize to [0, 1] by dividing by window size
        return {self.signal_name: repetition_count / window_size}


class TurnsSinceChangeSignal(SignalDetector):
    """Count how many turns since strategy last changed.

    Namespaced signal: temporal.turns_since_strategy_change

    Returns number of consecutive turns using the current strategy.

    Used for: Detecting when to switch strategies for variety.
    """

    signal_name = "temporal.turns_since_strategy_change"
    description = "How many consecutive turns have used the current strategy. High values (3+) suggest it's time to switch strategies to maintain variety."

    async def detect(self, context, graph_state, response_text):
        """Count turns since strategy last changed."""
        strategy_history = []

        # Try to get strategy_history from context
        if hasattr(context, "strategy_history") and context.strategy_history:
            strategy_history = context.strategy_history

        if not strategy_history or len(strategy_history) < 2:
            return {self.signal_name: 0}

        # Count consecutive occurrences of current strategy from the end
        current = strategy_history[-1]
        turns_since_change = 0

        for strategy in reversed(strategy_history):
            if strategy == current:
                turns_since_change += 1
            else:
                break

        # Normalize to [0, 1] by dividing by practical max (5)
        practical_max = 5
        return {self.signal_name: min(turns_since_change / practical_max, 1.0)}
