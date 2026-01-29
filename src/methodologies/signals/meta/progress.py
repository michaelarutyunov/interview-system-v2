"""Meta progress signals - interview progress, completion likelihood."""

from src.methodologies.signals.common import (
    SignalDetector,
    SignalCostTier,
    RefreshTrigger,
)


class InterviewProgressSignal(SignalDetector):
    """Estimates interview progress based on multiple signals.

    Namespaced signal: meta.interview_progress
    Cost: low (O(1) - composes other signals)
    Refresh: per_turn (cached during turn)

    Returns float 0-1:
    - 0: Just started, minimal coverage
    - 1: Near completion, good coverage depth

    Composites:
    - Coverage breadth (graph.coverage_breadth)
    - Graph depth (graph.max_depth)
    - Turn count relative to max turns
    """

    signal_name = "meta.interview_progress"
    description = "Overall interview progress from 0-1. 0 = just started, 1 = near completion. Combines coverage breadth, graph depth, and turn count. Higher values suggest we can start closing."
    cost_tier = SignalCostTier.LOW
    refresh_trigger = RefreshTrigger.PER_TURN

    async def detect(self, context, graph_state, response_text):
        """Calculate interview progress from multiple signals."""
        # Need signals dict to compose from
        if not hasattr(context, "signals") or not context.signals:
            return {self.signal_name: 0.0}

        signals = context.signals

        # Component 1: Coverage breadth (0-1)
        coverage_breadth = signals.get("graph.coverage_breadth", 0.0)

        # Component 2: Depth (normalized to 0-1, assuming depth 3+ is good)
        max_depth = signals.get("graph.max_depth", 0)
        depth_score = min(max_depth / 3.0, 1.0)

        # Component 3: Missing terminal value (penalty if missing)
        missing_terminal = signals.get("graph.missing_terminal_value", True)
        terminal_penalty = 0.3 if missing_terminal else 0.0

        # Combine components (weighted average)
        progress = (
            (coverage_breadth * 0.4)
            + (depth_score * 0.4)
            + ((1.0 - terminal_penalty) * 0.2)
        )

        return {self.signal_name: progress}
