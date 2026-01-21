"""
Session API endpoints.

Provides CRUD operations for interview sessions.
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import structlog

from src.core.config import settings
from src.core.exceptions import SessionNotFoundError
from src.domain.models.session import Session, SessionState
from src.persistence.repositories.session_repo import SessionRepository

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


# =============================================================================
# Request/Response Models
# =============================================================================

class CreateSessionRequest(BaseModel):
    """Request body for creating a new session."""
    methodology: str = Field(..., description="Interview methodology (e.g., 'mec', 'zmet')")
    concept_id: str = Field(..., description="Concept identifier being explored")
    concept_name: str = Field(..., description="Human-readable concept name")


# =============================================================================
# Dependencies
# =============================================================================

def get_session_repository() -> SessionRepository:
    """Dependency that provides a SessionRepository instance."""
    return SessionRepository(str(settings.database_path))


SessionRepoDep = Annotated[SessionRepository, Depends(get_session_repository)]


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/", response_model=Session, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: CreateSessionRequest,
    session_repo: SessionRepoDep
) -> Session:
    """
    Create a new interview session.

    Args:
        request: Session creation parameters
        session_repo: Injected repository dependency

    Returns:
        The created session with generated ID and timestamps
    """
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    session = Session(
        id=session_id,
        methodology=request.methodology,
        concept_id=request.concept_id,
        concept_name=request.concept_name,
        created_at=now,
        updated_at=now,
        status="active",
        state=SessionState(
            methodology=request.methodology,
            concept_id=request.concept_id,
            concept_name=request.concept_name,
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

    return created_session


@router.get("/{session_id}", response_model=Session)
async def get_session(
    session_id: str,
    session_repo: SessionRepoDep
) -> Session:
    """
    Get a session by ID.

    Args:
        session_id: The session's unique identifier
        session_repo: Injected repository dependency

    Returns:
        The session if found

    Raises:
        HTTPException: 404 if session not found
    """
    session = await session_repo.get(session_id)

    if not session:
        log.warning("session_not_found", session_id=session_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    session_repo: SessionRepoDep
) -> None:
    """
    Delete a session by ID.

    Args:
        session_id: The session's unique identifier
        session_repo: Injected repository dependency

    Raises:
        HTTPException: 404 if session not found
    """
    deleted = await session_repo.delete(session_id)

    if not deleted:
        log.warning("session_delete_not_found", session_id=session_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    log.info("session_deleted", session_id=session_id)


@router.get("/", response_model=list[Session])
async def list_sessions(
    session_repo: SessionRepoDep
) -> list[Session]:
    """
    List all active sessions.

    Args:
        session_repo: Injected repository dependency

    Returns:
        List of active sessions, ordered by creation date (newest first)
    """
    sessions = await session_repo.list_active()
    log.debug("sessions_listed", count=len(sessions))
    return sessions
