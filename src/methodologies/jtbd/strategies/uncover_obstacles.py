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
        # Use nodes_by_type to find alternative nodes
        alt_nodes = (
            graph_state.nodes_by_type.get("alternative", []) +
            graph_state.nodes_by_type.get("workaround", [])
        )
        if alt_nodes:
            node = alt_nodes[-1]
            return node.get("label") if isinstance(node, dict) else node.label
        return None
