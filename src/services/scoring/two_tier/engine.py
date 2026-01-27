"""Two-tier hybrid scoring engine.

Implements the two-tier approach:
- Tier 1: Hard constraints (boolean vetoes) with early exit
- Tier 2: Weighted additive scoring for ranking valid candidates
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import structlog

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.two_tier.base import (
    Tier1Scorer,
    Tier1Output,
    Tier2Scorer,
    Tier2Output,
)
from src.core.exceptions import ScorerFailureError

if TYPE_CHECKING:
    from src.domain.models.pipeline_contracts import (
        Focus,
        VetoResult,
        WeightedResult,
        ScoredStrategy,
        StrategySelectionResult,
    )

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
    scorer_sum: Optional[float] = (
        None  # Sum of weighted scorer outputs (before phase multiplier)
    )
    phase_multiplier: Optional[float] = None  # Phase multiplier applied to scorer_sum


class TwoTierScoringEngine:
    """
    Orchestrates two-tier hybrid scoring for strategy selection.

    Scoring pipeline:
    1. Run all Tier 1 scorers sequentially
    2. If any veto → return vetoed result (early exit)
    3. If all pass → run all Tier 2 scorers
    4. Compute final score: scorer_sum × phase_multiplier
       where scorer_sum = Σ(strategy_weight × raw_score)
    5. Return complete result with reasoning trace

    Features:
    - Early exit on first veto (performance)
    - Complete reasoning trace for debugging
    - Strategy-scorer weight matrix from config
    - Phase-based modulation (exploratory/focused/closing)
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

        # Load phase profiles from config
        self.phase_profiles = self.config.get("phase_profiles", {})
        if not self.phase_profiles:
            logger.warning("No phase_profiles configured, using defaults")
            self.phase_profiles = {
                "exploratory": {},
                "focused": {},
                "closing": {},
            }

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
            phases_available=list(self.phase_profiles.keys()),
        )

    def _validate_weights(self):
        """Validate strategy_weights configuration.

        With the new formula, we don't require weights to sum to 1.0 anymore.
        Instead, we validate that each scorer has at least a default weight.
        """
        if not self.tier2_scorers:
            logger.warning("No Tier 2 scorers enabled")
            return

        # Check that each scorer has strategy_weights configured
        for scorer in self.tier2_scorers:
            strategy_weights = scorer.config.get("strategy_weights", {})
            if "default" not in strategy_weights:
                logger.warning(
                    f"Scorer {scorer.scorer_id} has no 'default' weight in strategy_weights. "
                    f"Will use 0.1 as fallback."
                )

        logger.debug(
            "Tier 2 scorers validated",
            num_scorers=len(self.tier2_scorers),
            scorer_ids=[s.scorer_id for s in self.tier2_scorers],
        )

    async def score_candidate(
        self,
        strategy: Dict[str, Any],
        focus: Dict[str, Any],
        graph_state: GraphState,
        recent_nodes: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]],
        phase: Optional[str] = None,
    ) -> ScoringResult:
        """Score a single (strategy, focus) candidate using two-tier approach.

        Args:
            strategy: Strategy dict
            focus: Focus dict
            graph_state: Current graph state
            recent_nodes: List of recent node dicts
            conversation_history: Recent conversation turns
            phase: Current interview phase (exploratory/focused/closing).
                   If None, defaults to 'exploratory'.

        Returns:
            ScoringResult with final score and complete reasoning
        """
        reasoning_trace = []
        tier1_outputs = []
        tier2_outputs = []

        # Determine phase (default to exploratory if not specified)
        if phase is None:
            phase = graph_state.properties.get("phase", "exploratory")

        reasoning_trace.append(f"Phase: {phase}")

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
                logger.error(
                    "Tier1 scorer failed - terminating interview",
                    scorer=scorer.scorer_id,
                    error=str(e),
                    strategy=strategy.get("id"),
                    exc_info=True,
                )
                raise ScorerFailureError(
                    f"Tier 1 scorer {scorer.scorer_id} failed: {str(e)}"
                ) from e

        # ===== TIER 2: Weighted Additive Scoring =====
        # Step 1: Sum weighted scorer outputs for this strategy
        scorer_sum = 0.0

        for scorer in self.tier2_scorers:
            try:
                # Get strategy-specific weight from config
                strategy_weights = scorer.config.get("strategy_weights", {})
                strategy_weight = strategy_weights.get(
                    strategy.get("id"), strategy_weights.get("default", 0.1)
                )

                # Scorer returns raw score (independent of weights)
                output = await scorer.score(
                    strategy=strategy,
                    focus=focus,
                    graph_state=graph_state,
                    recent_nodes=recent_nodes,
                    conversation_history=conversation_history,
                )
                tier2_outputs.append(output)

                # Apply strategy_weight to raw_score
                contribution = strategy_weight * output.raw_score
                scorer_sum += contribution

                # Update output with strategy weight for debugging
                output.weight = strategy_weight
                output.contribution = contribution

                # Log the scoring
                trace = (
                    f"{output.scorer_id}: "
                    f"raw={output.raw_score:.{self._score_precision}f} × "
                    f"strategy_weight={strategy_weight:.2f} = "
                    f"{contribution:.{self._score_precision}f} → "
                    f"scorer_sum={scorer_sum:.{self._score_precision}f}"
                )
                reasoning_trace.append(trace + f" ({output.reasoning})")
                logger.debug(
                    "Tier2 scoring",
                    scorer=output.scorer_id,
                    raw_score=output.raw_score,
                    strategy_weight=strategy_weight,
                    contribution=contribution,
                    scorer_sum=scorer_sum,
                )

            except Exception as e:
                logger.error(
                    "Tier2 scorer failed - terminating interview",
                    scorer=scorer.scorer_id,
                    error=str(e),
                    strategy=strategy.get("id"),
                    exc_info=True,
                )
                raise ScorerFailureError(
                    f"Tier 2 scorer {scorer.scorer_id} failed: {str(e)}"
                ) from e

        # Step 2: Apply phase multiplier
        phase_key = phase or "exploratory"
        phase_profile = self.phase_profiles.get(phase_key, {})
        strategy_id = strategy.get("id") or ""
        phase_multiplier = phase_profile.get(strategy_id, 1.0)
        final_score = scorer_sum * phase_multiplier

        reasoning_trace.append(
            f"Phase multiplier: {phase_multiplier:.2f} → "
            f"final_score = {scorer_sum:.{self._score_precision}f} × {phase_multiplier:.2f} = "
            f"{final_score:.{self._score_precision}f}"
        )

        logger.debug(
            "Scoring complete",
            strategy=strategy.get("id"),
            focus_type=focus.get("focus_type"),
            phase=phase,
            scorer_sum=scorer_sum,
            phase_multiplier=phase_multiplier,
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
            scorer_sum=scorer_sum,
            phase_multiplier=phase_multiplier,
        )

    async def score_all_candidates(
        self,
        candidates: List[tuple[Dict[str, Any], Dict[str, Any]]],
        graph_state: GraphState,
        recent_nodes: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]],
        phase: Optional[str] = None,
    ) -> List[ScoringResult]:
        """Score multiple (strategy, focus) candidates.

        Args:
            candidates: List of (strategy, focus) tuples
            graph_state: Current graph state
            recent_nodes: List of recent node dicts
            conversation_history: Recent conversation turns
            phase: Current interview phase (exploratory/focused/closing).
                   If None, defaults to graph_state.phase or 'exploratory'.

        Returns:
            List of ScoringResults, sorted by final_score (descending)
        """
        results = []

        # Determine phase once for all candidates
        if phase is None:
            phase = graph_state.properties.get("phase", "exploratory")

        for strategy, focus in candidates:
            result = await self.score_candidate(
                strategy=strategy,
                focus=focus,
                graph_state=graph_state,
                recent_nodes=recent_nodes,
                conversation_history=conversation_history,
                phase=phase,
            )
            results.append(result)

        # Sort by final score (descending), vetoed candidates go to bottom
        results.sort(
            key=lambda r: (0 if r.vetoed_by else 1, r.final_score), reverse=True
        )

        logger.info(
            "Scored all candidates",
            phase=phase,
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


# =============================================================================
# ADR-010 Phase 2: Conversion Functions for New Schema
# =============================================================================

"""
Conversion functions to transform dataclass-based ScoringResult
into Pydantic-based StrategySelectionResult.

These functions maintain backward compatibility while enabling
the new type-safe schema.
"""


def _convert_focus_to_pydantic(focus_dict: Dict[str, Any]) -> Focus:
    """Convert focus dict to Pydantic Focus model."""
    from src.domain.models.pipeline_contracts import Focus

    return Focus(
        focus_type=focus_dict.get("focus_type", "unknown"),
        focus_description=focus_dict.get("focus_description", ""),
        node_id=focus_dict.get("node_id"),
        element_id=focus_dict.get("element_id"),
    )


def _convert_tier1_output_to_veto_result(output: Tier1Output) -> VetoResult:
    """Convert Tier1Output to VetoResult Pydantic model."""
    from src.domain.models.pipeline_contracts import VetoResult

    return VetoResult(
        scorer_id=output.scorer_id,
        is_veto=output.is_veto,
        reasoning=output.reasoning,
        signals=output.signals,
    )


def _convert_tier2_output_to_weighted_result(output: Tier2Output) -> WeightedResult:
    """Convert Tier2Output to WeightedResult Pydantic model."""
    from src.domain.models.pipeline_contracts import WeightedResult

    return WeightedResult(
        scorer_id=output.scorer_id,
        raw_score=output.raw_score,
        weight=output.weight,
        contribution=output.contribution,
        reasoning=output.reasoning,
        signals=output.signals,
    )


def convert_scoring_result_to_scored_strategy(
    scoring_result: ScoringResult,
    is_selected: bool = False,
) -> ScoredStrategy:
    """Convert ScoringResult dataclass to ScoredStrategy Pydantic model.

    Args:
        scoring_result: The dataclass-based ScoringResult
        is_selected: Whether this strategy was the winner

    Returns:
        ScoredStrategy Pydantic model
    """
    from src.domain.models.pipeline_contracts import ScoredStrategy

    # Convert focus dict to Pydantic model
    focus = _convert_focus_to_pydantic(scoring_result.focus)

    # Convert Tier 1 outputs
    tier1_results = [
        _convert_tier1_output_to_veto_result(o) for o in scoring_result.tier1_outputs
    ]

    # Convert Tier 2 outputs
    tier2_results = [
        _convert_tier2_output_to_weighted_result(o)
        for o in scoring_result.tier2_outputs
    ]

    # Build reasoning string from trace
    reasoning = "\n".join(scoring_result.reasoning_trace)

    return ScoredStrategy(
        strategy_id=scoring_result.strategy.get("id", "unknown"),
        strategy_name=scoring_result.strategy.get("name", ""),
        focus=focus,
        tier1_results=tier1_results,
        tier2_results=tier2_results,
        tier2_score=scoring_result.scorer_sum or 0.0,
        final_score=scoring_result.final_score,
        is_selected=is_selected,
        vetoed_by=scoring_result.vetoed_by,
        reasoning=reasoning,
    )


def convert_selection_to_strategy_selection_result(
    session_id: str,
    turn_number: int,
    phase: str,
    phase_multiplier: float,
    selected_result: ScoringResult,
    alternative_results: List[ScoringResult],
    total_candidates: int,
    vetoed_count: int,
) -> StrategySelectionResult:
    """Convert selection data to StrategySelectionResult Pydantic model.

    Args:
        session_id: Session identifier
        turn_number: Turn number
        phase: Interview phase
        phase_multiplier: Phase multiplier applied
        selected_result: ScoringResult for the winning strategy
        alternative_results: List of ScoringResults for runner-ups
        total_candidates: Total number of candidates evaluated
        vetoed_count: Number of vetoed candidates

    Returns:
        StrategySelectionResult Pydantic model
    """
    from src.domain.models.pipeline_contracts import StrategySelectionResult

    # Convert selected strategy
    selected_strategy = convert_scoring_result_to_scored_strategy(
        selected_result, is_selected=True
    )

    # Convert alternatives
    alternatives = [
        convert_scoring_result_to_scored_strategy(r, is_selected=False)
        for r in alternative_results
    ]

    return StrategySelectionResult(
        session_id=session_id,
        turn_number=turn_number,
        phase=phase,
        phase_multiplier=phase_multiplier,
        selected_strategy=selected_strategy,
        alternatives=alternatives,
        total_candidates=total_candidates,
        vetoed_count=vetoed_count,
    )
