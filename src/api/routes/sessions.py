"""
Session API routes.

Endpoints for session management and turn processing.
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated

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
)
from src.core.config import settings
from src.core.exceptions import SessionNotFoundError, SessionCompletedError
from src.domain.models.session import Session, SessionState
from src.persistence.database import get_db
from src.persistence.repositories.session_repo import SessionRepository
from src.persistence.repositories.graph_repo import GraphRepository
from src.services.session_service import SessionService
from src.services.export_service import ExportService

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


# ============ DEPENDENCY INJECTION ============

def get_session_repository() -> SessionRepository:
    """Dependency that provides a SessionRepository instance."""
    return SessionRepository(str(settings.database_path))


SessionRepoDep = Annotated[SessionRepository, Depends(get_session_repository)]


async def get_session_service(
    db: aiosqlite.Connection = Depends(get_db),
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

    # Get concept_name from config
    concept_name = request.config.get("concept_name", request.concept_id)

    session = Session(
        id=session_id,
        methodology=request.methodology,
        concept_id=request.concept_id,
        concept_name=concept_name,
        created_at=now,
        updated_at=now,
        status="active",
        state=SessionState(
            methodology=request.methodology,
            concept_id=request.concept_id,
            concept_name=concept_name,
            turn_count=0,
            coverage_score=0.0
        )
    )

    created_session = await session_repo.create(session)

    log.info(
        "session_created",
        session_id=session_id,
        methodology=request.methodology,
        concept_id=request.concept_id
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
            detail=f"Session {session_id} not found"
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
            detail=f"Session {session_id} not found"
        )

    log.info("session_deleted", session_id=session_id)


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
                    ExtractedRelationshipSchema(**r) for r in result.extracted["relationships"]
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
    except SessionCompletedError as e:
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
