"""
LLM-derived signals (high cost, fresh every response).

These signals are computed by analyzing the user's response with an LLM.
They are ALWAYS recomputed per response (PER_RESPONSE) to ensure freshness.

Key principle: NO cross-response caching for LLM signals.
Each response gets fresh analysis for accurate current state.

Example signals:
- ResponseDepthSignal: surface | moderate | deep analysis
- SentimentSignal: positive | neutral | negative sentiment
- UncertaintySignal: how uncertain/hesitant the response is
- AmbiguitySignal: how ambiguous/vague the response is
"""

from src.methodologies.signals.llm.depth import ResponseDepthSignal
from src.methodologies.signals.llm.quality import (
    SentimentSignal,
    UncertaintySignal,
    AmbiguitySignal,
)

__all__ = [
    "ResponseDepthSignal",
    "SentimentSignal",
    "UncertaintySignal",
    "AmbiguitySignal",
]
