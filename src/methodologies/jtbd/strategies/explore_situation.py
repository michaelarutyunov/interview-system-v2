from typing import Dict, Optional, TYPE_CHECKING
from src.methodologies.base import BaseStrategy

if TYPE_CHECKING:
    pass


class ExploreSituationStrategy(BaseStrategy):
    """Explore the context/circumstances when the job arises."""

    name = "explore_situation"
    description = "Understand when and where the job occurs"

    @staticmethod
    def score_signals() -> Dict[str, float]:
        return {
            "job_identified": 0.3,  # Need job first
            "situation_depth": -0.4,  # Less needed if covered
            "mentioned_trigger": 0.2,  # Good if trigger mentioned
            "strategy_repetition_count": -0.2,
        }

    async def generate_focus(self, context, graph_state) -> Optional[str]:
        # Focus on the job statement
        # Use nodes_by_type to find job nodes
        job_nodes = (
            graph_state.nodes_by_type.get("job_statement", []) +
            graph_state.nodes_by_type.get("core_job", [])
        )
        if job_nodes:
            # Return the label of the most recent job node
            return job_nodes[-1].get("label") if isinstance(job_nodes[-1], dict) else job_nodes[-1].label
        return None
