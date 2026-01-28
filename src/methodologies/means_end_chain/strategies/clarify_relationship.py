from typing import Dict, Optional, TYPE_CHECKING
from src.methodologies.base import BaseStrategy

if TYPE_CHECKING:
    from src.domain.models.knowledge_graph import GraphState
    from src.services.turn_pipeline.context import PipelineContext


class ClarifyRelationshipStrategy(BaseStrategy):
    """
    Clarify how concepts are connected.

    Used when we have disconnected nodes or unclear relationships.
    """

    name = "clarify_relationship"
    description = "Clarify how concepts relate to each other"

    @staticmethod
    def score_signals() -> Dict[str, float]:
        return {
            "disconnected_nodes": 0.5,  # High if orphan nodes exist
            "edge_density": -0.3,  # Less needed if well-connected
            "response_ambiguity": 0.3,  # Good if last response was unclear
            "strategy_repetition_count": -0.2,  # Avoid repetition
        }

    async def generate_focus(
        self,
        context: "PipelineContext",
        graph_state: "GraphState",
    ) -> Optional[str]:
        """Find a disconnected node to clarify."""
        # Use recent_nodes from context
        # For now, return the first recent node as a simplified approach
        # A full implementation would check which nodes are disconnected
        if context.recent_nodes:
            return context.recent_nodes[0].label
        return None
