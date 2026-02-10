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
    """FastAPI dependency injection for SessionRepository.

    Provides a repository instance for session CRUD operations in API routes.
    Each request gets a new repository with database connection from settings.
    """
    return SessionRepository(str(settings.database_path))


def get_utterance_repository() -> UtteranceRepository:
    """FastAPI dependency injection for UtteranceRepository.

    Provides a repository instance for utterance CRUD operations in API routes.
    Each request gets a new repository with database connection from settings.
    """
    return UtteranceRepository(str(settings.database_path))


async def get_graph_repository(
    db: aiosqlite.Connection = Depends(get_db),
) -> GraphRepository:
    """FastAPI dependency injection for GraphRepository.

    Provides a repository instance for knowledge graph CRUD operations in API routes.
    Uses the shared database connection from get_db dependency.
    """
    return GraphRepository(db)


@lru_cache(maxsize=1)
def get_shared_extraction_client() -> LLMClient:
    """Cached LLM client for concept and relationship extraction.

    Shared across all extraction requests to avoid re-initializing the client.
    Uses LRU cache so the client is created once per process and reused.
    """
    return get_extraction_llm_client()


@lru_cache(maxsize=1)
def get_shared_generation_client() -> LLMClient:
    """Cached LLM client for question generation.

    Shared across all question generation requests to avoid re-initializing the client.
    Uses LRU cache so the client is created once per process and reused.
    """
    return get_generation_llm_client()


# Type aliases for dependency injection
SessionRepoDep = Annotated[SessionRepository, Depends(get_session_repository)]
UtteranceRepoDep = Annotated[UtteranceRepository, Depends(get_utterance_repository)]
GraphRepoDep = Annotated[GraphRepository, Depends(get_graph_repository)]
ExtractionClientDep = Annotated[LLMClient, Depends(get_shared_extraction_client)]
GenerationClientDep = Annotated[LLMClient, Depends(get_shared_generation_client)]
