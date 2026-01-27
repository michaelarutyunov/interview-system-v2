"""Saturation scorer (Tier 2).

Detects topic exhaustion using Chao1 estimator and consecutive low-info turns.
Penalizes depth strategies when topic is saturated, boosts breadth strategies.
"""

from typing import Any, Dict, List, Optional

import structlog

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.two_tier.base import Tier2Scorer, Tier2Output

logger = structlog.get_logger(__name__)


class SaturationScorer(Tier2Scorer):
    """
    Detect topic exhaustion using Chao1 estimator and low-info turn tracking.

    Algorithm:
    1. Calculate Chao1 coverage ratio from graph state
    2. Check consecutive low-info turns from graph state properties
    3. Penalize depth strategies when saturated
    4. Boost breadth strategies when saturated

    Scoring logic:
    - Not saturated → 1.0 (neutral)
    - Saturated + depth strategy → 0.7 (penalty)
    - Saturated + breadth strategy → 1.5 (boost)

    Configuration parameters:
    - chao1_threshold: Saturation threshold (default: 0.90)
    - new_info_threshold: Min new info rate (default: 0.05)
    - run_length: Consecutive low-info turns to trigger (default: 2)
    - saturated_penalty: Penalty for depth on saturated topic (default: 0.7)
    - breadth_boost: Boost for breadth when saturated (default: 1.5)

    Weight: 0.15 (default)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        if "weight" not in self.config:
            self.weight = 0.15

        # Saturation thresholds
        self.chao1_threshold = self.params.get("chao1_threshold", 0.90)
        self.new_info_threshold = self.params.get("new_info_threshold", 0.05)
        self.run_length = self.params.get("run_length", 2)

        # Score values
        self.saturated_penalty = self.params.get("saturated_penalty", 0.7)
        self.breadth_boost = self.params.get("breadth_boost", 1.5)

        logger.info(
            "SaturationScorer initialized",
            weight=self.weight,
            chao1_threshold=self.chao1_threshold,
            new_info_threshold=self.new_info_threshold,
            run_length=self.run_length,
        )

    def _calculate_chao1_ratio(
        self, graph_state: GraphState, recent_nodes: List[Dict[str, Any]]
    ) -> float:
        """Calculate Chao1 coverage ratio estimator.

        Chao1 estimates species richness (unique elements) based on:
        - S_obs: Total number of unique species observed (unique node types)
        - f1: Number of species observed exactly once (singletons)
        - f2: Number of species observed exactly twice (doubletons)

        Chao1 = S_obs + (f1^2) / (2 * f2) if f2 > 0, else S_obs + f1 * (f1 - 1) / 2

        Coverage ratio = S_obs / Chao1 (approaches 1.0 as saturation increases)

        Args:
            graph_state: Current graph state
            recent_nodes: Recent nodes from graph for frequency analysis

        Returns:
            Chao1 coverage ratio between 0.0 and 1.0
        """
        # Count node type frequencies
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

        # Coverage ratio
        if chao1 > 0:
            coverage_ratio = s_obs / chao1
        else:
            coverage_ratio = 0.0

        return min(1.0, coverage_ratio)

    async def score(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],  # noqa: ARG001 - focus not used for saturation
        graph_state: GraphState,
        recent_nodes: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]],  # noqa: ARG001 - not used for saturation
    ) -> Tier2Output:
        """Score based on topic saturation.

        Args:
            strategy: Strategy being evaluated (must have type_category)
            focus: Focus target (not used for saturation scorer)
            graph_state: Current graph state
            recent_nodes: Recent nodes from graph for Chao1 calculation
            conversation_history: Conversation history (not used for saturation)

        Returns:
            Tier2Output with score based on saturation detection
        """
        # Calculate Chao1 coverage ratio
        chao1_ratio = self._calculate_chao1_ratio(graph_state, recent_nodes)

        # Get saturation metrics from graph_state.saturation_metrics (ADR-010 Phase 2)
        # Fall back to defaults if not yet populated
        if graph_state.saturation_metrics:
            new_info_rate = graph_state.saturation_metrics.new_info_rate
            consecutive_low_info = graph_state.saturation_metrics.consecutive_low_info
        else:
            new_info_rate = 1.0
            consecutive_low_info = 0

        signals = {
            "chao1_ratio": chao1_ratio,
            "new_info_rate": new_info_rate,
            "consecutive_low_info": consecutive_low_info,
        }

        # Check saturation conditions
        is_chao1_saturated = chao1_ratio > self.chao1_threshold
        is_low_info_run = consecutive_low_info >= self.run_length
        # Saturated if Chao1 threshold exceeded OR consecutive low info turns
        is_saturated = is_chao1_saturated or is_low_info_run

        signals["is_saturated"] = is_saturated
        signals["is_chao1_saturated"] = is_chao1_saturated
        signals["is_low_info_run"] = is_low_info_run

        # ADR-010 Phase 2: Populate graph_state.saturation_metrics
        # Import here to avoid circular dependency
        from src.domain.models.knowledge_graph import SaturationMetrics

        graph_state.saturation_metrics = SaturationMetrics(
            chao1_ratio=chao1_ratio,
            new_info_rate=new_info_rate,
            consecutive_low_info=consecutive_low_info,
            is_saturated=is_saturated,
        )

        # Get strategy type
        strategy_type = strategy.get("type_category", "").lower()

        # Apply scoring based on saturation and strategy type
        if not is_saturated:
            raw_score = 1.0
            reasoning = "Topic not saturated - no adjustment"
        elif strategy_type == "depth":
            # Penalize depth strategies when saturated
            raw_score = self.saturated_penalty
            reasoning = (
                f"Topic saturated (Chao1={chao1_ratio:.2f}, "
                f"new_info_rate={new_info_rate:.2f}, low_info_turns={consecutive_low_info}) "
                f"- depth strategy penalized"
            )
        elif strategy_type == "breadth":
            # Boost breadth strategies when saturated
            raw_score = self.breadth_boost
            reasoning = (
                f"Topic saturated (Chao1={chao1_ratio:.2f}) "
                f"- breadth strategy encouraged to switch topics"
            )
        else:
            # Neutral for other strategy types (coverage, closing, etc.)
            raw_score = 1.0
            reasoning = (
                f"Topic saturated but {strategy_type} strategy - neutral adjustment"
            )

        # Clamp to range [0.5, 1.8]
        raw_score = max(0.5, min(1.8, raw_score))

        logger.debug(
            "SaturationScorer scored",
            score=raw_score,
            chao1_ratio=chao1_ratio,
            is_saturated=is_saturated,
            strategy_type=strategy_type,
            reasoning=reasoning,
        )

        return self.make_output(
            raw_score=raw_score, signals=signals, reasoning=reasoning
        )
