"""LLM signal pool — response quality analysis via Kimi K2.5.

Signals:
- ResponseDepthSignal — elaboration quantity (1-5)
- SpecificitySignal — concreteness of language (1-5)
- CertaintySignal — epistemic confidence (1-5)
- ValenceSignal — emotional tone (1-5)
- EngagementSignal — willingness to engage (1-5)
"""

from src.signals.llm.signals.depth import ResponseDepthSignal
from src.signals.llm.signals.specificity import SpecificitySignal
from src.signals.llm.signals.certainty import CertaintySignal
from src.signals.llm.signals.valence import ValenceSignal
from src.signals.llm.signals.engagement import EngagementSignal

__all__ = [
    "ResponseDepthSignal",
    "SpecificitySignal",
    "CertaintySignal",
    "ValenceSignal",
    "EngagementSignal",
]
