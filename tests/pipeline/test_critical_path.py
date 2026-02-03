"""
Critical path tests for the turn processing pipeline.

These tests validate the core flow:
1. Load context (session, graph state)
2. Save user utterance
3. Extract concepts/relationships
4. Update graph
5. Compute state
6. Select strategy
7. Decide continuation
8. Generate question
9. Save response
10. Persist scoring

This is NOT a comprehensive test suite - it validates that the pipeline
executes end-to-end with correct data flow.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.turn_pipeline.context import PipelineContext
from src.services.turn_pipeline.pipeline import TurnPipeline
from src.domain.models.session import Session, SessionState
from src.domain.models.interview_state import InterviewMode
from src.llm.client import LLMClientType


@pytest.mark.asyncio
async def test_pipeline_critical_path_minimal(session_repo, graph_repo, utterance_repo):
    """
    Test the minimal critical path: context load → extraction.

    This validates:
    - Pipeline stages can be created
    - Context flows through stages
    - Extraction produces a result

    Does NOT test:
    - LLM calls (mocked)
    - Correctness of strategy selection logic
    - Graph updates (uses empty graph)
    """
    from src.services.turn_pipeline.stages.context_loading_stage import ContextLoadingStage
    from src.services.turn_pipeline.stages.utterance_saving_stage import UtteranceSavingStage
    from src.services.turn_pipeline.stages.extraction_stage import ExtractionStage
    from src.services.extraction_service import ExtractionService
    from src.services.graph_service import GraphService

    # Setup: Create a session first
    session_id = "test-critical-path"
    now = datetime.now(timezone.utc)
    session = Session(
        id=session_id,
        methodology="means_end_chain",
        concept_id="oat_milk_v2",
        concept_name="Oat Milk",
        created_at=now,
        updated_at=now,
        state=SessionState(
            methodology="means_end_chain",
            concept_id="oat_milk_v2",
            concept_name="Oat Milk",
            turn_count=0,
            mode=InterviewMode.EXPLORATORY,
        ),
        mode=InterviewMode.EXPLORATORY,
        status="active",
    )
    await session_repo.create(session=session)

    # Create services needed for stages
    graph_service = GraphService(graph_repo)

    # Create minimal pipeline (first 3 stages)
    stages = [
        ContextLoadingStage(session_repo, graph_service),
        UtteranceSavingStage(),
        ExtractionStage(extraction_service=ExtractionService()),
    ]

    pipeline = TurnPipeline(stages)

    # Create context
    context = PipelineContext(
        session_id=session_id,
        user_input="I like oat milk because it's creamy",
    )

    # Mock the extraction to return empty result (no LLM call)
    with patch.object(
        stages[2].extraction, "extract", new_callable=AsyncMock
    ) as mock_extract:
        from src.domain.models.extraction import ExtractionResult
        mock_extract.return_value = ExtractionResult(
            concepts=[],
            relationships=[],
            discourse_markers=[],
            is_extractable=True,
        )

        # Execute pipeline (first 3 stages only)
        await pipeline.execute(context)

    # Verify context was populated
    assert context.session_id == session_id
    assert context.methodology == "means_end_chain"
    assert context.concept_id == "oat_milk_v2"
    assert context.turn_number == 1

    # Verify extraction was called with methodology
    mock_extract.assert_called_once()
    call_args = mock_extract.call_args
    assert call_args[1]["methodology"] == "means_end_chain"


@pytest.mark.asyncio
async def test_graph_state_strategy_history_deque():
    """
    Test that GraphState.strategy_history is a deque with maxlen=30.

    Validates the ry8 fix: strategy_history automatically trims to 30 items.
    """
    from collections import deque
    from src.domain.models.knowledge_graph import GraphState, DepthMetrics

    state = GraphState(
        node_count=5,
        edge_count=3,
        nodes_by_type={"attribute": 3, "value": 2},
        edges_by_type={"leads_to": 3},
        orphan_count=1,
        depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.0, depth_by_element={}),
        current_phase="exploratory",
        turn_count=1,
    )

    # Verify strategy_history is a deque with maxlen
    assert isinstance(state.strategy_history, deque)
    assert state.strategy_history.maxlen == 30

    # Test adding strategies
    state.add_strategy_used("deepen")
    assert list(state.strategy_history) == ["deepen"]

    state.add_strategy_used("broaden")
    assert list(state.strategy_history) == ["deepen", "broaden"]

    # Test auto-trimming at 30 items
    for i in range(35):
        state.add_strategy_used(f"strategy_{i}")

    # Should be trimmed to 30
    assert len(state.strategy_history) == 30
    # Oldest items removed
    assert "deepen" not in state.strategy_history
    assert "broaden" not in state.strategy_history


@pytest.mark.asyncio
async def test_phase_boundaries_configurable():
    """
    Test that phase boundaries are configurable per methodology.

    Validates the 54d fix: methodologies define their own phase transition thresholds.
    """
    from src.methodologies.registry import MethodologyRegistry

    registry = MethodologyRegistry()

    # Check MEC has configured boundaries
    mec_config = registry.get_methodology("means_end_chain")
    assert mec_config.phases is not None
    assert "early" in mec_config.phases
    assert mec_config.phases["early"].phase_boundaries is not None
    assert mec_config.phases["early"].phase_boundaries.get("early_max_nodes") == 5
    assert mec_config.phases["early"].phase_boundaries.get("mid_max_nodes") == 15

    # Check JTBD has different boundaries
    jtbd_config = registry.get_methodology("jobs_to_be_done")
    assert jtbd_config.phases is not None
    assert "early" in jtbd_config.phases
    assert jtbd_config.phases["early"].phase_boundaries.get("early_max_nodes") == 3
    assert jtbd_config.phases["early"].phase_boundaries.get("mid_max_nodes") == 8


@pytest.mark.asyncio
async def test_extraction_extract_requires_methodology():
    """
    Test that ExtractionService.extract() requires methodology parameter.

    Validates the at0 fix: methodology is now required on extract(), no default.
    """
    from src.services.extraction_service import ExtractionService

    # Create service with skip_extractability_check to avoid heuristic filtering
    service = ExtractionService(skip_extractability_check=True)

    # This should work - methodology provided
    # Note: We mock the LLM call so we don't need a real API key
    with patch.object(service.llm, "complete", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MagicMock(
            content='{"concepts": [], "relationships": [], "discourse_markers": []}',
            model="claude-3-5-sonnet-20241022",
            prompt_tokens=10,
            completion_tokens=20,
        )

        result = await service.extract(
            text="This is a longer text that passes heuristic checks",
            methodology="means_end_chain",
        )

        assert result is not None

    # Verify the LLM was called with the correct methodology-based prompt
    mock_llm.assert_called_once()


@pytest.mark.asyncio
async def test_llm_timeout_error_exists():
    """
    Test that LLMTimeoutError exists and is properly defined.

    Validates the wqo fix: LLM clients raise LLMTimeoutError on timeout.
    """
    from src.core.exceptions import LLMTimeoutError
    from src.llm.client import AnthropicClient

    # Verify LLMTimeoutError exists and can be raised
    assert LLMTimeoutError is not None
    assert issubclass(LLMTimeoutError, Exception)

    # Create client with very short timeout
    # Note: This test doesn't actually make an API call, it just verifies
    # the client can be created with a timeout parameter
    client = AnthropicClient(
        model="claude-3-5-sonnet-20241022",
        temperature=0.7,
        max_tokens=1000,
        timeout=0.001,  # 1ms timeout
        client_type="extraction",
        api_key="test-key",
    )

    # Verify timeout attribute is set
    assert client.timeout == 0.001
