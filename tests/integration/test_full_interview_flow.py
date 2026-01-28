"""Integration tests for full interview flow with methodology-centric architecture.

These tests verify end-to-end functionality of the new methodology-based
strategy selection system.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.methodologies import get_methodology
from src.services.turn_pipeline.pipeline import TurnPipeline
from src.services.turn_pipeline.context import PipelineContext
from src.domain.models.knowledge_graph import GraphState, DepthMetrics, CoverageState
from src.domain.models.extraction import ExtractionResult, ExtractedConcept
from src.domain.models.turn import Focus


class TestMECInterviewFlow:
    """Integration tests for Means-End Chain interview flow."""

    @pytest.mark.asyncio
    async def test_mec_strategy_selection_with_signals(self):
        """Test that MEC methodology detects signals and selects strategies."""
        # Get MEC methodology
        methodology = get_methodology("means_end_chain")
        assert methodology is not None
        assert methodology.name == "means_end_chain"

        # Verify signal detector exists
        signal_detector = methodology.get_signal_detector()
        assert signal_detector is not None

        # Verify strategies are registered
        strategies = methodology.get_strategies()
        assert len(strategies) == 4  # ladder_deeper, clarify_relationship, explore_new_attribute, reflect_and_validate
        strategy_names = [s.name for s in strategies]
        assert "ladder_deeper" in strategy_names
        assert "clarify_relationship" in strategy_names
        assert "explore_new_attribute" in strategy_names
        assert "reflect_and_validate" in strategy_names

    @pytest.mark.asyncio
    async def test_mec_signal_detection(self):
        """Test MEC signal detection produces expected signals."""
        methodology = get_methodology("means_end_chain")
        signal_detector = methodology.get_signal_detector()

        # Create proper context with graph_state
        from src.services.turn_pipeline.context import PipelineContext

        context = PipelineContext(
            session_id="test",
            user_input="I like oat milk",
            turn_number=1,
        )

        graph_state = GraphState(
            node_count=5,
            edge_count=3,
            depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.0),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=1,
        )
        context.graph_state = graph_state

        # Detect signals
        signals = await signal_detector.detect(
            context=context,
            graph_state=graph_state,
            response_text="I like oat milk because it's creamy",
        )

        # Verify common signals (access via model_dump for Pydantic models)
        signal_dict = signals.model_dump()
        assert "strategy_repetition_count" in signal_dict
        assert "turns_since_strategy_change" in signal_dict
        assert "response_confidence" in signal_dict

        # Verify MEC-specific signals
        assert "missing_terminal_value" in signal_dict
        assert "ladder_depth" in signal_dict
        assert "disconnected_nodes" in signal_dict
        assert "edge_density" in signal_dict
        assert "coverage_breadth" in signal_dict

    @pytest.mark.asyncio
    async def test_mec_strategy_scoring(self):
        """Test MEC strategies can be scored based on signals."""
        from src.methodologies import get_methodology
        from src.methodologies.scoring import score_strategy

        methodology = get_methodology("means_end_chain")
        strategies = methodology.get_strategies()

        # Test each strategy has score_signals method
        for strategy_class in strategies:
            weights = strategy_class.score_signals()
            assert isinstance(weights, dict)
            assert len(weights) > 0

            # Verify weights are numeric
            for signal_name, weight in weights.items():
                assert isinstance(signal_name, str)
                assert isinstance(weight, (int, float))

    @pytest.mark.asyncio
    async def test_mec_strategy_ranking(self):
        """Test MEC strategies can be ranked by score."""
        from src.methodologies import get_methodology
        from src.methodologies.scoring import rank_strategies
        from src.methodologies.base import SignalState

        methodology = get_methodology("means_end_chain")
        strategies = methodology.get_strategies()

        # Create test signals
        signals = SignalState(
            missing_terminal_value=True,
            ladder_depth=2,
            disconnected_nodes=0,
            edge_density=0.6,
            coverage_breadth=0.3,
        )

        # Rank strategies
        ranked = rank_strategies(strategies, signals)

        # Verify ranking
        assert len(ranked) == len(strategies)
        assert all(isinstance(score, (int, float)) for _, score in ranked)

        # Verify descending order
        for i in range(len(ranked) - 1):
            assert ranked[i][1] >= ranked[i + 1][1]


class TestJTBDInterviewFlow:
    """Integration tests for Jobs-to-be-Done interview flow."""

    @pytest.mark.asyncio
    async def test_jtbd_strategy_selection_with_signals(self):
        """Test that JTBD methodology detects signals and selects strategies."""
        # Get JTBD methodology
        methodology = get_methodology("jobs_to_be_done")
        assert methodology is not None
        assert methodology.name == "jobs_to_be_done"

        # Verify signal detector exists
        signal_detector = methodology.get_signal_detector()
        assert signal_detector is not None

        # Verify strategies are registered
        strategies = methodology.get_strategies()
        assert len(strategies) == 6  # explore_situation, probe_alternatives, dig_motivation, uncover_obstacles, validate_outcome, balance_coverage
        strategy_names = [s.name for s in strategies]
        assert "explore_situation" in strategy_names
        assert "probe_alternatives" in strategy_names
        assert "dig_motivation" in strategy_names
        assert "uncover_obstacles" in strategy_names
        assert "validate_outcome" in strategy_names
        assert "balance_coverage" in strategy_names

    @pytest.mark.asyncio
    async def test_jtbd_signal_detection(self):
        """Test JTBD signal detection produces expected signals."""
        methodology = get_methodology("jobs_to_be_done")
        signal_detector = methodology.get_signal_detector()

        # Create proper context
        from src.services.turn_pipeline.context import PipelineContext

        context = PipelineContext(
            session_id="test",
            user_input="I needed breakfast",
            turn_number=1,
        )

        graph_state = GraphState(
            node_count=5,
            edge_count=3,
            depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.0),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=1,
        )
        context.graph_state = graph_state

        # Detect signals
        signals = await signal_detector.detect(
            context=context,
            graph_state=graph_state,
            response_text="I needed a quick breakfast before work",
        )

        # Verify common signals
        signal_dict = signals.model_dump()
        assert "strategy_repetition_count" in signal_dict
        assert "turns_since_strategy_change" in signal_dict

        # Verify JTBD-specific signals
        assert "job_identified" in signal_dict
        assert "situation_depth" in signal_dict
        assert "motivation_depth" in signal_dict
        assert "alternatives_explored" in signal_dict
        assert "obstacles_explored" in signal_dict
        assert "outcome_clarity" in signal_dict


class TestMethodologyServiceIntegration:
    """Integration tests for MethodologyStrategyService."""

    @pytest.mark.asyncio
    async def test_mec_methodology_service_strategy_selection(self):
        """Test end-to-end strategy selection for MEC methodology."""
        from src.services.methodology_strategy_service import MethodologyStrategyService
        from src.services.turn_pipeline.context import PipelineContext

        service = MethodologyStrategyService()

        # Create proper context
        context = PipelineContext(
            session_id="test-session",
            user_input="I like oat milk",
            turn_number=1,
        )

        graph_state = GraphState(
            node_count=5,
            edge_count=3,
            depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.0),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=1,
        )
        context.graph_state = graph_state
        context.methodology = MagicMock()
        context.methodology.name = "means_end_chain"

        # Select strategy
        strategy, focus, alternatives, signals = await service.select_strategy(
            context=context,
            graph_state=graph_state,
            response_text="I like oat milk",
        )

        # Verify results
        assert strategy is not None
        assert isinstance(strategy, str)
        assert signals is not None
        assert isinstance(signals, dict)
        assert alternatives is not None
        assert len(alternatives) > 0

        # Verify alternatives are tuples of (strategy_name, score)
        for alt in alternatives:
            assert isinstance(alt, tuple)
            assert len(alt) == 2
            assert isinstance(alt[0], str)
            assert isinstance(alt[1], (int, float))

    @pytest.mark.asyncio
    async def test_jtbd_methodology_service_strategy_selection(self):
        """Test end-to-end strategy selection for JTBD methodology."""
        from src.services.methodology_strategy_service import MethodologyStrategyService
        from src.services.turn_pipeline.context import PipelineContext

        service = MethodologyStrategyService()

        # Create proper context
        context = PipelineContext(
            session_id="test-session",
            user_input="I needed breakfast",
            turn_number=1,
        )

        graph_state = GraphState(
            node_count=5,
            edge_count=3,
            depth_metrics=DepthMetrics(max_depth=2, avg_depth=1.0),
            coverage_state=CoverageState(),
            current_phase="exploratory",
            turn_count=1,
        )
        context.graph_state = graph_state
        context.methodology = MagicMock()
        context.methodology.name = "jobs_to_be_done"

        # Select strategy
        strategy, focus, alternatives, signals = await service.select_strategy(
            context=context,
            graph_state=graph_state,
            response_text="I needed a quick breakfast",
        )

        # Verify results
        assert strategy is not None
        assert signals is not None
        assert alternatives is not None
        assert len(alternatives) > 0
