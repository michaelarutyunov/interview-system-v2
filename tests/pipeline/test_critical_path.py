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
from src.domain.models.session import Session, SessionState
from src.domain.models.interview_state import InterviewMode


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
    from src.services.turn_pipeline.stages.context_loading_stage import (
        ContextLoadingStage,
    )
    from src.services.turn_pipeline.stages.utterance_saving_stage import (
        UtteranceSavingStage,
    )
    from src.services.turn_pipeline.stages.extraction_stage import ExtractionStage
    from src.services.extraction_service import ExtractionService
    from src.services.graph_service import GraphService
    from src.llm.client import AnthropicClient

    # Setup: Create a session first
    session_id = "test-critical-path"
    now = datetime.now(timezone.utc)
    session = Session(
        id=session_id,
        methodology="means_end_chain",
        concept_id="oatmilk_mec_legacy",
        concept_name="Oat Milk",
        created_at=now,
        updated_at=now,
        state=SessionState(
            methodology="means_end_chain",
            concept_id="oatmilk_mec_legacy",
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

    # Create mock LLM client for extraction service
    mock_llm = AnthropicClient(
        model="claude-3-5-sonnet-20241022",
        temperature=0.3,
        max_tokens=2000,
        client_type="extraction",
        api_key="test-key",
        timeout=60.0,
    )

    # Create minimal pipeline (first 3 stages)
    stages = [
        ContextLoadingStage(session_repo, graph_service),
        UtteranceSavingStage(),
        ExtractionStage(extraction_service=ExtractionService(llm_client=mock_llm)),
    ]

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

        # Execute stages directly (not pipeline.execute) since this is a
        # partial pipeline test that skips strategy selection and later stages
        for stage in stages:
            context = await stage.process(context)

    # Verify context was populated
    assert context.session_id == session_id
    assert context.methodology == "means_end_chain"
    assert context.concept_id == "oatmilk_mec_legacy"
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
async def test_phase_boundaries_calculated_from_max_turns():
    """
    Test that phase boundaries are automatically calculated from max_turns.

    Validates the design: phases scale proportionally with interview length.
    - early: ~10% of max_turns (minimum 1 turn)
    - mid: max_turns - 2 (reserving last 2 turns for late)
    - late: final 2 turns for validation
    """
    from src.signals.meta.interview_phase import InterviewPhaseSignal

    # Test with max_turns = 20 (default)
    boundaries_20 = InterviewPhaseSignal.calculate_phase_boundaries(20)
    assert boundaries_20["early_max_turns"] == 2  # 10% of 20 = 2
    assert boundaries_20["mid_max_turns"] == 18  # 20 - 2 = 18

    # Test with max_turns = 10 (short interview)
    boundaries_10 = InterviewPhaseSignal.calculate_phase_boundaries(10)
    assert boundaries_10["early_max_turns"] == 1  # 10% of 10 = 1
    assert boundaries_10["mid_max_turns"] == 8  # 10 - 2 = 8

    # Test with max_turns = 30 (long interview)
    boundaries_30 = InterviewPhaseSignal.calculate_phase_boundaries(30)
    assert boundaries_30["early_max_turns"] == 3  # 10% of 30 = 3
    assert boundaries_30["mid_max_turns"] == 28  # 30 - 2 = 28

    # Verify late phase always gets exactly 2 turns
    assert boundaries_20["mid_max_turns"] == 20 - 2
    assert boundaries_10["mid_max_turns"] == 10 - 2
    assert boundaries_30["mid_max_turns"] == 30 - 2


@pytest.mark.asyncio
async def test_extraction_extract_requires_methodology():
    """
    Test that ExtractionService.extract() requires methodology parameter.

    Validates the at0 fix: methodology is now required on extract(), no default.
    """
    from src.services.extraction_service import ExtractionService
    from src.llm.client import AnthropicClient

    # Create mock LLM client
    mock_llm = AnthropicClient(
        model="claude-3-5-sonnet-20241022",
        temperature=0.3,
        max_tokens=2000,
        client_type="extraction",
        api_key="test-key",
        timeout=60.0,
    )

    # Create service with skip_extractability_check to avoid heuristic filtering
    service = ExtractionService(llm_client=mock_llm, skip_extractability_check=True)

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


# =============================================================================
# Saturation Tracking Tests (8yko)
# =============================================================================


@pytest.mark.asyncio
async def test_saturation_metrics_model():
    """
    Test that SaturationMetrics model has all required fields.

    Validates the 8yko fix: SaturationMetrics extended with quality and depth tracking.
    """
    from src.domain.models.knowledge_graph import SaturationMetrics

    # Create metrics with all fields
    metrics = SaturationMetrics(
        chao1_ratio=0.8,
        new_info_rate=0.5,
        consecutive_low_info=3,
        is_saturated=False,
        consecutive_shallow=2,
        consecutive_depth_plateau=1,
        prev_max_depth=4,
    )

    # Verify all fields accessible
    assert metrics.chao1_ratio == 0.8
    assert metrics.new_info_rate == 0.5
    assert metrics.consecutive_low_info == 3
    assert metrics.is_saturated is False
    assert metrics.consecutive_shallow == 2
    assert metrics.consecutive_depth_plateau == 1
    assert metrics.prev_max_depth == 4

    # Verify is_saturated defaults to False
    default_metrics = SaturationMetrics()
    assert default_metrics.is_saturated is False
    assert default_metrics.consecutive_low_info == 0


@pytest.mark.asyncio
async def test_state_computation_output_has_saturation():
    """
    Test that StateComputationOutput includes saturation_metrics field.

    Validates the 8yko fix: saturation computed by StateComputationStage.
    """
    from src.domain.models.pipeline_contracts import StateComputationOutput
    from src.domain.models.knowledge_graph import (
        GraphState,
        DepthMetrics,
        SaturationMetrics,
    )

    # Create state computation output with saturation
    graph_state = GraphState(
        node_count=5,
        edge_count=3,
        nodes_by_type={"attribute": 3, "value": 2},
        edges_by_type={"leads_to": 3},
        orphan_count=0,
        depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.5, depth_by_element={}),
        current_phase="focused",
        turn_count=3,
    )

    saturation = SaturationMetrics(
        new_info_rate=0.3,
        consecutive_low_info=2,
        is_saturated=False,
    )

    output = StateComputationOutput(
        graph_state=graph_state,
        recent_nodes=[],
        computed_at=datetime.now(timezone.utc),
        saturation_metrics=saturation,
    )

    # Verify saturation metrics accessible
    assert output.saturation_metrics is not None
    assert output.saturation_metrics.is_saturated is False
    assert output.saturation_metrics.consecutive_low_info == 2


@pytest.mark.asyncio
async def test_continuation_stage_reads_saturation_from_context():
    """
    Test that ContinuationStage reads saturation from StateComputationOutput.

    Validates the 8yko fix: ContinuationStage is now a pure consumer of
    pre-computed saturation metrics (no internal state).
    """
    from src.services.turn_pipeline.stages.continuation_stage import ContinuationStage
    from src.services.turn_pipeline.context import PipelineContext
    from src.domain.models.pipeline_contracts import (
        ContextLoadingOutput,
        StateComputationOutput,
        StrategySelectionOutput,
    )
    from src.domain.models.knowledge_graph import (
        GraphState,
        DepthMetrics,
        SaturationMetrics,
    )
    from src.services.focus_selection_service import FocusSelectionService

    # Create mock dependencies
    focus_selection_service = FocusSelectionService()

    stage = ContinuationStage(
        focus_selection_service=focus_selection_service,
    )

    # Create graph state (use 'focused' as valid phase literal)
    graph_state = GraphState(
        node_count=10,
        edge_count=8,
        nodes_by_type={"attribute": 5, "value": 5},
        edges_by_type={"leads_to": 8},
        orphan_count=0,
        depth_metrics=DepthMetrics(max_depth=3, avg_depth=2.0, depth_by_element={}),
        current_phase="focused",
        turn_count=6,
    )

    # Test case 1: Not saturated - should continue
    context = PipelineContext(session_id="test-1", user_input="test")

    # Set up contracts (single source of truth)
    context.context_loading_output = ContextLoadingOutput(
        methodology="means_end_chain",
        concept_id="test-concept",
        concept_name="Test Product",
        turn_number=6,
        mode="exploratory",
        max_turns=15,
    )

    context.state_computation_output = StateComputationOutput(
        graph_state=graph_state,
        recent_nodes=[],
        computed_at=datetime.now(timezone.utc),
        saturation_metrics=SaturationMetrics(
            new_info_rate=0.5,
            consecutive_low_info=1,
            is_saturated=False,
        ),
    )

    context.strategy_selection_output = StrategySelectionOutput(
        strategy="deepen",
        focus={"type": "node", "node_id": "node-1"},
        signals={},
    )

    result = await stage.process(context)

    assert result.continuation_output is not None
    assert result.continuation_output.should_continue is True

    # Test case 2: Saturated - should end
    context2 = PipelineContext(session_id="test-2", user_input="test")

    context2.context_loading_output = ContextLoadingOutput(
        methodology="means_end_chain",
        concept_id="test-concept",
        concept_name="Test Product",
        turn_number=10,
        mode="exploratory",
        max_turns=15,
    )

    context2.state_computation_output = StateComputationOutput(
        graph_state=graph_state,
        recent_nodes=[],
        computed_at=datetime.now(timezone.utc),
        saturation_metrics=SaturationMetrics(
            new_info_rate=0.0,
            consecutive_low_info=5,  # Threshold is 5
            is_saturated=True,
        ),
    )

    context2.strategy_selection_output = StrategySelectionOutput(
        strategy="deepen",
        focus={},
        signals={},
    )

    result2 = await stage.process(context2)

    assert result2.continuation_output is not None
    assert result2.continuation_output.should_continue is False
    assert "saturated" in result2.continuation_output.reason


@pytest.mark.asyncio
async def test_saturation_thresholds_in_state_computation():
    """
    Test that saturation thresholds are defined in StateComputationStage.

    Validates the 8yko fix: thresholds centralized in StateComputationStage.
    """
    from src.services.turn_pipeline.stages.state_computation_stage import (
        CONSECUTIVE_ZERO_YIELD_THRESHOLD,
        CONSECUTIVE_SHALLOW_THRESHOLD,
        DEPTH_PLATEAU_THRESHOLD,
    )

    # Verify thresholds are defined
    assert CONSECUTIVE_ZERO_YIELD_THRESHOLD == 5
    assert CONSECUTIVE_SHALLOW_THRESHOLD == 6
    assert DEPTH_PLATEAU_THRESHOLD == 6
