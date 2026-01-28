"""Test MEC signal detection."""
import pytest
from src.methodologies.means_end_chain.signals import MECSignalDetector, MECSignalState


@pytest.mark.asyncio
async def test_mec_signal_state_creation():
    """Test that MECSignalState can be created with default values."""
    state = MECSignalState()
    assert state.missing_terminal_value is True
    assert state.ladder_depth == 0
    assert state.disconnected_nodes == 0
    assert state.edge_density == 0.0
    assert state.attributes_explored == 0
    assert state.consequences_explored == 0
    assert state.values_explored == 0
    assert state.coverage_breadth == 0.0
    assert state.new_concepts_mentioned is False
    assert state.response_depth == "surface"


@pytest.mark.asyncio
async def test_mec_signal_detector_instantiation():
    """Test that MECSignalDetector can be instantiated."""
    detector = MECSignalDetector()
    assert detector is not None


@pytest.mark.asyncio
async def test_mec_signal_detector_returns_state():
    """Test that MECSignalDetector.detect returns a MECSignalState."""
    from src.domain.models.knowledge_graph import GraphState, DepthMetrics, CoverageState
    from src.services.turn_pipeline.context import PipelineContext

    detector = MECSignalDetector()

    # Create minimal graph state with required fields
    depth_metrics = DepthMetrics(max_depth=0, avg_depth=0.0, depth_by_element={})
    coverage_state = CoverageState()
    graph_state = GraphState(
        node_count=0,
        edge_count=0,
        nodes_by_type={},
        edges_by_type={},
        orphan_count=0,
        depth_metrics=depth_metrics,
        coverage_state=coverage_state,
    )

    # Create minimal context (mock)
    context = PipelineContext(
        session_id="test",
        user_input="test input",
    )
    context.graph_state = graph_state

    result = await detector.detect(context, graph_state, "test response")

    assert isinstance(result, MECSignalState)
    assert result.missing_terminal_value is True  # Empty graph has no terminal values
    assert result.ladder_depth == 0  # Empty graph has no depth
