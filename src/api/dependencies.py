"""Dependency injection for API routes."""

from typing import Annotated

from fastapi import Depends
import aiosqlite

from src.core.config import settings
from src.persistence.repositories.session_repo import SessionRepository
from src.persistence.repositories.utterance_repo import UtteranceRepository
from src.persistence.database import get_db
from src.persistence.repositories.graph_repo import GraphRepository


def get_session_repository() -> SessionRepository:
    """Dependency that provides a SessionRepository instance."""
    return SessionRepository(str(settings.database_path))


def get_utterance_repository() -> UtteranceRepository:
    """Dependency that provides an UtteranceRepository instance."""
    return UtteranceRepository(str(settings.database_path))


async def get_graph_repository(
    db: aiosqlite.Connection = Depends(get_db),
) -> GraphRepository:
    """Dependency that provides a GraphRepository instance."""
    return GraphRepository(db)


# Type aliases for dependency injection
SessionRepoDep = Annotated[SessionRepository, Depends(get_session_repository)]
UtteranceRepoDep = Annotated[UtteranceRepository, Depends(get_utterance_repository)]
GraphRepoDep = Annotated[GraphRepository, Depends(get_graph_repository)]
