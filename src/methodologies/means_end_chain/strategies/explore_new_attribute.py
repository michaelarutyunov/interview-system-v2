from typing import Dict, Optional, TYPE_CHECKING
from src.methodologies.base import BaseStrategy

if TYPE_CHECKING:
    from src.domain.models.knowledge_graph import GraphState
    from src.services.turn_pipeline.context import PipelineContext


class ExploreNewAttributeStrategy(BaseStrategy):
    """
    Start a new ladder from an unexplored attribute.

    Used to broaden coverage when current ladder is exhausted.
    """

    name = "explore_new_attribute"
    description = "Start exploring a new product attribute"

    @staticmethod
    def score_signals() -> Dict[str, float]:
        return {
            "coverage_breadth": -0.4,  # Less needed if coverage high
            "missing_terminal_value": -0.2,  # Prefer finishing current ladder first
            "ladder_depth": 0.3,  # Good if current ladder is deep (complete)
            "attributes_explored": -0.2,  # Less needed if many attributes done
            "strategy_repetition_count": -0.15,
        }

    async def generate_focus(
        self,
        context: "PipelineContext",
        graph_state: "GraphState",
    ) -> Optional[str]:
        """Find an unexplored concept element to start new ladder."""
        # Use coverage_state from graph_state to find unexplored elements
        if graph_state.coverage_state:
            for element_id, coverage in graph_state.coverage_state.elements.items():
                if not coverage.covered:
                    # Return element name if available
                    if context.recent_nodes:
                        # For now, return a generic message
                        # In a full implementation, we'd look up the element name
                        return "new attribute"
        return None
