"""Tests for SessionService model warmup behavior."""

import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src.services.session_service import SessionService
from src.services.srl_service import SRLService
from src.services.embedding_service import EmbeddingService


@pytest.fixture
def mock_repos():
    """Create mock repositories for SessionService construction."""
    session_repo = MagicMock()
    session_repo.db_path = "/tmp/test.db"
    graph_repo = MagicMock()
    return session_repo, graph_repo


@pytest.fixture
def mock_llm_clients():
    """Create mock LLM clients."""
    extraction_client = MagicMock()
    generation_client = MagicMock()
    generation_client.generate = AsyncMock(return_value="What brings you here today?")
    return extraction_client, generation_client


class TestSRLServiceReference:
    """Test that SRLService is stored on SessionService for warmup access."""

    @patch("src.services.session_service.settings")
    def test_srl_service_stored_when_enabled(self, mock_settings, mock_repos, mock_llm_clients):
        """SRLService should be stored on self when enable_srl is True."""
        mock_settings.enable_srl = True
        mock_settings.enable_canonical_slots = True

        session_repo, graph_repo = mock_repos
        extraction_client, generation_client = mock_llm_clients

        service = SessionService(
            session_repo=session_repo,
            graph_repo=graph_repo,
            extraction_llm_client=extraction_client,
            generation_llm_client=generation_client,
        )

        assert hasattr(service, "_srl_service")
        assert isinstance(service._srl_service, SRLService)

    @patch("src.services.session_service.settings")
    def test_srl_service_none_when_disabled(self, mock_settings, mock_repos, mock_llm_clients):
        """_srl_service should be None when enable_srl is False."""
        mock_settings.enable_srl = False
        mock_settings.enable_canonical_slots = True

        session_repo, graph_repo = mock_repos
        extraction_client, generation_client = mock_llm_clients

        service = SessionService(
            session_repo=session_repo,
            graph_repo=graph_repo,
            extraction_llm_client=extraction_client,
            generation_llm_client=generation_client,
        )

        assert service._srl_service is None


class TestWarmupModels:
    """Test _warmup_models eagerly loads ML models."""

    @patch("src.services.session_service.settings")
    def test_warmup_skips_srl_when_disabled(self, mock_settings, mock_repos, mock_llm_clients):
        """Warmup should not touch SRLService.nlp when enable_srl is False."""
        mock_settings.enable_srl = False
        mock_settings.enable_canonical_slots = True

        session_repo, graph_repo = mock_repos
        extraction_client, generation_client = mock_llm_clients

        service = SessionService(
            session_repo=session_repo,
            graph_repo=graph_repo,
            extraction_llm_client=extraction_client,
            generation_llm_client=generation_client,
        )

        assert service._srl_service is None
        # Warmup should not raise despite no SRLService
        service._warmup_models()

    @patch("src.services.session_service.settings")
    def test_warmup_skips_when_graph_is_none(self, mock_settings, mock_repos, mock_llm_clients):
        """Warmup should handle graph being None gracefully."""
        mock_settings.enable_srl = False
        mock_settings.enable_canonical_slots = True

        session_repo, graph_repo = mock_repos
        extraction_client, generation_client = mock_llm_clients

        service = SessionService(
            session_repo=session_repo,
            graph_repo=graph_repo,
            extraction_llm_client=extraction_client,
            generation_llm_client=generation_client,
        )
        service.graph = None

        # Should not raise
        service._warmup_models()
