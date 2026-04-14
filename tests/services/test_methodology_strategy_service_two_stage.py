"""Tests for joint strategy-node scoring in MethodologyStrategyService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.exceptions import ScoringError
from src.methodologies.registry import (
    StrategyConfig,
    MethodologyConfig,
    PhaseConfig,
)
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
class TestJointScoring:
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

    async def test_alternatives_are_structured_dicts(self):
        """Alternatives should be uniform 3-tuples (strategy, node_id_or_None, score)."""
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
        # Should be structured dicts with strategy, node_id, score keys
        assert len(alternatives) == 2
        assert alternatives[0]["strategy"] == "deepen"  # Higher score
        assert alternatives[0]["score"] > alternatives[1]["score"]


@pytest.mark.asyncio
class TestJointScoringDecompositionCapture:
    """Tests for joint strategy-node score decomposition capture in service layer."""

    async def test_decomposition_captured_in_output(self):
        """Service should capture decomposition from joint scoring."""
        deepen = StrategyConfig(
            name="deepen",
            description="D",
            signal_weights={
                "llm.response_depth.low": 0.8,
                "llm.engagement.high": 0.7,
                "graph.node.exhaustion_score.low": 1.0,  # Node-scoped weight
            },
        )
        explore = StrategyConfig(
            name="explore",
            description="E",
            signal_weights={"llm.response_depth.low": 0.5},
        )
        config = MethodologyConfig(
            name="test",
            description="Test",
            signals={},
            strategies=[deepen, explore],
            phases={
                "mid": PhaseConfig(
                    name="mid",
                    description="Mid interview phase",
                    signal_weights={"deepen": 1.3},
                    phase_bonuses={"deepen": 0.2},
                )
            },
        )

        service = MethodologyStrategyService()
        service.methodology_registry = MagicMock()
        service.methodology_registry.get_methodology.return_value = config

        service.global_signal_service = AsyncMock()
        service.global_signal_service.detect.return_value = {
            "llm.response_depth": 0.1,  # low → True
            "llm.engagement": 0.9,  # high → True
        }
        service.node_signal_service = AsyncMock()
        service.node_signal_service.detect.return_value = {
            "node_a": {"graph.node.exhaustion_score": 0.8},
            "node_b": {"graph.node.exhaustion_score": 0.1},
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

        # Verify strategy selection
        assert strategy_name == "deepen"
        assert focus_node_id == "node_b"  # Lower exhaustion wins

        # Verify decomposition exists
        assert decomp is not None
        assert len(decomp) > 0

    async def test_node_binding_none_has_none_node_id(self):
        """Strategy with node_binding='none' should have node_id=None in decomposition."""
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
        service.node_signal_service.detect.return_value = {}

        with patch(
            "src.services.methodology_strategy_service.InterviewPhaseSignal"
        ) as MockPhase:
            mock_instance = AsyncMock()
            mock_instance.detect.return_value = {"meta.interview.phase": "late"}
            MockPhase.return_value = mock_instance

            result = await service.select_strategy_and_focus(
                _make_context(), _make_graph_state(), "test"
            )

        strategy_name, focus_node_id, alternatives, signals, node_signals, decomp = (
            result
        )

        assert strategy_name == "reflect"
        assert focus_node_id is None  # No node selection

        # Should have strategy decomposition (rank_strategies uses "" for node_id)
        assert decomp is not None
        assert len(decomp) == 1
        assert decomp[0].strategy == "reflect"
        assert len(decomp[0].signal_contributions) == 1


@pytest.mark.asyncio
class TestJointScoringOverride:
    """Tests verifying that joint scoring can override the Stage 1 strategy winner."""

    async def test_better_node_overrides_higher_global_strategy(self):
        """When ascend wins globally but bridge has a better node, joint scoring selects bridge.

        This is the core motivation for joint scoring: the 2-stage architecture
        would pick ascend because it has the highest global score, but the
        (bridge, node_with_level_skip) pair has a higher combined score.
        """
        ascend = StrategyConfig(
            name="ascend",
            description="Ascend",
            signal_weights={
                "graph.node.gap_above.true": 0.5,
                "graph.node.exhaustion_score": -0.3,
            },
            node_binding="required",
            valid_when="graph.node.gap_above",
        )
        bridge = StrategyConfig(
            name="bridge",
            description="Bridge",
            signal_weights={
                "graph.node.level_skip.true": 0.8,
                "graph.node.exhaustion_score": -0.3,
            },
            node_binding="required",
            valid_when="graph.node.level_skip",
        )
        config = MethodologyConfig(
            name="test",
            description="Test",
            signals={},
            strategies=[ascend, bridge],
            phases=None,
        )

        service = MethodologyStrategyService()
        service.methodology_registry = MagicMock()
        service.methodology_registry.get_methodology.return_value = config

        service.global_signal_service = AsyncMock()
        service.global_signal_service.detect.return_value = {}  # No global signals

        # Node A: has gap_above=True, NOT level_skip → only ascend is eligible
        # Node B: has level_skip=True, NOT gap_above → only bridge is eligible
        # Node A has high exhaustion (penalty), Node B has low exhaustion
        service.node_signal_service = AsyncMock()
        service.node_signal_service.detect.return_value = {
            "node_a": {
                "graph.node.gap_above": True,
                "graph.node.level_skip": False,
                "graph.node.exhaustion_score": 0.9,  # High exhaustion → big penalty
            },
            "node_b": {
                "graph.node.gap_above": False,
                "graph.node.level_skip": True,
                "graph.node.exhaustion_score": 0.1,  # Low exhaustion → small penalty
            },
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

        # Bridge on node_b should win because:
        # bridge score on node_b = 0.8 * 1.0 + (-0.3) * 0.1 = 0.77
        # ascend score on node_a = 0.5 * 1.0 + (-0.3) * 0.9 = 0.23
        assert strategy_name == "bridge"
        assert focus_node_id == "node_b"

    async def test_all_gates_filtered_raises_error(self):
        """When all valid_when gates filter out all strategies, raise ScoringError."""
        ascend = StrategyConfig(
            name="ascend",
            description="Ascend",
            signal_weights={"graph.node.gap_above.true": 0.5},
            node_binding="required",
            valid_when="graph.node.gap_above",
        )
        config = MethodologyConfig(
            name="test",
            description="Test",
            signals={},
            strategies=[ascend],
            phases=None,
        )

        service = MethodologyStrategyService()
        service.methodology_registry = MagicMock()
        service.methodology_registry.get_methodology.return_value = config

        service.global_signal_service = AsyncMock()
        service.global_signal_service.detect.return_value = {}

        # No nodes pass the gap_above gate
        service.node_signal_service = AsyncMock()
        service.node_signal_service.detect.return_value = {
            "node_a": {
                "graph.node.gap_above": False,
            },
        }

        with patch(
            "src.services.methodology_strategy_service.InterviewPhaseSignal"
        ) as MockPhase:
            mock_instance = AsyncMock()
            mock_instance.detect.return_value = {"meta.interview.phase": "mid"}
            MockPhase.return_value = mock_instance

            with pytest.raises(ScoringError, match="No valid"):
                await service.select_strategy_and_focus(
                    _make_context(), _make_graph_state(), "test"
                )

    async def test_conversation_only_strategy_selected(self):
        """When only conversation strategies are eligible, returns (strategy, None, score)."""
        revitalize = StrategyConfig(
            name="revitalize",
            description="Revitalize",
            signal_weights={"llm.engagement.low": 0.8},
            node_binding="none",
        )
        config = MethodologyConfig(
            name="test",
            description="Test",
            signals={},
            strategies=[revitalize],
            phases=None,
        )

        service = MethodologyStrategyService()
        service.methodology_registry = MagicMock()
        service.methodology_registry.get_methodology.return_value = config

        service.global_signal_service = AsyncMock()
        service.global_signal_service.detect.return_value = {
            "llm.engagement": 0.1,  # low -> True
        }
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

        strategy_name, focus_node_id, alternatives, signals, node_signals, decomp = (
            result
        )

        assert strategy_name == "revitalize"
        assert focus_node_id is None
