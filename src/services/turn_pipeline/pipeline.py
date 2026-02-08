"""
Pipeline orchestrator for turn processing.

ADR-008 Phase 3: TurnPipeline executes stages sequentially with timing and error handling.
"""

import time
from typing import List

import structlog

from .base import TurnStage
from .context import PipelineContext
from .result import TurnResult

log = structlog.get_logger(__name__)


class TurnPipeline:
    """
    Orchestrates execution of pipeline stages.

    Executes stages sequentially, tracking timing and handling errors.
    """

    def __init__(self, stages: List[TurnStage]):
        """
        Initialize pipeline with a list of stages.

        Args:
            stages: Ordered list of TurnStage instances
        """
        self.stages = stages
        self.logger = log

    async def execute(self, context: PipelineContext) -> TurnResult:
        """
        Execute all stages sequentially.

        Args:
            context: Initial turn context with session_id and user_input

        Returns:
            TurnResult with extraction, graph state, next question

        Raises:
            Exception: If any stage fails
        """
        start_time = time.perf_counter()

        self.logger.info(
            "pipeline_started",
            session_id=context.session_id,
            num_stages=len(self.stages),
        )

        for stage in self.stages:
            stage_start = time.perf_counter()

            try:
                self.logger.debug(
                    "stage_started",
                    stage_name=stage.stage_name,
                    session_id=context.session_id,
                )

                context = await stage.process(context)

                stage_elapsed = (time.perf_counter() - stage_start) * 1000
                context.stage_timings[stage.stage_name] = stage_elapsed

                self.logger.debug(
                    "stage_completed",
                    stage_name=stage.stage_name,
                    duration_ms=stage_elapsed,
                )

            except Exception as e:
                self.logger.error(
                    "stage_failed",
                    stage_name=stage.stage_name,
                    error=str(e),
                    exc_info=True,
                )
                raise

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        self.logger.info(
            "pipeline_completed",
            session_id=context.session_id,
            turn_number=context.turn_number,
            latency_ms=latency_ms,
            stage_timings=context.stage_timings,
        )

        return self._build_result(context, latency_ms)

    def _build_result(self, context: PipelineContext, latency_ms: int) -> TurnResult:
        """
        Build TurnResult from context.

        Args:
            context: Final turn context
            latency_ms: Total pipeline latency

        Returns:
            TurnResult
        """
        # Build extracted data
        extracted = {
            "concepts": [],
            "relationships": [],
        }

        if context.extraction:
            extracted["concepts"] = [
                {
                    "text": c.text,
                    "type": c.node_type,
                    "confidence": c.confidence,
                }
                for c in context.extraction.concepts
            ]
            extracted["relationships"] = [
                {
                    "source": r.source_text,
                    "target": r.target_text,
                    "type": r.relationship_type,
                }
                for r in context.extraction.relationships
            ]

        # Build graph state
        graph_state = {}
        if context.graph_state:
            graph_state = {
                "node_count": context.graph_state.node_count,
                "edge_count": context.graph_state.edge_count,
                "depth_achieved": context.graph_state.nodes_by_type,
            }

        # Safely access stage outputs (may be None for partial pipeline execution)
        # Access contracts directly to avoid RuntimeError from convenience properties
        turn_number = (
            context.context_loading_output.turn_number
            if context.context_loading_output
            else 1
        )
        strategy_selected = (
            context.strategy_selection_output.strategy
            if context.strategy_selection_output
            else None
        )
        next_question = (
            context.question_generation_output.question
            if context.question_generation_output
            else ""
        )
        should_continue = (
            context.continuation_output.should_continue
            if context.continuation_output
            else True
        )
        termination_reason = (
            context.continuation_output.reason
            if context.continuation_output and not should_continue
            else None
        )

        # Extract methodology signals and strategy alternatives for observability
        signals = None
        strategy_alternatives = None
        if context.strategy_selection_output:
            signals = context.strategy_selection_output.signals
            # Convert tuples to dicts for JSON serialization
            alternatives = context.strategy_selection_output.strategy_alternatives
            if alternatives:
                strategy_alternatives = []
                for alt in alternatives:
                    if len(alt) == 2:
                        strategy, score = alt
                        strategy_alternatives.append({"strategy": strategy, "score": score})
                    elif len(alt) == 3:
                        strategy, node_id, score = alt
                        strategy_alternatives.append({
                            "strategy": strategy,
                            "node_id": node_id,
                            "score": score
                        })

        # Phase 3 (Dual-Graph Integration), bead 0nl3: Build canonical_graph and graph_comparison
        canonical_graph = None
        graph_comparison = None

        if context.canonical_graph_state:
            cg_state = context.canonical_graph_state
            canonical_graph = {
                "slots": {
                    "concept_count": cg_state.concept_count,
                    "orphan_count": cg_state.orphan_count,
                    "avg_support": round(cg_state.avg_support, 2),
                },
                "edges": {
                    "edge_count": cg_state.edge_count,
                },
                "metrics": {
                    "max_depth": cg_state.max_depth,
                },
            }

            # Build graph_comparison metrics
            if context.graph_state:
                surface_nodes = context.graph_state.node_count
                canonical_nodes = cg_state.concept_count
                node_reduction_pct = (
                    (1 - canonical_nodes / surface_nodes) * 100
                    if surface_nodes > 0
                    else 0.0
                )

                surface_edges = context.graph_state.edge_count
                canonical_edges = cg_state.edge_count
                edge_aggregation_ratio = (
                    canonical_edges / surface_edges
                    if surface_edges > 0
                    else 0.0
                )

                # Orphan improvement: canonical graph has fewer orphans (due to aggregation)
                # Placeholder value since surface orphan computation is not yet implemented
                orphan_improvement_pct = 0.0

                graph_comparison = {
                    "node_reduction_pct": round(node_reduction_pct, 1),
                    "edge_aggregation_ratio": round(edge_aggregation_ratio, 2),
                    "orphan_improvement_pct": round(orphan_improvement_pct, 1),
                }

        return TurnResult(
            turn_number=turn_number,
            extracted=extracted,
            graph_state=graph_state,
            scoring=context.scoring
            or {
                "depth": 0.0,
                "saturation": 0.0,
            },
            strategy_selected=strategy_selected,
            next_question=next_question,
            should_continue=should_continue,
            latency_ms=latency_ms,
            signals=signals,
            strategy_alternatives=strategy_alternatives,
            termination_reason=termination_reason,
            canonical_graph=canonical_graph,
            graph_comparison=graph_comparison,
        )
