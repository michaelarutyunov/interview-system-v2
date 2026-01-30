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
    - 0: Just started, minimal depth
    - 1: Near completion, good depth and chain completion

    Composites:
    - Chain completion (graph.chain_completion)
    - Graph depth (graph.max_depth)
    - Node count (graph.node_count)
    """

    signal_name = "meta.interview_progress"
    description = "Overall interview progress from 0-1. 0 = just started, 1 = near completion. Combines chain completion, graph depth, and node count. Higher values suggest we can start closing."
    cost_tier = SignalCostTier.LOW
    refresh_trigger = RefreshTrigger.PER_TURN

    async def detect(self, context, graph_state, response_text):
        """Calculate interview progress from multiple signals."""
        # Need signals dict to compose from
        if not hasattr(context, "signals") or not context.signals:
            return {self.signal_name: 0.0}

        signals = context.signals

        # Component 1: Chain completion (0-1) - replaces coverage breadth
        # chain_completion is a dict with "has_complete_chain" and "complete_chain_count"
        chain_completion_data = signals.get("graph.chain_completion", {})
        if isinstance(chain_completion_data, dict):
            # Calculate completion ratio (complete chains / total level 1 nodes)
            level_1_count = chain_completion_data.get("level_1_node_count", 1)
            complete_count = chain_completion_data.get("complete_chain_count", 0)
            chain_completion = (
                (complete_count / max(level_1_count, 1)) if level_1_count > 0 else 0.0
            )
        else:
            chain_completion = (
                float(chain_completion_data) if chain_completion_data else 0.0
            )

        # Component 2: Depth (normalized to 0-1, assuming depth 3+ is good)
        max_depth = signals.get("graph.max_depth", 0)
        depth_score = min(max(max_depth / 3.0, 0.0), 1.0)

        # Component 3: Node count (normalized to 0-1, assuming 10+ nodes is good)
        node_count = signals.get("graph.node_count", 0)
        node_score = min(max(node_count / 10.0, 0.0), 1.0)

        # Combine components (weighted average)
        progress = (chain_completion * 0.4) + (depth_score * 0.4) + (node_score * 0.2)

        return {self.signal_name: progress}
