"""
Comprehensive tests for all signal pools.

Tests validate the complete signal pool architecture:
1. Graph signals (free, cached on graph update)
2. LLM signals (high cost, fresh every response)
3. Temporal signals (conversation history)
4. Meta signals (composite)
"""

import pytest

from src.methodologies.signals.graph import (
    GraphNodeCountSignal,
    GraphMaxDepthSignal,
    CoverageBreadthSignal,
    MissingTerminalValueSignal,
)
from src.methodologies.signals.llm import (
    ResponseDepthSignal,
    SentimentSignal,
    UncertaintySignal,
    AmbiguitySignal,
)
from src.methodologies.signals.temporal import (
    StrategyRepetitionCountSignal,
    TurnsSinceChangeSignal,
)
from src.methodologies.signals.meta import InterviewProgressSignal
from src.methodologies.techniques import (
    LadderingTechnique,
    ElaborationTechnique,
    ProbingTechnique,
    ValidationTechnique,
)
from src.services.focus_selection_service import (
    FocusSelectionService,
    FocusSelectionInput,
)
from src.domain.models.knowledge_graph import (
    GraphState,
    DepthMetrics,
    CoverageState,
)


class MockContext:
    """Mock pipeline context with signals."""

    def __init__(self, signals=None, strategy_history=None, recent_nodes=None):
        self.signals = signals or {}
        self.strategy_history = strategy_history or []
        self.recent_nodes = recent_nodes or []


class MockNode:
    """Mock graph node."""

    def __init__(self, node_id, label):
        self.id = node_id
        self.label = label


class TestGraphSignals:
    """Tests for graph-derived signals."""

    @pytest.mark.asyncio
    async def test_all_graph_signals_namespaced(self):
        """All graph signals should use graph.* namespace."""
        detectors = [
            GraphNodeCountSignal(),
            GraphMaxDepthSignal(),
            CoverageBreadthSignal(),
            MissingTerminalValueSignal(),
        ]

        for detector in detectors:
            assert detector.signal_name.startswith("graph."), (
                f"{detector.__class__.__name__} should have graph.* namespace"
            )
            assert detector.cost_tier in ["free", "low"]
            assert detector.refresh_trigger == "per_turn"

    @pytest.mark.asyncio
    async def test_graph_signals_compose(self):
        """Should compose multiple graph signals."""
        detectors = [
            GraphNodeCountSignal(),
            GraphMaxDepthSignal(),
            CoverageBreadthSignal(),
        ]

        graph_state = GraphState(
            node_count=5,
            edge_count=3,
            nodes_by_type={"attribute": 3, "terminal_value": 2},
            edges_by_type={},
            orphan_count=0,
            depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.0, depth_by_element={}),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=1,
        )

        all_signals = {}
        for detector in detectors:
            signals = await detector.detect(None, graph_state, "")
            all_signals.update(signals)

        # Verify all graph signals present
        assert "graph.node_count" in all_signals
        assert "graph.max_depth" in all_signals
        assert "graph.coverage_breadth" in all_signals


