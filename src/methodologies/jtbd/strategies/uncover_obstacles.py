from typing import Dict, Optional, TYPE_CHECKING
from src.methodologies.base import BaseStrategy

if TYPE_CHECKING:
    pass


class UncoverObstaclesStrategy(BaseStrategy):
    """Explore barriers and pain points."""

    name = "uncover_obstacles"
    description = "Understand what held them back or caused friction"

    @staticmethod
    def score_signals() -> Dict[str, float]:
        return {
            "obstacles_explored": -0.5,
            "mentioned_struggle": 0.3,
            "alternatives_explored": 0.2,  # Often comes after alternatives
            "strategy_repetition_count": -0.2,
        }

    async def generate_focus(self, context, graph_state) -> Optional[str]:
        for node in graph_state.nodes:
            if node.node_type in ("alternative", "workaround"):
                return node.label
        return None
