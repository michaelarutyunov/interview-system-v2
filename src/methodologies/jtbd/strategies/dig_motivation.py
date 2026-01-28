from typing import Dict, Optional, TYPE_CHECKING
from src.methodologies.base import BaseStrategy

if TYPE_CHECKING:
    pass


class DigMotivationStrategy(BaseStrategy):
    """
    Dig into the underlying motivation/why.

    This is where laddering comes in for JTBD.
    """

    name = "dig_motivation"
    description = "Understand why this job matters (laddering)"

    @staticmethod
    def score_signals() -> Dict[str, float]:
        return {
            "job_identified": 0.3,
            "motivation_depth": -0.4,
            "response_confidence": 0.2,  # Need clear answers to ladder
            "strategy_repetition_count": -0.15,  # Can repeat more (laddering)
        }

    async def generate_focus(self, context, graph_state) -> Optional[str]:
        # Find most recent motivation or job to ladder from
        # Use nodes_by_type to collect relevant nodes
        motivation_nodes = (
            graph_state.nodes_by_type.get("motivation", []) +
            graph_state.nodes_by_type.get("desired_outcome", []) +
            graph_state.nodes_by_type.get("job_statement", [])
        )
        if motivation_nodes:
            node = motivation_nodes[-1]  # Most recent
            return node.get("label") if isinstance(node, dict) else node.label
        return None
