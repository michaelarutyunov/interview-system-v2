from typing import Dict, Optional, TYPE_CHECKING
from src.methodologies.base import BaseStrategy

if TYPE_CHECKING:
    from src.domain.models.knowledge_graph import GraphState
    from src.services.turn_pipeline.context import PipelineContext


class ReflectAndValidateStrategy(BaseStrategy):
    """
    Summarize and validate understanding with respondent.

    Used to confirm extracted chain is correct.
    """

    name = "reflect_and_validate"
    description = "Summarize the chain and confirm understanding"

    @staticmethod
    def score_signals() -> Dict[str, float]:
        return {
            "ladder_depth": 0.3,  # Good after deep ladder
            "response_depth": 0.2,  # Good after rich responses
            "turns_since_strategy_change": 0.2,  # Good if been on same track
            "strategy_repetition_count": -0.3,  # Don't over-reflect
            "missing_terminal_value": -0.2,  # Prefer after reaching values
        }

    async def generate_focus(
        self,
        context: "PipelineContext",
        graph_state: "GraphState",
    ) -> Optional[str]:
        """Identify the chain to reflect on."""
        # Use recent_nodes from context to find value nodes
        for node in reversed(context.recent_nodes):
            if node.node_type in ("instrumental_value", "terminal_value"):
                return node.label
        return None
