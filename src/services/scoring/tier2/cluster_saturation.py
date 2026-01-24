"""ClusterSaturation scorer (Tier 2).

Boosts synthesis strategy when topic saturation indicates good coverage.

Per bead ekm (P1): if strategy.id==synthesis and saturation>0.7: score=1.5,
elif saturation>0.4: score=1.2, else: 1.0
"""

from typing import Any, Dict, List, Optional

import structlog

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.two_tier.base import Tier2Scorer, Tier2Output

logger = structlog.get_logger(__name__)


class ClusterSaturationScorer(Tier2Scorer):
    """
    Boosts synthesis strategy based on topic saturation level.

    Uses Chao1 coverage ratio to estimate how thoroughly the topic
    has been explored. When saturation is high, synthesis becomes more
    valuable to consolidate learning.

    Scoring logic (per bead ekm):
    - synthesis + saturation > 0.7 → score = 1.5 (strong boost)
    - synthesis + saturation > 0.4 → score = 1.2 (moderate boost)
    - otherwise → score = 1.0 (neutral)

    Weight: 0.10 (default)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        if "weight" not in self.config:
            self.weight = 0.10

        # Saturation thresholds
        self.high_saturation_threshold = self.params.get(
            "high_saturation_threshold", 0.7
        )
        self.moderate_saturation_threshold = self.params.get(
            "moderate_saturation_threshold", 0.4
        )

        logger.info(
            "ClusterSaturationScorer initialized",
            weight=self.weight,
            high_threshold=self.high_saturation_threshold,
            moderate_threshold=self.moderate_saturation_threshold,
        )

    async def score(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
        recent_nodes: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]],
    ) -> Tier2Output:
        """Score based on saturation level for synthesis strategy.

        Args:
            strategy: Strategy being evaluated
            focus: Focus target (not used for saturation)
            graph_state: Current graph state
            recent_nodes: Recent nodes for frequency analysis
            conversation_history: Conversation history (not used)

        Returns:
            Tier2Output with score based on saturation
        """
        strategy_id = strategy.get("id", "")

        # Only apply to synthesis strategy
        if strategy_id != "synthesis":
            return self.make_output(
                raw_score=1.0,
                signals={"saturation_checked": False},
                reasoning=f"Not synthesis strategy ({strategy_id}), saturation not applicable",
            )

        # Calculate saturation using Chao1 estimator
        saturation = self._calculate_saturation(graph_state, recent_nodes)

        # Determine score based on saturation level
        if saturation > self.high_saturation_threshold:
            raw_score = 1.5
            reasoning = (
                f"High saturation ({saturation:.2f} > {self.high_saturation_threshold}) "
                f"- synthesis strongly encouraged to consolidate learning"
            )
        elif saturation > self.moderate_saturation_threshold:
            raw_score = 1.2
            reasoning = (
                f"Moderate saturation ({saturation:.2f} > {self.moderate_saturation_threshold}) "
                f"- synthesis moderately encouraged"
            )
        else:
            raw_score = 1.0
            reasoning = (
                f"Low saturation ({saturation:.2f}) - synthesis not specifically encouraged, "
                f"consider deepening exploration first"
            )

        signals = {
            "saturation": saturation,
            "high_threshold": self.high_saturation_threshold,
            "moderate_threshold": self.moderate_saturation_threshold,
            "strategy_id": strategy_id,
        }

        logger.debug(
            "ClusterSaturationScorer scored",
            score=raw_score,
            saturation=saturation,
            strategy_id=strategy_id,
            reasoning=reasoning,
        )

        return self.make_output(
            raw_score=raw_score,
            signals=signals,
            reasoning=reasoning,
        )

    def _calculate_saturation(
        self,
        graph_state: GraphState,
        recent_nodes: List[Dict[str, Any]],
    ) -> float:
        """
        Calculate Chao1 coverage ratio estimator for saturation.

        This is the same calculation used in SaturationScorer, extracted
        here for standalone use.

        Args:
            graph_state: Current graph state
            recent_nodes: Recent nodes for frequency analysis

        Returns:
            Chao1 coverage ratio between 0.0 and 1.0
        """
        # Count node type frequencies from graph_state
        node_type_counts: Dict[str, int] = {}
        for node_type, count in graph_state.nodes_by_type.items():
            node_type_counts[node_type] = count

        # Also consider recent nodes for more granular analysis
        if recent_nodes:
            for node in recent_nodes:
                node_type = node.get("node_type", "")
                if node_type:
                    node_type_counts[node_type] = node_type_counts.get(node_type, 0) + 1

        if not node_type_counts:
            return 0.0

        # Calculate frequencies
        frequencies = list(node_type_counts.values())
        s_obs = len(frequencies)  # Total unique node types observed
        f1 = frequencies.count(1)  # Singletons
        f2 = frequencies.count(2)  # Doubletons

        # Calculate Chao1 estimator
        if f2 > 0:
            chao1 = s_obs + (f1 * f1) / (2 * f2)
        else:
            # Bias-corrected form for when f2 = 0
            chao1 = s_obs + f1 * (f1 - 1) / 2

        # Coverage ratio (saturation)
        if chao1 > 0:
            coverage_ratio = s_obs / chao1
        else:
            coverage_ratio = 0.0

        return min(1.0, coverage_ratio)