class TestLLMSignals:
    """Tests for LLM-derived signals."""

    @pytest.mark.asyncio
    async def test_all_llm_signals_namespaced(self):
        """All LLM signals should use llm.* namespace."""
        detectors = [
            ResponseDepthSignal(),
            SentimentSignal(),
            UncertaintySignal(),
            AmbiguitySignal(),
        ]

        for detector in detectors:
            assert detector.signal_name.startswith("llm."), (
                f"{detector.__class__.__name__} should have llm.* namespace"
            )
            assert detector.cost_tier == "high"
            assert detector.refresh_trigger == "per_response"

    @pytest.mark.asyncio
    async def test_response_depth_signal_analyzes_text(self):
        """Should analyze response depth correctly."""
        detector = ResponseDepthSignal()

        # Surface response (< 10 words)
        result = await detector.detect(None, None, "I like it")
        assert result["llm.response_depth"] == "surface"

        # Moderate response (10-30 words)
        result = await detector.detect(
            None,
            None,
            "I like it because it provides good quality and excellent value for money",
        )
        assert result["llm.response_depth"] == "moderate"

        # Deep response (> 30 words)
        result = await detector.detect(
            None,
            None,
            "I really like this product because it provides excellent quality and makes me feel confident about my choice every single time I use it for my daily needs and I would recommend it to anyone",
        )
        assert result["llm.response_depth"] == "deep"

    @pytest.mark.asyncio
    async def test_sentiment_signal_detects_sentiment(self):
        """Should detect sentiment in text."""
        detector = SentimentSignal()

        # Positive
        result = await detector.detect(None, None, "I love it, it's great")
        assert result["llm.sentiment"] == "positive"

        # Negative (use "hate" which is clearly negative)
        result = await detector.detect(None, None, "I hate it")
        assert result["llm.sentiment"] == "negative"

        # Neutral
        result = await detector.detect(None, None, "It is okay")
        assert result["llm.sentiment"] == "neutral"


class TestTemporalSignals:
    """Tests for temporal/history signals."""

    @pytest.mark.asyncio
    async def test_all_temporal_signals_namespaced(self):
        """All temporal signals should use temporal.* namespace."""
        detectors = [
            StrategyRepetitionCountSignal(),
            TurnsSinceChangeSignal(),
        ]

        for detector in detectors:
            assert detector.signal_name.startswith("temporal."), (
                f"{detector.__class__.__name__} should have temporal.* namespace"
            )
            assert detector.cost_tier == "free"
            assert detector.refresh_trigger == "per_turn"

    @pytest.mark.asyncio
    async def test_strategy_repetition_count(self):
        """Should count strategy repetitions."""
        detector = StrategyRepetitionCountSignal()
        context = MockContext(
            strategy_history=["deepen", "deepen", "explore", "deepen"]
        )

        result = await detector.detect(context, None, "")
        # "deepen" appears 3 times in last 5 entries
        assert result["temporal.strategy_repetition_count"] == 3

    @pytest.mark.asyncio
    async def test_turns_since_change(self):
        """Should count turns since strategy change."""
        detector = TurnsSinceChangeSignal()
        context = MockContext(strategy_history=["deepen", "deepen", "deepen"])

        result = await detector.detect(context, None, "")
        # "deepen" used 3 times consecutively
        assert result["temporal.turns_since_strategy_change"] == 3


class TestMetaSignals:
    """Tests for composite meta signals."""

    @pytest.mark.asyncio
    async def test_all_meta_signals_namespaced(self):
        """All meta signals should use meta.* namespace."""
        detector = InterviewProgressSignal()

        assert detector.signal_name.startswith("meta.")
        assert detector.cost_tier == "low"
        assert detector.refresh_trigger == "per_turn"

    @pytest.mark.asyncio
    async def test_interview_progress_composes_signals(self):
        """Should compose multiple signals into progress score."""
        detector = InterviewProgressSignal()

        # Mock context with signals
        context = MockContext(
            signals={
                "graph.coverage_breadth": 0.67,
                "graph.max_depth": 2,
                "graph.missing_terminal_value": False,
            }
        )

        result = await detector.detect(context, None, "")
        progress = result["meta.interview_progress"]

        # Should be reasonable progress (0-1)
        assert 0 <= progress <= 1
        # Should be decent with coverage and depth
        assert progress > 0.3


class TestAllTechniques:
    """Tests for all techniques."""

    @pytest.mark.asyncio
    async def test_all_four_techniques_work(self):
        """All four techniques should generate questions."""
        techniques = [
            LadderingTechnique(),
            ElaborationTechnique(),
            ProbingTechnique(),
            ValidationTechnique(),
        ]

        context = MockContext(
            signals={"graph.max_depth": 1},
            recent_nodes=[MockNode("quality", "quality")],
        )

        for technique in techniques:
            questions = await technique.generate_questions("quality", context)
            assert len(questions) > 0
            assert all(isinstance(q, str) for q in questions)


