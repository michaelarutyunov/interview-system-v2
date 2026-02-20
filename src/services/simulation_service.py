"""AI-to-AI simulation service for automated interview testing.

Orchestrates SessionService (interviewer) with SyntheticService (respondent)
to generate complete interview simulations for testing and validation.

Usage:
    - Pass concept_id and persona_id to simulate a full interview
    - Service extracts product_name and objective from concept
    - Runs interview until max_turns or close strategy
    - Returns complete transcript with turn-by-turn analysis
    - Automatically saves JSON results to synthetic_interviews/

Key Design:
    - No graph state sharing between services
    - Synthetic service receives interview context (product_name, turn_number)
    - Session service controls max_turns (NOT synthetic service)
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

import structlog

from src.core.concept_loader import load_concept
from src.services.session_service import SessionService
from src.services.synthetic_service import SyntheticService
from src.persistence.repositories.session_repo import SessionRepository
from src.persistence.repositories.graph_repo import GraphRepository
from src.api.dependencies import (
    get_shared_extraction_client,
    get_shared_generation_client,
)
from src.domain.models.session import Session, SessionState
from src.domain.models.interview_state import InterviewMode

log = structlog.get_logger(__name__)

# Output directory for synthetic interview results
SYNTHETIC_OUTPUT_DIR = Path("synthetic_interviews")


@dataclass
class SimulationTurn:
    """Single turn in simulated interview.

    Contains the question asked, synthetic response generated, strategy selected,
    and observability data including signals and alternatives.
    """

    turn_number: int
    question: str
    response: str
    persona: str
    persona_name: str
    strategy_selected: Optional[str] = None
    should_continue: bool = True
    latency_ms: int = 0
    # Methodology-based signal detection observability
    signals: Optional[Dict[str, Any]] = None
    strategy_alternatives: Optional[List[Dict[str, Any]]] = None
    # Termination reason (populated when should_continue=False)
    termination_reason: Optional[str] = None
    # Graph changes this turn for turn-by-turn evolution analysis (cu72.2)
    nodes_added: Optional[List[Dict[str, Any]]] = None
    edges_added: Optional[List[Dict[str, Any]]] = None
    extraction_summary: Optional[Dict[str, Any]] = None
    # Saturation tracking metrics from StateComputationStage
    saturation_metrics: Optional[Dict[str, Any]] = None
    # Per-node signals from StrategySelectionStage (Stage 6)
    node_signals: Optional[Dict[str, Any]] = None


@dataclass
class SimulationResult:
    """Result of simulated interview.

    Contains complete interview transcript with turn-by-turn analysis,
    knowledge graph diagnostics for both surface and canonical graphs,
    and session metadata.
    """

    concept_id: str
    concept_name: str
    product_name: str
    objective: str
    methodology: str
    persona_id: str
    persona_name: str
    session_id: str
    total_turns: int
    turns: List[SimulationTurn] = field(default_factory=list)
    status: str = "completed"  # completed, max_turns_reached, error

    # Surface graph diagnostics (kg_nodes, kg_edges)
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)

    # Canonical graph diagnostics (canonical_slots, canonical_edges)
    canonical_slots: List[Dict[str, Any]] = field(default_factory=list)
    canonical_edges: List[Dict[str, Any]] = field(default_factory=list)


class SimulationService:
    """Service for AI-to-AI interview simulation.

    Orchestrates interviewer AI (SessionService) with synthetic respondent AI
    to generate complete interview transcripts for testing and validation.
    """

    DEFAULT_MAX_TURNS = 10  # Default for simulations (shorter than real interviews)
    DEFAULT_PERSONA = "health_conscious"

    def __init__(
        self,
        session_service: SessionService,
        synthetic_service: Optional[SyntheticService] = None,
    ):
        """Initialize simulation service with required dependencies.

        Args:
            session_service: Session service for interviewer AI
            synthetic_service: Synthetic service for respondent AI (creates default if None)
        """
        self.session = session_service
        self.synthetic = synthetic_service or SyntheticService()

        log.info(
            "simulation_service_initialized",
            default_persona=self.DEFAULT_PERSONA,
            default_max_turns=self.DEFAULT_MAX_TURNS,
        )

    async def simulate_interview(
        self,
        concept_id: str,
        persona_id: str = DEFAULT_PERSONA,
        max_turns: int = DEFAULT_MAX_TURNS,
        session_id: Optional[str] = None,
    ) -> SimulationResult:
        """Simulate a complete AI-to-AI interview.

        Args:
            concept_id: Concept ID (e.g., 'oat_milk_v2')
            persona_id: Persona ID for synthetic respondent
            max_turns: Maximum turns before forcing stop (controlled by SessionService)
            session_id: Optional session ID (generates new if None)

        Returns:
            SimulationResult with complete transcript, graph diagnostics, and metadata

        Raises:
            ValueError: If concept or persona not found
        """
        # Load concept to get product_name and objective
        concept = load_concept(concept_id)

        # Extract product_name from concept.name
        product_name = concept.name

        # Extract objective from concept context
        objective = concept.context.objective or concept.name

        # Validate persona
        from src.llm.prompts.synthetic import get_available_personas

        available_personas = get_available_personas()
        if persona_id not in available_personas:
            raise ValueError(
                f"Unknown persona: {persona_id}. "
                f"Available: {', '.join(available_personas.keys())}"
            )
        persona_name = available_personas[persona_id]

        # Generate session_id if not provided
        if session_id is None:
            import uuid

            session_id = str(uuid.uuid4())

        log.info(
            "simulation_started",
            session_id=session_id,
            concept_id=concept_id,
            product_name=product_name,
            persona_id=persona_id,
            max_turns=max_turns,
        )

        # Create session in repository with max_turns override
        await self._create_simulation_session(
            session_id=session_id,
            concept_id=concept_id,
            concept_name=concept.name,
            methodology=concept.methodology,
            max_turns=max_turns,
        )

        # Generate opening question
        opening_question = await self.session.start_session(session_id)

        turns: List[SimulationTurn] = []
        turn_number = 0

        # Process opening with synthetic response
        turn_result = await self._simulate_turn(
            session_id=session_id,
            turn_number=turn_number,
            question=opening_question,
            persona_id=persona_id,
            product_name=product_name,
        )
        turns.append(turn_result)

        # Continue until should_continue is False or max_turns
        while turn_result.should_continue and turn_number < max_turns:
            # Get next question from session service
            # (process_turn will handle extraction, graph update, strategy selection)
            turn_result_session = await self.session.process_turn(
                session_id=session_id,
                user_input=turn_result.response,
            )

            turn_number += 1

            # Generate synthetic response
            turn_result = await self._simulate_turn(
                session_id=session_id,
                turn_number=turn_number,
                question=turn_result_session.next_question,
                persona_id=persona_id,
                product_name=product_name,
                strategy_selected=turn_result_session.strategy_selected,
                should_continue=turn_result_session.should_continue,
                signals=turn_result_session.signals,
                strategy_alternatives=turn_result_session.strategy_alternatives,
                termination_reason=turn_result_session.termination_reason,
                context_nodes_added=turn_result_session.nodes_added,
                context_edges_added=turn_result_session.edges_added,
                saturation_metrics=turn_result_session.saturation_metrics,
                node_signals=turn_result_session.node_signals,
            )
            turns.append(turn_result)

            # Rate limit pacing: small delay between turns to avoid hitting
            # Kimi rate limits (simulation runs faster than human-paced interviews)
            await asyncio.sleep(0.5)

        # NEW: Fetch graph data for diagnostics (after loop, before result creation)
        (
            nodes_data,
            edges_data,
            canonical_slots_data,
            canonical_edges_data,
        ) = await self._serialize_graph_data(session_id)

        # Determine status from termination reason
        if turn_result.should_continue:
            # Loop was terminated by turn count reaching max_turns
            status = "completed"
        elif turn_result.termination_reason:
            # Use actual termination reason (e.g., "graph_saturated", "close_strategy")
            status = turn_result.termination_reason
        else:
            # Fallback
            status = "max_turns_reached"

        result = SimulationResult(
            concept_id=concept_id,
            concept_name=concept.name,
            product_name=product_name,
            objective=objective,
            methodology=concept.methodology,
            persona_id=persona_id,
            persona_name=persona_name,
            session_id=session_id,
            total_turns=len(turns),
            turns=turns,
            status=status,
            nodes=nodes_data,
            edges=edges_data,
            canonical_slots=canonical_slots_data,
            canonical_edges=canonical_edges_data,
        )

        log.info(
            "simulation_completed",
            session_id=session_id,
            total_turns=result.total_turns,
            status=result.status,
        )

        # Automatically save to JSON
        await self._save_simulation_result(result)

        return result

    async def _simulate_turn(
        self,
        session_id: str,
        turn_number: int,
        question: str,
        persona_id: str,
        product_name: str,
        strategy_selected: Optional[str] = None,
        should_continue: bool = True,
        signals: Optional[Dict[str, Any]] = None,
        strategy_alternatives: Optional[List[Dict[str, Any]]] = None,
        termination_reason: Optional[str] = None,
        context_nodes_added: Optional[List[Any]] = None,
        context_edges_added: Optional[List[Dict[str, Any]]] = None,
        saturation_metrics: Optional[Dict[str, Any]] = None,
        node_signals: Optional[Dict[str, Any]] = None,
    ) -> SimulationTurn:
        """Simulate a single interview turn.

        Generates synthetic response to interviewer's question using the specified
        persona and interview context.

        Args:
            session_id: Session ID
            turn_number: Turn number
            question: Interviewer's question
            persona_id: Persona ID
            product_name: Product name for context
            strategy_selected: Strategy selected by interviewer
            should_continue: Whether interview should continue
            signals: Methodology signals from signal pools
            strategy_alternatives: Alternative strategies with scores
            termination_reason: Reason for termination (if should_continue=False)

        Returns:
            SimulationTurn with question and response
        """
        # Get graph state to extract previous concepts
        assert self.session.graph is not None, (
            "SessionService.graph must be initialized"
        )
        graph_state = await self.session.graph.get_graph_state(session_id)

        # Build interview context for synthetic service
        interview_context = {
            "product_name": product_name,
            "turn_number": turn_number + 1,  # 1-indexed for display
        }

        # Generate synthetic response
        synthetic_response = await self.synthetic.generate_response(
            question=question,
            session_id=session_id,
            persona=persona_id,
            graph_state=graph_state,
            interview_context=interview_context,
            use_deflection=None,  # Use default deflection chance
        )

        # Serialize graph changes for turn-by-turn evolution analysis (cu72.2)
        nodes_added_data = None
        edges_added_data = None
        extraction_summary_data = None
        if context_nodes_added is not None or context_edges_added is not None:
            nodes_added_data = [
                {"id": n["id"], "label": n["label"], "node_type": n["node_type"]}
                for n in (context_nodes_added or [])
            ]
            edges_added_data = [
                {
                    "source_node_id": e.get("source_node_id"),
                    "target_node_id": e.get("target_node_id"),
                    "edge_type": e.get("edge_type"),
                }
                for e in (context_edges_added or [])
            ]
            extraction_summary_data = {
                "nodes_added": len(nodes_added_data),
                "edges_added": len(edges_added_data),
            }

        return SimulationTurn(
            turn_number=turn_number,
            question=question,
            response=synthetic_response["response"],
            persona=persona_id,
            persona_name=synthetic_response["persona_name"],
            strategy_selected=strategy_selected,
            should_continue=should_continue,
            latency_ms=synthetic_response["latency_ms"],
            signals=signals,
            strategy_alternatives=strategy_alternatives,
            termination_reason=termination_reason,
            nodes_added=nodes_added_data,
            edges_added=edges_added_data,
            extraction_summary=extraction_summary_data,
            saturation_metrics=saturation_metrics,
            node_signals=node_signals,
        )

    async def _serialize_graph_data(
        self, session_id: str
    ) -> tuple[
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
    ]:
        """Fetch and serialize surface and canonical graph data for JSON output.

        Args:
            session_id: Session ID to fetch graph data for

        Returns:
            Tuple of (nodes_list, edges_list, canonical_slots_list, canonical_edges_list)
            as JSON-compatible dicts for simulation result export
        """
        # Fetch surface graph from graph repository
        nodes = await self.session.graph_repo.get_nodes_by_session(session_id)
        edges = await self.session.graph_repo.get_edges_by_session(session_id)

        # Serialize surface nodes to JSON-compatible format
        nodes_data = [
            {
                "id": n.id,
                "label": n.label,
                "node_type": n.node_type,
                "confidence": n.confidence,
                "properties": n.properties,
                "source_utterance_ids": n.source_utterance_ids,
                "stance": n.stance,
                "recorded_at": n.recorded_at.isoformat(),
                "superseded_by": n.superseded_by,
            }
            for n in nodes
        ]

        # Serialize surface edges to JSON-compatible format
        edges_data = [
            {
                "id": e.id,
                "source_node_id": e.source_node_id,
                "target_node_id": e.target_node_id,
                "edge_type": e.edge_type,
                "confidence": e.confidence,
                "properties": e.properties,
                "source_utterance_ids": e.source_utterance_ids,
                "recorded_at": e.recorded_at.isoformat(),
            }
            for e in edges
        ]

        # Fetch canonical graph if available
        canonical_slots_data = []
        canonical_edges_data = []

        if self.session.canonical_slot_repo is not None:
            # Fetch canonical slots with provenance (surface_node_ids)
            slots_with_provenance = (
                await self.session.canonical_slot_repo.get_slots_with_provenance(
                    session_id
                )
            )
            canonical_slots_data = slots_with_provenance  # Already in dict format

            # Fetch canonical edges with metadata
            edges_with_metadata = (
                await self.session.canonical_slot_repo.get_edges_with_metadata(
                    session_id
                )
            )
            canonical_edges_data = edges_with_metadata  # Already in dict format

            log.info(
                "canonical_graph_serialized",
                session_id=session_id,
                canonical_slots=len(canonical_slots_data),
                canonical_edges=len(canonical_edges_data),
            )
        else:
            log.info(
                "canonical_graph_skipped",
                session_id=session_id,
                reason="canonical_slot_repo is None (feature disabled)",
            )

        return nodes_data, edges_data, canonical_slots_data, canonical_edges_data

    def _count_nodes_by_type(self, nodes: list[dict[str, Any]]) -> dict[str, int]:
        """Count nodes by their type for summary statistics.

        Args:
            nodes: List of serialized node dictionaries

        Returns:
            Dictionary mapping node_type to count
        """
        counts: dict[str, int] = {}
        for node in nodes:
            node_type = node.get("node_type", "unknown")
            counts[node_type] = counts.get(node_type, 0) + 1
        return counts

    def _count_edges_by_type(self, edges: list[dict[str, Any]]) -> dict[str, int]:
        """Count edges by their type for summary statistics.

        Args:
            edges: List of serialized edge dictionaries

        Returns:
            Dictionary mapping edge_type to count
        """
        counts: dict[str, int] = {}
        for edge in edges:
            edge_type = edge.get("edge_type", "unknown")
            counts[edge_type] = counts.get(edge_type, 0) + 1
        return counts

    def _count_slots_by_type(self, slots: list[dict[str, Any]]) -> dict[str, int]:
        """Count canonical slots by their node_type for summary statistics.

        Args:
            slots: List of canonical slot dictionaries

        Returns:
            Dictionary mapping node_type to count
        """
        counts: dict[str, int] = {}
        for slot in slots:
            node_type = slot.get("node_type", "unknown")
            counts[node_type] = counts.get(node_type, 0) + 1
        return counts

    def _count_canonical_edges_by_type(
        self, edges: list[dict[str, Any]]
    ) -> dict[str, int]:
        """Count canonical edges by their edge_type for summary statistics.

        Args:
            edges: List of canonical edge dictionaries

        Returns:
            Dictionary mapping edge_type to count
        """
        counts: dict[str, int] = {}
        for edge in edges:
            edge_type = edge.get("edge_type", "unknown")
            counts[edge_type] = counts.get(edge_type, 0) + 1
        return counts

    async def _create_simulation_session(
        self,
        session_id: str,
        concept_id: str,
        concept_name: str,
        methodology: str,
        max_turns: int,
    ):
        """Create a session in the repository for simulation.

        Args:
            session_id: Session ID
            concept_id: Concept ID
            concept_name: Concept name
            methodology: Methodology ID
            max_turns: Maximum turns
        """
        now = datetime.now(timezone.utc)

        session = Session(
            id=session_id,
            methodology=methodology,
            concept_id=concept_id,
            concept_name=concept_name,
            created_at=now,
            updated_at=now,
            status="active",
            mode=InterviewMode.EXPLORATORY,
            state=SessionState(
                methodology=methodology,
                concept_id=concept_id,
                concept_name=concept_name,
                turn_count=0,
                mode=InterviewMode.EXPLORATORY,
            ),
        )

        config = {"max_turns": max_turns}
        await self.session.session_repo.create(session, config)

    async def _save_simulation_result(self, result: SimulationResult) -> Path:
        """Save simulation result to JSON file in synthetic_interviews/.

        Args:
            result: SimulationResult to save

        Returns:
            Path to saved file
        """
        # Create output directory if it doesn't exist
        SYNTHETIC_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Generate filename: {timestamp}_{concept_id}_{persona_id}.json
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{result.concept_id}_{result.persona_id}.json"
        filepath = SYNTHETIC_OUTPUT_DIR / filename

        # Convert dataclass to dict, handling nested dataclasses
        data = {
            "metadata": {
                "concept_id": result.concept_id,
                "concept_name": result.concept_name,
                "product_name": result.product_name,
                "objective": result.objective,
                "methodology": result.methodology,
                "persona_id": result.persona_id,
                "persona_name": result.persona_name,
                "session_id": result.session_id,
                "total_turns": result.total_turns,
                "status": result.status,
                "saved_at": datetime.now(timezone.utc).isoformat(),
            },
            # Surface graph section (kg_nodes, kg_edges)
            "graph": {
                "nodes": result.nodes,
                "edges": result.edges,
                "summary": {
                    "total_nodes": len(result.nodes),
                    "total_edges": len(result.edges),
                    "nodes_by_type": self._count_nodes_by_type(result.nodes),
                    "edges_by_type": self._count_edges_by_type(result.edges),
                },
            },
            # Canonical graph section (canonical_slots, canonical_edges)
            "canonical_graph": {
                "slots": result.canonical_slots,
                "edges": result.canonical_edges,
                "summary": {
                    "total_slots": len(result.canonical_slots),
                    "total_edges": len(result.canonical_edges),
                    "slots_by_type": self._count_slots_by_type(result.canonical_slots),
                    "edges_by_type": self._count_canonical_edges_by_type(
                        result.canonical_edges
                    ),
                },
            },
            "turns": [
                {
                    "turn_number": t.turn_number,
                    "question": t.question,
                    "response": t.response,
                    "persona": t.persona,
                    "persona_name": t.persona_name,
                    "strategy_selected": t.strategy_selected,
                    "should_continue": t.should_continue,
                    "latency_ms": t.latency_ms,
                    # Signal detection observability
                    "signals": t.signals,
                    "strategy_alternatives": t.strategy_alternatives,
                    "termination_reason": t.termination_reason,
                    # Graph evolution observability (cu72.2)
                    "nodes_added": t.nodes_added,
                    "edges_added": t.edges_added,
                    "extraction_summary": t.extraction_summary,
                    # Saturation tracking metrics (is_saturated, consecutive counters)
                    "saturation_metrics": t.saturation_metrics,
                    # Per-node signals from StrategySelectionStage
                    "node_signals": t.node_signals,
                }
                for t in result.turns
            ],
        }

        # Write to file
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        log.info(
            "simulation_result_saved",
            filepath=str(filepath),
            total_turns=result.total_turns,
        )

        return filepath


def get_simulation_service(
    session_repo: Optional[SessionRepository] = None,
    graph_repo: Optional[GraphRepository] = None,
) -> SimulationService:
    """Factory for simulation service with repository dependencies.

    Args:
        session_repo: Optional session repository (creates default if None)
        graph_repo: Optional graph repository (creates default if None)

    Returns:
        SimulationService instance

    Note:
        graph_repo must be provided since it requires an async database connection.
        Consider creating SimulationService directly with a SessionService instance.
    """
    if session_repo is None:
        from src.core.config import settings

        session_repo = SessionRepository(str(settings.database_path))

    if graph_repo is None:
        raise ValueError(
            "graph_repo must be provided to get_simulation_service. "
            "GraphRepository requires an async database connection. "
            "Consider using SimulationService directly with a SessionService instance."
        )

    # Create session service
    session_service = SessionService(
        session_repo=session_repo,
        graph_repo=graph_repo,
        extraction_llm_client=get_shared_extraction_client(),
        generation_llm_client=get_shared_generation_client(),
    )

    # Create synthetic service (will be created in SimulationService if None)
    return SimulationService(session_service=session_service)
