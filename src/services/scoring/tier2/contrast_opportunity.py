"""ContrastOpportunity scorer (Tier 2).

Detects opportunities to introduce counter-examples by checking for opposite
stance nodes in the graph.

Per bead 8xa (P1): if strategy.id==contrast and has_opposite and density>0.6:
score=1.5, elif has_opposite: score=1.2, else: 1.0
"""

from typing import Any, Dict, List, Optional

import structlog

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.two_tier.base import Tier2Scorer, Tier2Output
from src.services.scoring.graph_utils import (
    get_simple_local_density,
    has_opposite_stance_simple,
)

logger = structlog.get_logger(__name__)


class ContrastOpportunityScorer(Tier2Scorer):
    """
    Boosts contrast strategy when opposite stance nodes exist.

    Detects whether there are nodes with opposite stances (e.g., positive vs
    negative attitudes toward the same concept) that could serve as natural
    counter-examples. Higher cluster density indicates more cohesive concepts
    that are better for contrastive questioning.

    Scoring logic (per bead 8xa):
    - contrast + has_opposite + density > 0.6 → score = 1.5 (strong boost)
    - contrast + has_opposite → score = 1.2 (moderate boost)
    - otherwise → score = 1.0 (neutral)

    Weight: 0.10 (default)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        if "weight" not in self.config:
            self.weight = 0.10

        # Density threshold for "cohesive cluster" determination
        self.high_density_threshold = self.params.get("high_density_threshold", 0.6)

        logger.info(
            "ContrastOpportunityScorer initialized",
            weight=self.weight,
            high_density_threshold=self.high_density_threshold,
        )

    async def score(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
        recent_nodes: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]],
    ) -> Tier2Output:
        """Score based on contrast opportunity detection.

        Args:
            strategy: Strategy being evaluated
            focus: Focus target with node_id
            graph_state: Current graph state
            recent_nodes: Recent nodes from graph
            conversation_history: Conversation history

        Returns:
            Tier2Output with score based on contrast opportunity
        """
        strategy_id = strategy.get("id", "")

        # Only apply to contrast strategy
        if strategy_id != "contrast":
            return self.make_output(
                raw_score=1.0,
                signals={"opportunity_checked": False},
                reasoning=f"Not contrast strategy ({strategy_id}), opportunity check not applicable",
            )

        # Check for opposite stance node (using simple helper)
        has_opposite = has_opposite_stance_simple(
            focus_node_id=(focus.get("node_id") or "") if focus else "",
            recent_nodes=recent_nodes,
        )

        # Get cluster density around the focus node (using simple helper)
        density = get_simple_local_density(
            focus_node_id=(focus.get("node_id") or "") if focus else "",
            graph_state=graph_state,
            recent_nodes=recent_nodes,
        )

        # Determine score based on opportunity detection
        if has_opposite and density > self.high_density_threshold:
            raw_score = 1.5
            reasoning = (
                f"Has opposite stance node and high cluster density ({density:.2f} > {self.high_density_threshold}) "
                f"- excellent opportunity for counter-example"
            )
        elif has_opposite:
            raw_score = 1.2
            reasoning = (
                f"Has opposite stance node but lower cluster density ({density:.2f}) "
                f"- good opportunity for counter-example"
            )
        else:
            raw_score = 1.0
            reasoning = "No opposite stance node found - contrast strategy not particularly valuable"

        signals = {
            "has_opposite": has_opposite,
            "density": density,
            "high_threshold": self.high_density_threshold,
            "strategy_id": strategy_id,
            "focus_node_id": focus.get("node_id"),
        }

        logger.debug(
            "ContrastOpportunityScorer scored",
            score=raw_score,
            has_opposite=has_opposite,
            density=density,
            reasoning=reasoning,
        )

        return self.make_output(
            raw_score=raw_score,
            signals=signals,
            reasoning=reasoning,
        )