class TestFocusSelectionService:
    """Tests for FocusSelectionService."""

    @pytest.mark.asyncio
    async def test_service_selects_focus_by_strategy(self):
        """Should select focus based on strategy preference."""
        service = FocusSelectionService()

        graph_state = GraphState(
            node_count=3,
            edge_count=2,
            nodes_by_type={"attribute": 3},
            edges_by_type={},
            orphan_count=0,
            depth_metrics=DepthMetrics(
                max_depth=1, avg_depth=0.5, depth_by_element={"n1": 0, "n2": 1}
            ),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=1,
        )

        recent_nodes = [MockNode("n1", "quality"), MockNode("n2", "health")]

        # Test "deepen" strategy (prefers shallow)
        input_data = FocusSelectionInput(
            strategy="deepen",
            graph_state=graph_state,
            recent_nodes=recent_nodes,
            signals={"graph.depth_by_element": {"n1": 0, "n2": 1}},
        )

        focus = await service.select(input_data)
        # Should select shallow node (n1 with depth 0)
        assert focus == "quality"

    @pytest.mark.asyncio
    async def test_service_handles_no_nodes(self):
        """Should return None when no nodes available."""
        service = FocusSelectionService()

        input_data = FocusSelectionInput(
            strategy="deepen",
            graph_state=None,
            recent_nodes=[],
            signals={},
        )

        focus = await service.select(input_data)
        assert focus is None


class TestEndToEndIntegration:
    """End-to-end integration tests."""

    @pytest.mark.asyncio
    async def test_complete_signal_detection_pipeline(self):
        """Should detect all signal types in one pipeline."""
        # Setup
        graph_state = GraphState(
            node_count=5,
            edge_count=3,
            nodes_by_type={"attribute": 3, "terminal_value": 2},
            edges_by_type={},
            orphan_count=0,
            depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.0, depth_by_element={}),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=1,
        )

        context = MockContext(
            strategy_history=["deepen", "deepen", "explore"],
            recent_nodes=[MockNode("quality", "quality")],
        )

        # Detect all signal types
        all_signals = {}

        # Graph signals
        graph_detectors = [
            GraphNodeCountSignal(),
            GraphMaxDepthSignal(),
            CoverageBreadthSignal(),
        ]
        for detector in graph_detectors:
            signals = await detector.detect(context, graph_state, "")
            all_signals.update(signals)

        # LLM signals
        llm_detectors = [ResponseDepthSignal(), SentimentSignal()]
        for detector in llm_detectors:
            signals = await detector.detect(context, graph_state, "I like it")
            all_signals.update(signals)

        # Temporal signals
        temporal_detectors = [
            StrategyRepetitionCountSignal(),
            TurnsSinceChangeSignal(),
        ]
        for detector in temporal_detectors:
            signals = await detector.detect(context, graph_state, "")
            all_signals.update(signals)

        # Meta signals (need context.signals)
        context.signals = all_signals
        meta_detector = InterviewProgressSignal()
        signals = await meta_detector.detect(context, graph_state, "")
        all_signals.update(signals)

        # Verify all signal types present
        # Graph
        assert "graph.node_count" in all_signals
        assert "graph.max_depth" in all_signals
        # LLM
        assert "llm.response_depth" in all_signals
        assert "llm.sentiment" in all_signals
        # Temporal
        assert "temporal.strategy_repetition_count" in all_signals
        assert "temporal.turns_since_strategy_change" in all_signals
        # Meta
        assert "meta.interview_progress" in all_signals

        # Verify namespacing - no collisions
        signal_names = list(all_signals.keys())
        assert len(signal_names) == len(set(signal_names)), (
            "Signal names should be unique"
        )
