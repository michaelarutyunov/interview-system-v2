"""Node strategy repetition signals.

These signals track how often the same strategy is used repeatedly
on a specific node, helping to avoid repetitive questioning patterns.
"""

from src.signals.graph.node_base import NodeSignalDetector


class NodeStrategyRepetitionSignal(NodeSignalDetector):
    """How many times the same strategy has been used consecutively on a node.

    Tracks consecutive usage of the same strategy on a node to detect
    repetitive patterns that might indicate the need to switch strategies.

    Categories:
    - none: 0 consecutive times (not currently repeating)
    - low: 1-2 consecutive times
    - medium: 3-4 consecutive times
    - high: 5+ consecutive times

    Namespaced signal: technique.node.strategy_repetition
    """

    signal_name = "technique.node.strategy_repetition"

    async def detect(self, context, graph_state, response_text):
        """Detect strategy repetition for all nodes.

        Returns:
            Dict mapping node_id -> "none" | "low" | "medium" | "high"
        """
        results = {}

        for node_id, state in self._get_all_node_states().items():
            repetition_category = self._categorize_repetition(state.consecutive_same_strategy)
            results[node_id] = repetition_category

        return results

    def _categorize_repetition(self, consecutive: int) -> str:
        """Categorize consecutive strategy usage.

        Args:
            consecutive: Number of consecutive times same strategy was used

        Returns:
            Category: "none", "low", "medium", or "high"
        """
        if consecutive == 0:
            return "none"
        elif consecutive <= 2:
            return "low"
        elif consecutive <= 4:
            return "medium"
        else:
            return "high"
