"""
Session API routes.

Endpoints for session management and turn processing.
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
import aiosqlite
import structlog

from src.api.schemas import (
    SessionCreate,
    SessionResponse,
    SessionListResponse,
    TurnRequest,
    TurnResponse,
    StartSessionResponse,
    ExtractionSchema,
    GraphStateSchema,
    ScoringSchema,
    ExtractedConceptSchema,
    ExtractedRelationshipSchema,
    NodeSchema,
    EdgeSchema,
    GraphResponse,
    SessionStatusResponse,
    ScoringCandidateSchema,
    ScoringTurnResponse,
)
from src.core.config import settings
from src.core.exceptions import SessionNotFoundError, SessionCompletedError
from src.domain.models.session import Session, SessionState
from src.persistence.database import get_db
from src.persistence.repositories.session_repo import SessionRepository
from src.persistence.repositories.graph_repo import GraphRepository
from src.services.session_service import SessionService
from src.services.export_service import ExportService
from src.services.scoring.two_tier import create_scoring_engine, TwoTierScoringEngine
from src.services.strategy_service import StrategyService

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


# ============ DEPENDENCY INJECTION ============


def get_session_repository() -> SessionRepository:
    """Dependency that provides a SessionRepository instance."""
    return SessionRepository(str(settings.database_path))


SessionRepoDep = Annotated[SessionRepository, Depends(get_session_repository)]


def get_scoring_engine() -> TwoTierScoringEngine:
    """
    Dependency that provides a TwoTierScoringEngine instance.

    Loads configuration from config/scoring.yaml and initializes
    all Tier 2 scorers with their weights.
    """
    # Create engine from YAML config
    engine = create_scoring_engine()
    log.info("scoring_engine_created", engine=str(engine))
    return engine


ScoringEngineDep = Annotated[TwoTierScoringEngine, Depends(get_scoring_engine)]


def get_strategy_service(
    scoring_engine: ScoringEngineDep,
) -> StrategyService:
    """
    Dependency that provides a StrategyService instance.

    Uses the TwoTierScoringEngine for strategy selection.
    """
    from src.services.scoring.llm_signals import QualitativeSignalExtractor

    # Create signal extractor for enhanced scoring
    signal_extractor = QualitativeSignalExtractor()

    service = StrategyService(
        scoring_engine=scoring_engine,
        config={},  # Use default config
        signal_extractor=signal_extractor,
    )
    log.info("strategy_service_created")
    return service


StrategyServiceDep = Annotated[StrategyService, Depends(get_strategy_service)]


async def get_graph_repository(
    db: aiosqlite.Connection = Depends(get_db),
) -> GraphRepository:
    """Dependency that provides a GraphRepository instance."""
    return GraphRepository(db)


GraphRepoDep = Annotated[GraphRepository, Depends(get_graph_repository)]


async def get_session_service(
    db: aiosqlite.Connection = Depends(get_db),
    strategy_service: StrategyService = Depends(get_strategy_service),
) -> SessionService:
    """
    Create SessionService with dependencies.

    Injected into route handlers.
    """
    session_repo = SessionRepository(str(settings.database_path))
    graph_repo = GraphRepository(db)

    return SessionService(
        session_repo=session_repo,
        graph_repo=graph_repo,
        strategy_service=strategy_service,  # Inject StrategyService
    )


# ============ SESSION CRUD (from Phase 1) ============


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    request: SessionCreate,
    session_repo: SessionRepoDep,
):
    """Create a new interview session."""
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Get concept_name and max_turns from config
    concept_name = request.config.get("concept_name", request.concept_id)
    max_turns = request.config.get("max_turns", 20)

    session = Session(
        id=session_id,
        methodology=request.methodology,
        concept_id=request.concept_id,
        concept_name=concept_name,
        created_at=now,
        updated_at=now,
        status="active",
        mode=request.mode,  # NEW: Pass mode from request
        state=SessionState(
            methodology=request.methodology,
            concept_id=request.concept_id,
            concept_name=concept_name,
            turn_count=0,
            coverage_score=0.0,
            mode=request.mode,  # NEW: Pass mode to state
        ),
    )

    # Create session with config
    created_session = await session_repo.create(session, request.config)

    log.info(
        "session_created",
        session_id=session_id,
        methodology=request.methodology,
        concept_id=request.concept_id,
        max_turns=max_turns,
    )

    return SessionResponse(
        id=created_session.id,
        methodology=created_session.methodology,
        concept_id=created_session.concept_id,
        status=created_session.status,
        config=request.config,
        turn_count=created_session.state.turn_count or 0,
        created_at=created_session.created_at,
        updated_at=created_session.updated_at,
        mode=created_session.mode,  # NEW: Include mode in response
    )


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    session_repo: SessionRepoDep,
):
    """List all sessions."""
    sessions = await session_repo.list_active()

    return SessionListResponse(
        sessions=[
            SessionResponse(
                id=s.id,
                methodology=s.methodology,
                concept_id=s.concept_id,
                status=s.status,
                config={},  # Config not stored in Session model
                turn_count=s.state.turn_count or 0,
                created_at=s.created_at,
                updated_at=s.updated_at,
                mode=s.mode,  # NEW: Include mode in response
            )
            for s in sessions
        ],
        total=len(sessions),
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    session_repo: SessionRepoDep,
):
    """Get session details by ID."""
    session = await session_repo.get(session_id)

    if not session:
        log.warning("session_not_found", session_id=session_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    return SessionResponse(
        id=session.id,
        methodology=session.methodology,
        concept_id=session.concept_id,
        status=session.status,
        config={},  # Config not stored in Session model
        turn_count=session.state.turn_count or 0,
        created_at=session.created_at,
        updated_at=session.updated_at,
        mode=session.mode,  # NEW: Include mode in response
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    session_repo: SessionRepoDep,
):
    """Delete/close a session."""
    deleted = await session_repo.delete(session_id)

    if not deleted:
        log.warning("session_delete_not_found", session_id=session_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    log.info("session_deleted", session_id=session_id)


@router.get("/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str,
    service: SessionService = Depends(get_session_service),
):
    """Get session status including current strategy."""
    try:
        status_data = await service.get_status(session_id)
        return SessionStatusResponse(**status_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{session_id}/graph", response_model=GraphResponse)
async def get_session_graph(
    session_id: str,
    graph_repo: GraphRepoDep,
):
    """Get session knowledge graph nodes and edges."""
    # Get nodes
    nodes = await graph_repo.get_nodes_by_session(session_id)

    # Get edges
    edges = await graph_repo.get_edges_by_session(session_id)

    return GraphResponse(
        nodes=[
            NodeSchema(
                id=node.id,
                label=node.label,
                node_type=node.node_type,
                confidence=node.confidence,
                properties=node.properties or {},
            )
            for node in nodes
        ],
        edges=[
            EdgeSchema(
                id=edge.id,
                source_id=edge.source_node_id,
                target_id=edge.target_node_id,
                edge_type=edge.edge_type,
                confidence=edge.confidence,
                properties=edge.properties or {},
            )
            for edge in edges
        ],
        node_count=len(nodes),
        edge_count=len(edges),
    )


@router.get("/{session_id}/scoring/{turn_number}", response_model=ScoringTurnResponse)
async def get_turn_scoring(
    session_id: str,
    turn_number: int,
    service: SessionService = Depends(get_session_service),
):
    """Get all scoring candidates for a specific turn.

    Returns all (strategy, focus) candidates that were considered,
    including their Tier 1 veto results, Tier 2 scores, and final ranking.
    """
    scoring_data = await service.get_turn_scoring(session_id, turn_number)

    # Convert candidates to schemas
    candidates = [ScoringCandidateSchema(**c) for c in scoring_data["candidates"]]

    return ScoringTurnResponse(
        session_id=scoring_data["session_id"],
        turn_number=scoring_data["turn_number"],
        candidates=candidates,
        winner_strategy_id=scoring_data["winner_strategy_id"],
    )


@router.get("/{session_id}/scoring", response_model=List[ScoringTurnResponse])
async def get_all_scoring(
    session_id: str,
    service: SessionService = Depends(get_session_service),
):
    """Get all scoring data for all turns in a session.

    Returns a list of turns with their candidates.
    """
    scoring_data_list = await service.get_all_scoring(session_id)

    results = []
    for scoring_data in scoring_data_list:
        candidates = [ScoringCandidateSchema(**c) for c in scoring_data["candidates"]]
        results.append(
            ScoringTurnResponse(
                session_id=scoring_data["session_id"],
                turn_number=scoring_data["turn_number"],
                candidates=candidates,
                winner_strategy_id=scoring_data["winner_strategy_id"],
            )
        )

    return results


# ============ TURN PROCESSING (Phase 2) ============


@router.post(
    "/{session_id}/start",
    response_model=StartSessionResponse,
)
async def start_session(
    session_id: str,
    service: SessionService = Depends(get_session_service),
):
    """
    Start an interview session and get the opening question.

    Must be called before process_turn.
    """
    log.info("starting_session", session_id=session_id)

    try:
        opening_question = await service.start_session(session_id)

        return StartSessionResponse(
            session_id=session_id,
            opening_question=opening_question,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        log.error("start_session_failed", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start session: {e}",
        )


@router.post(
    "/{session_id}/turns",
    response_model=TurnResponse,
)
async def process_turn(
    session_id: str,
    request: TurnRequest,
    service: SessionService = Depends(get_session_service),
):
    """
    Process a respondent turn.

    Takes user input text, extracts concepts, updates graph,
    and returns next question.
    """
    log.info(
        "processing_turn_request",
        session_id=session_id,
        text_length=len(request.text),
    )

    try:
        result = await service.process_turn(
            session_id=session_id,
            user_input=request.text,
        )

        # Convert to response schema
        return TurnResponse(
            turn_number=result.turn_number,
            extracted=ExtractionSchema(
                concepts=[
                    ExtractedConceptSchema(**c) for c in result.extracted["concepts"]
                ],
                relationships=[
                    ExtractedRelationshipSchema(**r)
                    for r in result.extracted["relationships"]
                ],
            ),
            graph_state=GraphStateSchema(
                node_count=result.graph_state["node_count"],
                edge_count=result.graph_state["edge_count"],
                depth_achieved=result.graph_state.get("depth_achieved", {}),
            ),
            scoring=ScoringSchema(
                coverage=result.scoring["coverage"],
                depth=result.scoring["depth"],
                saturation=result.scoring["saturation"],
            ),
            strategy_selected=result.strategy_selected,
            next_question=result.next_question,
            should_continue=result.should_continue,
            latency_ms=result.latency_ms,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except SessionCompletedError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session has already completed",
        )
    except Exception as e:
        log.error(
            "process_turn_failed",
            session_id=session_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Turn processing failed: {e}",
        )


# ============ EXPORT (Phase 6) ============


async def get_export_service(
    db: aiosqlite.Connection = Depends(get_db),
) -> ExportService:
    """
    Create ExportService with dependencies.

    Injected into route handlers.
    """
    graph_repo = GraphRepository(db)

    return ExportService(graph_repo=graph_repo)


@router.get(
    "/{session_id}/export",
    response_class=Response,
    summary="Export session data",
    description="Export session data to JSON, Markdown, or CSV format",
)
async def export_session(
    session_id: str,
    format: str = Query(
        "json",
        description="Export format: json, markdown, or csv",
        pattern="^(json|markdown|csv)$",
    ),
    service: ExportService = Depends(get_export_service),
) -> Response:
    """
    Export session data to specified format.

    Args:
        session_id: Session ID to export
        format: Export format (json, markdown, csv)
        service: Injected export service

    Returns:
        Response with exported data and appropriate content-type

    Raises:
        HTTPException 404: If session not found
        HTTPException 400: If format is invalid
    """
    log_ctx = log.bind(session_id=session_id, format=format)

    log_ctx.info("export_session_requested")

    try:
        data = await service.export_session(session_id, format)

        # Set content-type based on format
        if format == "json":
            content_type = "application/json"
            filename = f"session_{session_id[:8]}.json"
        elif format == "markdown":
            content_type = "text/markdown"
            filename = f"session_{session_id[:8]}.md"
        else:  # csv
            content_type = "text/csv"
            filename = f"session_{session_id[:8]}.csv"

        log_ctx.info(
            "export_session_complete",
            content_type=content_type,
            content_length=len(data),
        )

        return Response(
            content=data,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    except SessionNotFoundError as e:
        log_ctx.warning("export_session_not_found", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValueError as e:
        log_ctx.warning("export_session_invalid_format", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        log_ctx.error(
            "export_session_error",
            error_type=type(e).__name__,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}",
        )
