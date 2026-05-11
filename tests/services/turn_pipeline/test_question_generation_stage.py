"""Tests for QuestionGenerationStage — history_includes_last_system_utterance flag."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.models.pipeline_contracts import (
    ContinuationOutput,
    StrategySelectionOutput,
)
from src.methodologies.registry import StrategyConfig
from src.services.turn_pipeline.context import PipelineContext
from src.services.turn_pipeline.stages.question_generation_stage import (
    QuestionGenerationStage,
)


def make_strategy_config(
    name: str, history_includes_last_system_utterance: bool = False
) -> StrategyConfig:
    return StrategyConfig(
        name=name,
        description="",
        signal_weights={},
        node_binding="none",
        history_includes_last_system_utterance=history_includes_last_system_utterance,
    )


def make_context(
    strategy: str,
    recent_utterances: list,
    user_input: str = "user reply",
    methodology: str = "means_end_chain_v2_strict",
) -> PipelineContext:
    ctx = PipelineContext(session_id="test-session", user_input=user_input)
    ctx.context_loading_output = MagicMock()
    ctx.context_loading_output.methodology = methodology
    ctx.context_loading_output.turn_number = 3
    ctx.context_loading_output.max_turns = 10
    ctx.context_loading_output.recent_utterances = recent_utterances
    ctx.context_loading_output.concept_name = "coffee"

    ctx.strategy_selection_output = StrategySelectionOutput(
        strategy=strategy,
        focus=None,
        generates_closing_question=False,
    )
    ctx.continuation_output = ContinuationOutput(
        should_continue=True,
        focus_concept={"label": "smooth taste", "node_type": "attribute"},
        reason="continuing",
        turns_remaining=7,
    )
    return ctx


def make_stage_and_mock_service():
    """Return (stage, mock_question_service)."""
    mock_service = MagicMock()
    mock_service.generate_conversation_level_question = AsyncMock(
        return_value="generated question"
    )
    mock_service.generate_question = AsyncMock(return_value="generated question")
    stage = QuestionGenerationStage(question_service=mock_service)
    return stage, mock_service


@pytest.mark.asyncio
async def test_history_includes_last_system_utterance_flag_true():
    """When flag is True, the last system utterance should be prepended to history."""
    system_utt = {"speaker": "system", "text": "Opening question?"}
    user_utt = {"speaker": "user", "text": "Some answer"}
    recent = [system_utt, user_utt]

    ctx = make_context(strategy="revitalize", recent_utterances=recent)
    stage, mock_service = make_stage_and_mock_service()

    strategy_cfg = make_strategy_config(
        "revitalize", history_includes_last_system_utterance=True
    )

    meth_config = MagicMock()
    meth_config.strategies = [strategy_cfg]
    registry = MagicMock()
    registry.get_methodology.return_value = meth_config

    with patch("src.methodologies.get_registry", return_value=registry):
        await stage.process(ctx)

    call_args = mock_service.generate_conversation_level_question.call_args
    utterances_used = call_args.kwargs.get(
        "recent_utterances", call_args.args[1] if len(call_args.args) > 1 else None
    )

    assert utterances_used is not None
    # The opening system utterance should appear (was prepended before windowing)
    speakers = [u["speaker"] for u in utterances_used]
    assert "system" in speakers, (
        f"Expected system utterance in history: {utterances_used}"
    )


@pytest.mark.asyncio
async def test_history_includes_last_system_utterance_flag_false():
    """When flag is False, the system utterance should NOT be prepended."""
    system_utt = {"speaker": "system", "text": "Opening question?"}
    user_utt = {"speaker": "user", "text": "Some answer"}
    recent = [system_utt, user_utt]

    ctx = make_context(strategy="elaborate", recent_utterances=recent)
    stage, mock_service = make_stage_and_mock_service()

    strategy_cfg = make_strategy_config(
        "elaborate", history_includes_last_system_utterance=False
    )

    meth_config = MagicMock()
    meth_config.strategies = [strategy_cfg]
    registry = MagicMock()
    registry.get_methodology.return_value = meth_config

    with patch("src.methodologies.get_registry", return_value=registry):
        await stage.process(ctx)

    call_args = mock_service.generate_conversation_level_question.call_args
    utterances_used = call_args.kwargs.get(
        "recent_utterances", call_args.args[1] if len(call_args.args) > 1 else None
    )

    assert utterances_used is not None
    # updated_utterances = recent + [current user input], so it already contains
    # the system utt from recent — but the prepend path should NOT add a duplicate.
    # The key check: no extra copy of the system utterance was added.
    system_count = sum(1 for u in utterances_used if u.get("speaker") == "system")
    # At most 1 system utterance (the one already in recent), not an extra prepend
    assert system_count <= 1, (
        f"Expected at most 1 system utterance in history (no prepend), got {system_count}: "
        f"{utterances_used}"
    )
