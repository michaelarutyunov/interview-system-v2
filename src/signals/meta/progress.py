"""Meta progress signals for interview completion estimation.

Provides interview progress metrics that indicate when the conversation
has sufficient coverage to begin closing. Progress is computed from
multiple graph state signals to balance breadth, depth, and structure.
"""

from src.signals.signal_base import SignalDetector


class InterviewProgressSignal(SignalDetector):
    """Estimate overall interview progress from chain completion, depth, and node count.

    Computes a weighted progress score (0.0-1.0) combining three graph
    health metrics to determine interview maturity. Higher values suggest
    sufficient coverage for closing strategies.

    Scoring components (weighted average):
    - Chain completion (40%): Ratio of level-1 nodes with complete chains
    - Graph depth (40%): Normalized max_depth (depth >= 3 = 1.0)
    - Node count (20%): Normalized node_count (>= 10 nodes = 1.0)

    This composite signal enables continuation decisions by providing a
    single metric for interview completeness.

    Namespaced signal: meta.interview_progress
    Cost: low (composes from existing signals in context.signals)
    Refresh: per_turn (recomputed each turn after signal detection)
    """

    signal_name = "meta.interview_progress"
    description = "Overall interview progress from 0-1. 0 = just started, 1 = near completion. Combines chain completion, graph depth, and node count. Higher values suggest we can start closing."
    dependencies = [
        "graph.chain_completion",
        "graph.max_depth",
        "graph.node_count",
    ]

    async def detect(self, context, graph_state, response_text):  # noqa: ARG001
        """Calculate interview progress from chain completion, depth, and node count.

        Composes progress score from three graph health metrics using
        weighted averaging. Requires context.signals to contain dependency
        signals (chain_completion, max_depth, node_count).

        Args:
            context: Pipeline context with signals dict containing dependency values
            graph_state: Current knowledge graph state (unused, composed from signals)
            response_text: User's response text (unused, composed from signals)

        Returns:
            Dict with meta.interview_progress: float (0.0-1.0)
        """
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
