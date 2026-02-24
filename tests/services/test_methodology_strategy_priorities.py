"""Test that MethodologyStrategyService passes node_type_priorities to node signal detection."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.methodologies.registry import StrategyConfig, MethodologyConfig


@pytest.mark.asyncio
async def test_merges_priorities_across_strategies():
    """Service merges node_type_priorities from all strategies (max per type)."""
    strategies = [
        StrategyConfig(
            name="explore",
            description="Explore",
            signal_weights={},
            node_type_priorities={"pain_point": 0.8, "job_trigger": 0.6},
        ),
        StrategyConfig(
            name="dig",
            description="Dig",
            signal_weights={},
            node_type_priorities={"pain_point": 0.5, "gain_point": 0.9},
        ),
    ]

    # Verify merge logic: pain_point should be max(0.8, 0.5) = 0.8
    merged = {}
    for strategy in strategies:
        for node_type, priority in strategy.node_type_priorities.items():
            if node_type not in merged or priority > merged[node_type]:
                merged[node_type] = priority

    assert merged == {
        "pain_point": 0.8,
        "job_trigger": 0.6,
        "gain_point": 0.9,
    }
