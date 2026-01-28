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
        for node in reversed(graph_state.nodes):
            if node.node_type in ("motivation", "desired_outcome", "job_statement"):
                return node.label
        return None
