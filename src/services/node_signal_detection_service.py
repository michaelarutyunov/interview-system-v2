"""
Node-level signal detection service.

Extracts node signal detection from MethodologyStrategyService for single responsibility.
"""

from typing import TYPE_CHECKING, Any, Dict

import structlog

from src.core.exceptions import ScorerFailureError

if TYPE_CHECKING:
    from src.domain.models.knowledge_graph import GraphState
    from src.services.turn_pipeline.context import PipelineContext
    from src.services.node_state_tracker import NodeStateTracker

log = structlog.get_logger(__name__)


class NodeSignalDetectionService:
    """Detects node-level signals for all tracked nodes.

    Node signals include:
    - graph.node.exhausted: Whether node has been fully explored
    - graph.node.exhaustion_score: Continuous exhaustion score (0.0-1.0)
    - graph.node.yield_stagnation: Turns since last new info from node
    - graph.node.focus_streak: Consecutive turns focused on node
    - graph.node.is_current_focus: Whether node is current focus
    - graph.node.recency_score: How recently node was added
    - graph.node.is_orphan: Whether node has no edges
    - graph.node.edge_count: Number of edges connected to node
    - graph.node.has_outgoing: Whether node has outgoing edges
    - technique.node.strategy_repetition: Times same strategy used on node
    """

    async def detect(
        self,
        context: "PipelineContext",
        graph_state: "GraphState",
        response_text: str,
        node_tracker: "NodeStateTracker",
    ) -> Dict[str, Dict[str, Any]]:
        """
        Detect node-level signals for all tracked nodes.

        Args:
            context: Pipeline context
            graph_state: Current knowledge graph state
            response_text: User's response text
            node_tracker: NodeStateTracker with node states

        Returns:
            Dict mapping node_id to dict of signal_name: value
            Example: {"node-123": {"graph.node.exhausted": True, ...}}
        """
        # Import node signal detectors (consolidated modules)
        from src.signals.graph.node_signals import (
            NodeExhaustedSignal,
            NodeExhaustionScoreSignal,
            NodeYieldStagnationSignal,
            NodeFocusStreakSignal,
            NodeIsCurrentFocusSignal,
            NodeRecencyScoreSignal,
            NodeIsOrphanSignal,
            NodeEdgeCountSignal,
            NodeHasOutgoingSignal,
        )
        from src.signals.session.node_strategy_repetition import (
            NodeStrategyRepetitionSignal,
        )

        # Get all tracked nodes
        all_states = node_tracker.get_all_states()

        if not all_states:
            log.warning(
                "no_tracked_nodes_for_signals",
                session_id=context.session_id
                if hasattr(context, "session_id")
                else None,
                turn_number=context.turn_number
                if hasattr(context, "turn_number")
                else None,
                graph_node_count=graph_state.node_count if graph_state else 0,
            )
            return {}

        # Initialize node signals dict
        node_signals: Dict[str, Dict[str, Any]] = {
            node_id: {} for node_id in all_states.keys()
        }

        # List of node signal detectors to run
        # These detectors take node_tracker in their constructor
        signal_detectors = [
            NodeExhaustedSignal(node_tracker),
            NodeExhaustionScoreSignal(node_tracker),
            NodeYieldStagnationSignal(node_tracker),
            NodeFocusStreakSignal(node_tracker),
            NodeIsCurrentFocusSignal(node_tracker),
            NodeRecencyScoreSignal(node_tracker),
            NodeIsOrphanSignal(node_tracker),
            NodeEdgeCountSignal(node_tracker),
            NodeHasOutgoingSignal(node_tracker),
            NodeStrategyRepetitionSignal(node_tracker),
        ]

        # Detect all node signals
        signals_detected_count = 0
        for detector in signal_detectors:
            try:
                detected = await detector.detect(context, graph_state, response_text)

                # Merge results into node_signals
                detector_count = 0
                for node_id, signal_value in detected.items():
                    if node_id in node_signals:
                        node_signals[node_id][detector.signal_name] = signal_value
                        detector_count += 1

                signals_detected_count += detector_count

                # Log if detector produced no results for any node
                if detector_count == 0:
                    log.debug(
                        "node_signal_detector_no_results",
                        signal=detector.signal_name,
                        tracked_nodes=len(all_states),
                    )

            except Exception as e:
                log.error(
                    "node_signal_detection_failed",
                    signal=detector.signal_name,
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )
                raise ScorerFailureError(
                    f"Node signal detector '{detector.signal_name}' failed during detection. "
                    f"Original error: {type(e).__name__}: {e}. "
                    f"Check that the signal detector is properly configured and "
                    f"that all required data (context, graph_state, node_tracker) is available."
                ) from e

        log.debug(
            "node_signals_detected",
            node_count=len(node_signals),
        )

        return node_signals
