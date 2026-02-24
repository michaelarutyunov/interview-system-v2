"""Base class for node-level signal detectors.

Node-level signals are derived from NodeStateTracker and computed
per node. These signals enable joint strategy-node scoring.

"""

from typing import TYPE_CHECKING, Optional

from src.signals.signal_base import SignalDetector
from src.domain.models.node_state import NodeState

if TYPE_CHECKING:
    from src.services.node_state_tracker import NodeStateTracker


class NodeSignalDetector(SignalDetector):
    """Base class for signals derived from NodeStateTracker.

    Node-level signals analyze per-node state from the NodeStateTracker
    to produce signal values for each tracked node.

    Unlike global signals that return a single value, node signals
    return a dictionary mapping node_id to signal value.

    Example:
        class NodeExhaustedSignal(NodeSignalDetector):
            signal_name = "graph.node.exhausted"
            requires_node_tracker = True  # Mark as node-level signal

            async def detect(self, context, graph_state, response_text):
                results = {}
                for node_id, state in self.node_tracker.get_all_states().items():
                    results[node_id] = self._is_exhausted(state)
                return results

    Attributes:
        node_tracker: NodeStateTracker instance for accessing node states (always set)
        signal_name: Namespaced signal name (e.g., "graph.node.exhausted")
        requires_node_tracker: Marker for node-level signals (class attribute)
    """

    # Override parent's optional type with non-optional for node-level signals
    node_tracker: "NodeStateTracker"  # type: ignore[assignment]

    # All node-level signals require NodeStateTracker
    requires_node_tracker: bool = True  # type: ignore[misc]

    async def _get_node_state(self, node_id: str) -> Optional[NodeState]:
        """Get NodeState for a node.

        Args:
            node_id: ID of node to get state for

        Returns:
            NodeState if tracked, None otherwise
        """
        return await self.node_tracker.get_state(node_id)

    def _get_all_node_states(self) -> dict[str, NodeState]:
        """Get all tracked node states.

        Returns:
            Dictionary mapping node_id to NodeState
        """
        return self.node_tracker.get_all_states()

    def _calculate_shallow_ratio(
        self, state: NodeState, recent_count: int = 3
    ) -> float:
        """Calculate ratio of shallow responses in recent N responses.

        Args:
            state: NodeState to analyze
            recent_count: Number of recent responses to consider

        Returns:
            Ratio of shallow responses (0.0 - 1.0)
        """
        if not state.all_response_depths:
            return 0.0

        # Get last N responses
        recent_responses = state.all_response_depths[-recent_count:]

        # Count shallow responses (surface or shallow)
        shallow_count = sum(
            1 for depth in recent_responses if depth in ("surface", "shallow")
        )

        return shallow_count / len(recent_responses)
