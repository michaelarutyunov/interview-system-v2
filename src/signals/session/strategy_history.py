"""Strategy history signals - repetition count, turns since change."""

import structlog

from src.signals.signal_base import SignalDetector

log = structlog.get_logger(__name__)


class StrategyRepetitionCountSignal(SignalDetector):
    """Count how many times current strategy was used recently.

    Namespaced signal: interview.strategy.self_count

    Returns count of how many times the current strategy appears
    in the last 5 entries of strategy history.

    Used for: Avoiding strategy overuse, forcing variety.
    """

    signal_name = "interview.strategy.self_count"
    description = (
        "Per-strategy recent usage frequency. Returns a dict keyed by strategy "
        "name with normalized counts in [0,1] over the last 5 turns. Scorer "
        "resolves to each candidate's own count; weight is thus a true "
        "self-repetition brake."
    )

    async def detect(self, context, graph_state, response_text):
        """Return a per-strategy repetition map.

        Historical note: this signal previously returned a single scalar equal
        to the frequency of the *last-selected* strategy, which caused the
        scorer to penalize every candidate in proportion to its weight —
        punishing candidates that hadn't fired. The fix returns a dict; the
        scorer picks the current candidate's own value before applying weight.
        """
        strategy_history = []
        if hasattr(context, "strategy_history") and context.strategy_history:
            strategy_history = context.strategy_history

        if not strategy_history:
            return {self.signal_name: {}}

        window_size = 5
        recent = strategy_history[-window_size:]

        counts: dict[str, float] = {}
        for s in recent:
            if not s:
                continue
            counts[s] = counts.get(s, 0.0) + 1.0

        normalized = {name: c / window_size for name, c in counts.items()}

        log.debug(
            "strategy_repetition_per_strategy",
            normalized=normalized,
            recent_5_strategies=recent,
        )

        return {self.signal_name: normalized}


class TurnsSinceChangeSignal(SignalDetector):
    """Count how many turns since strategy last changed.

    Namespaced signal: interview.strategy.turns_since_change

    Returns number of consecutive turns using the current strategy.

    Used for: Detecting when to switch strategies for variety.
    """

    signal_name = "interview.strategy.turns_since_change"
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
