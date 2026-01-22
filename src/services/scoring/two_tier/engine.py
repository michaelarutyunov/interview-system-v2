"""Two-tier hybrid scoring engine.

Implements the two-tier approach:
- Tier 1: Hard constraints (boolean vetoes) with early exit
- Tier 2: Weighted additive scoring for ranking valid candidates
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import structlog
from pydantic import BaseModel

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.two_tier.base import Tier1Scorer, Tier1Output, Tier2Scorer, Tier2Output

logger = structlog.get_logger(__name__)


@dataclass
class ScoringResult:
    """Complete result from scoring a (strategy, focus) candidate."""

    strategy: Dict[str, Any]
    focus: Dict[str, Any]
    final_score: float
    tier1_outputs: List[Tier1Output] = field(default_factory=list)
    tier2_outputs: List[Tier2Output] = field(default_factory=list)
    vetoed_by: Optional[str] = None
    reasoning_trace: List[str] = field(default_factory=list)


class TwoTierScoringEngine:
    """
    Orchestrates two-tier hybrid scoring for strategy selection.

    Scoring pipeline:
    1. Run all Tier 1 scorers sequentially
    2. If any veto → return vetoed result (early exit)
    3. If all pass → run all Tier 2 scorers
    4. Compute final score: base + Σ(weight × score)
    5. Return complete result with reasoning trace

    Features:
    - Early exit on first veto (performance)
    - Complete reasoning trace for debugging
    - Validation that weights sum to 1.0
    - Error handling for failed scorers
    """

    def __init__(
        self,
        tier1_scorers: List[Tier1Scorer],
        tier2_scorers: List[Tier2Scorer],
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize two-tier scoring engine.

        Args:
            tier1_scorers: List of hard constraint scorers
            tier2_scorers: List of weighted additive scorers
            config: Engine configuration
        """
        self.tier1_scorers = [s for s in tier1_scorers if s.enabled]
        self.tier2_scorers = [s for s in tier2_scorers if s.enabled]
        self.config = config or {}

        # Validate Tier 2 weights sum to 1.0
        self._validate_weights()

        # Configuration
        self._veto_on_first = self.config.get("veto_on_first", True)
        self._score_precision = self.config.get("score_precision", 4)

        logger.info(
            "TwoTierScoringEngine initialized",
            num_tier1=len(self.tier1_scorers),
            num_tier2=len(self.tier2_scorers),
            tier1_scorers=[s.scorer_id for s in self.tier1_scorers],
            tier2_scorers=[s.scorer_id for s in self.tier2_scorers],
            total_tier2_weight=sum(s.weight for s in self.tier2_scorers),
        )

    def _validate_weights(self):
        """Validate that Tier 2 weights sum to 1.0."""
        total_weight = sum(s.weight for s in self.tier2_scorers)

        if not self.tier2_scorers:
            logger.warning("No Tier 2 scorers enabled")
            return

        tolerance = self.config.get("weight_tolerance", 0.01)
        if abs(total_weight - 1.0) > tolerance:
            raise ValueError(
                f"Tier 2 weights must sum to 1.0 (current: {total_weight:.4f}). "
                f" Scorers: {[(s.scorer_id, s.weight) for s in self.tier2_scorers]}"
            )

        logger.debug("Tier 2 weights validated", total_weight=total_weight)

    async def score_candidate(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
        recent_nodes: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]],
    ) -> ScoringResult:
        """Score a single (strategy, focus) candidate using two-tier approach.

        Args:
            strategy: Strategy dict with priority_base
            focus: Focus dict
            graph_state: Current graph state
            recent_nodes: List of recent node dicts
            conversation_history: Recent conversation turns

        Returns:
            ScoringResult with final score and complete reasoning
        """
        reasoning_trace = []
        tier1_outputs = []
        tier2_outputs = []

        # Get base score from strategy
        base_score = strategy.get("priority_base", 1.0)
        reasoning_trace.append(f"Base score: {base_score:.{self._score_precision}f}")

        # ===== TIER 1: Hard Constraints =====
        for scorer in self.tier1_scorers:
            try:
                output = await scorer.evaluate(
                    strategy=strategy,
                    focus=focus,
                    graph_state=graph_state,
                    recent_nodes=recent_nodes,
                    conversation_history=conversation_history,
                )
                tier1_outputs.append(output)

                # Log the evaluation
                trace = (
                    f"{output.scorer_id}: "
                    f"{'VETO' if output.is_veto else 'PASS'} - {output.reasoning}"
                )
                reasoning_trace.append(trace)
                logger.debug(
                    "Tier1 evaluation",
                    scorer=output.scorer_id,
                    is_veto=output.is_veto,
                    reasoning=output.reasoning,
                )

                # Early exit on veto
                if output.is_veto and self._veto_on_first:
                    logger.info(
                        "Candidate vetoed",
                        scorer=output.scorer_id,
                        strategy=strategy.get("id"),
                        focus_type=focus.get("focus_type"),
                        reasoning=output.reasoning,
                    )
                    return ScoringResult(
                        strategy=strategy,
                        focus=focus,
                        final_score=0.0,
                        tier1_outputs=tier1_outputs,
                        tier2_outputs=[],
                        vetoed_by=output.scorer_id,
                        reasoning_trace=reasoning_trace,
                    )

            except Exception as e:
                logger.warning(
                    "Tier1 scorer failed",
                    scorer=scorer.scorer_id,
                    error=str(e),
                    strategy=strategy.get("id"),
                )
                reasoning_trace.append(f"{scorer.scorer_id}: ERROR - {str(e)}")
                # Continue with other scorers

        # ===== TIER 2: Weighted Additive Scoring =====
        final_score = base_score
        tier2_contribution = 0.0

        for scorer in self.tier2_scorers:
            try:
                output = await scorer.score(
                    strategy=strategy,
                    focus=focus,
                    graph_state=graph_state,
                    recent_nodes=recent_nodes,
                    conversation_history=conversation_history,
                )
                tier2_outputs.append(output)

                # Add weighted contribution
                final_score += output.contribution
                tier2_contribution += output.contribution

                # Log the scoring
                trace = (
                    f"{output.scorer_id}: "
                    f"{output.raw_score:.{self._score_precision}f} × "
                    f"{output.weight:.2f} = "
                    f"{output.contribution:.{self._score_precision}f} → "
                    f"cumulative={final_score:.{self._score_precision}f}"
                )
                reasoning_trace.append(trace + f" ({output.reasoning})")
                logger.debug(
                    "Tier2 scoring",
                    scorer=output.scorer_id,
                    raw_score=output.raw_score,
                    weight=output.weight,
                    contribution=output.contribution,
                    cumulative=final_score,
                )

            except Exception as e:
                logger.warning(
                    "Tier2 scorer failed",
                    scorer=scorer.scorer_id,
                    error=str(e),
                    strategy=strategy.get("id"),
                )
                reasoning_trace.append(f"{scorer.scorer_id}: ERROR - {str(e)}")
                # Continue with other scorers

        logger.debug(
            "Scoring complete",
            strategy=strategy.get("id"),
            focus_type=focus.get("focus_type"),
            final_score=final_score,
            tier1_count=len(tier1_outputs),
            tier2_count=len(tier2_outputs),
        )

        return ScoringResult(
            strategy=strategy,
            focus=focus,
            final_score=final_score,
            tier1_outputs=tier1_outputs,
            tier2_outputs=tier2_outputs,
            vetoed_by=None,
            reasoning_trace=reasoning_trace,
        )

    async def score_all_candidates(
        self,
        candidates: List[tuple[Dict[str, Any], Dict[str, Any]]],
        graph_state: GraphState,
        recent_nodes: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]],
    ) -> List[ScoringResult]:
        """Score multiple (strategy, focus) candidates.

        Args:
            candidates: List of (strategy, focus) tuples
            graph_state: Current graph state
            recent_nodes: List of recent node dicts
            conversation_history: Recent conversation turns

        Returns:
            List of ScoringResults, sorted by final_score (descending)
        """
        results = []

        for strategy, focus in candidates:
            result = await self.score_candidate(
                strategy=strategy,
                focus=focus,
                graph_state=graph_state,
                recent_nodes=recent_nodes,
                conversation_history=conversation_history,
            )
            results.append(result)

        # Sort by final score (descending), vetoed candidates go to bottom
        results.sort(key=lambda r: (0 if r.vetoed_by else 1, r.final_score), reverse=True)

        logger.info(
            "Scored all candidates",
            total_candidates=len(candidates),
            vetoed_count=sum(1 for r in results if r.vetoed_by),
            top_score=results[0].final_score if results else 0,
            top_strategy=results[0].strategy.get("id") if results else None,
        )

        return results

    def __repr__(self) -> str:
        return (
            f"TwoTierScoringEngine("
            f"tier1={len(self.tier1_scorers)}, "
            f"tier2={len(self.tier2_scorers)})"
        )
