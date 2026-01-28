from typing import Dict, Optional, TYPE_CHECKING
from src.methodologies.base import BaseStrategy

if TYPE_CHECKING:
    pass


class ProbeAlternativesStrategy(BaseStrategy):
    """Explore what else was tried or considered."""

    name = "probe_alternatives"
    description = "Understand competitive landscape and alternatives tried"

    @staticmethod
    def score_signals() -> Dict[str, float]:
        return {
            "job_identified": 0.3,
            "alternatives_explored": -0.5,  # Less needed if covered
            "mentioned_competitor": 0.3,  # Good if competitor mentioned
            "strategy_repetition_count": -0.25,
        }

    async def generate_focus(self, context, graph_state) -> Optional[str]:
        for node in graph_state.nodes:
            if node.node_type == "alternative":
                return node.label
        return None
