"""Dependency injection for API routes."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
import aiosqlite

from src.core.config import settings
from src.persistence.repositories.session_repo import SessionRepository
from src.persistence.repositories.utterance_repo import UtteranceRepository
from src.persistence.database import get_db
from src.persistence.repositories.graph_repo import GraphRepository
from src.llm.client import LLMClient, get_extraction_llm_client, get_generation_llm_client


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


@lru_cache(maxsize=1)
def get_shared_extraction_client() -> LLMClient:
    """Get or create the shared extraction LLM client."""
    return get_extraction_llm_client()


@lru_cache(maxsize=1)
def get_shared_generation_client() -> LLMClient:
    """Get or create the shared generation LLM client."""
    return get_generation_llm_client()


# Type aliases for dependency injection
SessionRepoDep = Annotated[SessionRepository, Depends(get_session_repository)]
UtteranceRepoDep = Annotated[UtteranceRepository, Depends(get_utterance_repository)]
GraphRepoDep = Annotated[GraphRepository, Depends(get_graph_repository)]
ExtractionClientDep = Annotated[LLMClient, Depends(get_shared_extraction_client)]
GenerationClientDep = Annotated[LLMClient, Depends(get_shared_generation_client)]
