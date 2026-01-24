"""PeripheralReadiness scorer (Tier 2).

Boosts bridge strategy when peripheral cluster indicates readiness.

Per bead smg (P1): if strategy.id==bridge and density>0.7 and count>=3:
score=1.5, elif density>0.5 or count>=1: score=1.2, else: 1.0
"""

from typing import Any, Dict, List, Optional

import structlog

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.two_tier.base import Tier2Scorer, Tier2Output
from src.services.scoring.graph_utils import (
    get_simple_local_density,
    count_peripheral_nodes_simple,
)

logger = structlog.get_logger(__name__)


class PeripheralReadinessScorer(Tier2Scorer):
    """
    Boosts bridge strategy when peripheral cluster shows readiness.

    Checks if there are well-defined peripheral clusters (concepts related
    to but not central to the current topic) that could serve as natural
    bridging points. High cluster density with sufficient node count indicates
    a cohesive peripheral concept ready for bridging.

    Scoring logic (per bead smg):
    - bridge + density > 0.7 + count >= 3 → score = 1.5 (strong boost)
    - bridge + density > 0.5 OR count >= 1 → score = 1.2 (moderate boost)
    - otherwise → score = 1.0 (neutral)

    Weight: 0.10 (default)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        if "weight" not in self.config:
            self.weight = 0.10

        # Density thresholds for peripheral cluster readiness
        self.high_density_threshold = self.params.get("high_density_threshold", 0.7)
        self.moderate_density_threshold = self.params.get(
            "moderate_density_threshold", 0.5
        )
        self.min_peripheral_count = self.params.get("min_peripheral_count", 3)
        self.any_peripheral_count = self.params.get("any_peripheral_count", 1)

        logger.info(
            "PeripheralReadinessScorer initialized",
            weight=self.weight,
            high_density_threshold=self.high_density_threshold,
            moderate_density_threshold=self.moderate_density_threshold,
            min_peripheral_count=self.min_peripheral_count,
            any_peripheral_count=self.any_peripheral_count,
        )

    async def score(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
        recent_nodes: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]],
    ) -> Tier2Output:
        """Score based on peripheral cluster readiness for bridging.

        Args:
            strategy: Strategy being evaluated
            focus: Focus target with node_id
            graph_state: Current graph state
            recent_nodes: Recent nodes from graph
            conversation_history: Conversation history

        Returns:
            Tier2Output with score based on peripheral readiness
        """
        strategy_id = strategy.get("id", "")

        # Only apply to bridge strategy
        if strategy_id != "bridge":
            return self.make_output(
                raw_score=1.0,
                signals={"peripheral_checked": False},
                reasoning=f"Not bridge strategy ({strategy_id}), peripheral check not applicable",
            )

        # Get cluster density around the focus node (using simple helper)
        density = get_simple_local_density(
            focus_node_id=focus.get("node_id") if focus else None,
            graph_state=graph_state,
            recent_nodes=recent_nodes,
        )

        # Count peripheral nodes (using simple helper)
        peripheral_count = count_peripheral_nodes_simple(
            focus_node_id=focus.get("node_id") if focus else None,
            graph_state=graph_state,
            recent_nodes=recent_nodes,
        )

        # Determine score based on peripheral readiness
        if (
            density > self.high_density_threshold
            and peripheral_count >= self.min_peripheral_count
        ):
            raw_score = 1.5
            reasoning = (
                f"High cluster density ({density:.2f} > {self.high_density_threshold}) "
                f"and sufficient peripheral nodes ({peripheral_count} >= {self.min_peripheral_count}) "
                f"- excellent opportunity for lateral bridging"
            )
        elif (
            density > self.moderate_density_threshold
            or peripheral_count >= self.any_peripheral_count
        ):
            raw_score = 1.2
            reasoning = (
                f"Moderate cluster density ({density:.2f}) or peripheral nodes present ({peripheral_count}) "
                f"- good opportunity for bridging"
            )
        else:
            raw_score = 1.0
            reasoning = (
                f"Low cluster density ({density:.2f}) and no peripheral nodes ({peripheral_count}) "
                f"- bridging not particularly valuable"
            )

        signals = {
            "density": density,
            "peripheral_count": peripheral_count,
            "high_threshold": self.high_density_threshold,
            "moderate_threshold": self.moderate_density_threshold,
            "min_peripheral_count": self.min_peripheral_count,
            "strategy_id": strategy_id,
            "focus_node_id": focus.get("node_id"),
        }

        logger.debug(
            "PeripheralReadinessScorer scored",
            score=raw_score,
            density=density,
            peripheral_count=peripheral_count,
            reasoning=reasoning,
        )

        return self.make_output(
            raw_score=raw_score,
            signals=signals,
            reasoning=reasoning,
        )
