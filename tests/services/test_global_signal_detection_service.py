"""
Tests for GlobalSignalDetectionService.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.global_signal_detection_service import GlobalSignalDetectionService


@pytest.fixture
def global_signal_service():
    """Create a GlobalSignalDetectionService instance."""
    return GlobalSignalDetectionService()


@pytest.fixture
def mock_context():
    """Create a mock PipelineContext."""
    context = MagicMock()
    context.methodology = "means_end_chain"
    context.node_tracker = MagicMock()
    return context


@pytest.fixture
def mock_graph_state():
    """Create a mock GraphState."""
    graph_state = MagicMock()
    graph_state.node_count = 5
    graph_state.edge_count = 3
    return graph_state


@pytest.mark.asyncio
async def test_global_signal_service_instantiation(global_signal_service):
    """Test that GlobalSignalDetectionService can be instantiated."""
    assert global_signal_service is not None
    assert global_signal_service.methodology_registry is not None
    # Trend signal is lazy-loaded; verify the getter returns a non-None instance
    assert global_signal_service._get_global_trend_signal() is not None


@pytest.mark.asyncio
async def test_detect_returns_dict_with_expected_keys(
    global_signal_service, mock_context, mock_graph_state
):
    """Test that detect() returns a dict with expected signal keys."""
    # Mock the signal detector
    with patch.object(
        global_signal_service.methodology_registry,
        "get_methodology",
    ) as mock_get_methodology:
        mock_config = MagicMock()
        mock_get_methodology.return_value = mock_config

        with patch.object(
            global_signal_service.methodology_registry,
            "create_signal_detector",
        ) as mock_create_detector:
            mock_detector = AsyncMock()
            mock_detector.detect.return_value = {
                "llm.response_depth": "deep",
                "graph.node_count": 5,
            }
            mock_create_detector.return_value = mock_detector

            # Force lazy init then patch the trend signal detect method
            global_signal_service._get_global_trend_signal()
            with patch.object(
                global_signal_service._global_trend_signal,
                "detect",
                new_callable=AsyncMock,
            ) as mock_trend_detect:
                mock_trend_detect.return_value = {"llm.global_response_trend": "stable"}

                # Call detect
                result = await global_signal_service.detect(
                    methodology_name="means_end_chain",
                    context=mock_context,
                    graph_state=mock_graph_state,
                    response_text="This is a detailed response",
                )

                # Verify result structure
                assert isinstance(result, dict)
                assert "llm.response_depth" in result
                assert "llm.global_response_trend" in result
                assert result["llm.response_depth"] == "deep"
                assert result["llm.global_response_trend"] == "stable"


@pytest.mark.asyncio
async def test_detect_raises_for_unknown_methodology(
    global_signal_service, mock_context, mock_graph_state
):
    """Test that detect() raises ConfigurationError for unknown methodology."""
    with patch.object(
        global_signal_service.methodology_registry,
        "get_methodology",
        return_value=None,
    ):
        with patch.object(
            global_signal_service.methodology_registry,
            "list_methodologies",
            return_value=["means_end_chain"],
        ):
            from src.core.exceptions import ConfigurationError

            with pytest.raises(ConfigurationError, match="not found in registry"):
                await global_signal_service.detect(
                    methodology_name="unknown_methodology",
                    context=mock_context,
                    graph_state=mock_graph_state,
                    response_text="test",
                )
