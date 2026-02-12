"""LLM signals — response quality analysis via Kimi K2.5.

Signals:
- ResponseDepthSignal — elaboration quantity (1-5)
- SpecificitySignal — concreteness of language (1-5)
- CertaintySignal — epistemic confidence (1-5)
- ValenceSignal — emotional tone (1-5)
- EngagementSignal — willingness to engage (1-5)
"""

from src.signals.llm.signals import (
    ResponseDepthSignal,
    SpecificitySignal,
    CertaintySignal,
    ValenceSignal,
    EngagementSignal,
)

__all__ = [
    "ResponseDepthSignal",
    "SpecificitySignal",
    "CertaintySignal",
    "ValenceSignal",
    "EngagementSignal",
]
