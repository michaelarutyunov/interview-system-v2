"""Tests for two-stage strategy selection in MethodologyStrategyService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.methodologies.registry import StrategyConfig, MethodologyConfig
from src.services.methodology_strategy_service import MethodologyStrategyService


def _make_context(methodology="means_end_chain", turn_number=5, max_turns=20):
    ctx = MagicMock()
    ctx.methodology = methodology
    ctx.turn_number = turn_number
    ctx.max_turns = max_turns
    ctx.user_input = "I like oat milk because it's creamy"
    ctx.signals = {}
    ctx.node_tracker = MagicMock()
    ctx.node_tracker.previous_focus = None
    ctx.recent_utterances = []
    return ctx


def _make_graph_state():
    gs = MagicMock()
    gs.node_count = 5
    gs.edge_count = 3
    return gs


@pytest.mark.asyncio
class TestTwoStageSelection:
    async def test_node_binding_none_skips_node_selection(self):
        """Strategy with node_binding='none' returns focus_node_id=None."""
        reflect = StrategyConfig(
            name="reflect",
            description="Reflect",
            signal_weights={"meta.interview_progress": 0.5},
            node_binding="none",
        )
        config = MethodologyConfig(
            name="test",
            description="Test",
            signals={},
            strategies=[reflect],
            phases=None,
        )

        service = MethodologyStrategyService()
        service.methodology_registry = MagicMock()
        service.methodology_registry.get_methodology.return_value = config

        service.global_signal_service = AsyncMock()
        service.global_signal_service.detect.return_value = {
            "meta.interview_progress": 0.9
        }
        service.node_signal_service = AsyncMock()
        service.node_signal_service.detect.return_value = {
            "node_1": {"graph.node.exhaustion_score": 0.5}
        }

        with patch(
            "src.services.methodology_strategy_service.InterviewPhaseSignal"
        ) as MockPhase:
            mock_instance = AsyncMock()
            mock_instance.detect.return_value = {"meta.interview.phase": "mid"}
            MockPhase.return_value = mock_instance

            result = await service.select_strategy_and_focus(
                _make_context(), _make_graph_state(), "test"
            )

        strategy_name, focus_node_id, alternatives, signals, node_signals, decomp = (
            result
        )
        assert strategy_name == "reflect"
        assert focus_node_id is None

    async def test_node_binding_required_selects_best_node(self):
        """Strategy with node_binding='required' selects best node."""
        deepen = StrategyConfig(
            name="deepen",
            description="Deepen",
            signal_weights={
                "llm.response_depth.low": 0.8,
                "graph.node.exhaustion_score.low": 1.0,
            },
            node_binding="required",
        )
        config = MethodologyConfig(
            name="test",
            description="Test",
            signals={},
            strategies=[deepen],
            phases=None,
        )

        service = MethodologyStrategyService()
        service.methodology_registry = MagicMock()
        service.methodology_registry.get_methodology.return_value = config

        service.global_signal_service = AsyncMock()
        service.global_signal_service.detect.return_value = {"llm.response_depth": 0.1}
        service.node_signal_service = AsyncMock()
        service.node_signal_service.detect.return_value = {
            "node_a": {"graph.node.exhaustion_score": 0.8},  # high → .low=False
            "node_b": {"graph.node.exhaustion_score": 0.1},  # low → .low=True
        }

        with patch(
            "src.services.methodology_strategy_service.InterviewPhaseSignal"
        ) as MockPhase:
            mock_instance = AsyncMock()
            mock_instance.detect.return_value = {"meta.interview.phase": "mid"}
            MockPhase.return_value = mock_instance

            result = await service.select_strategy_and_focus(
                _make_context(), _make_graph_state(), "test"
            )

        strategy_name, focus_node_id, *_ = result
        assert strategy_name == "deepen"
        assert focus_node_id == "node_b"  # Lower exhaustion wins

    async def test_alternatives_are_strategy_level(self):
        """Alternatives should be (strategy_name, score) tuples, not (strategy, node, score)."""
        s1 = StrategyConfig(
            name="deepen",
            description="D",
            signal_weights={"llm.response_depth.low": 0.8},
        )
        s2 = StrategyConfig(
            name="explore",
            description="E",
            signal_weights={"llm.response_depth.low": 0.5},
        )
        config = MethodologyConfig(
            name="test", description="T", signals={}, strategies=[s1, s2], phases=None
        )

        service = MethodologyStrategyService()
        service.methodology_registry = MagicMock()
        service.methodology_registry.get_methodology.return_value = config

        service.global_signal_service = AsyncMock()
        service.global_signal_service.detect.return_value = {"llm.response_depth": 0.1}
        service.node_signal_service = AsyncMock()
        service.node_signal_service.detect.return_value = {"node_1": {}}

        with patch(
            "src.services.methodology_strategy_service.InterviewPhaseSignal"
        ) as MockPhase:
            mock_instance = AsyncMock()
            mock_instance.detect.return_value = {"meta.interview.phase": "mid"}
            MockPhase.return_value = mock_instance

            result = await service.select_strategy_and_focus(
                _make_context(), _make_graph_state(), "test"
            )

        _, _, alternatives, *_ = result
        # Should be 2-tuples (strategy_name, score)
        assert len(alternatives) == 2
        assert len(alternatives[0]) == 2
        assert alternatives[0][0] == "deepen"  # Higher score
