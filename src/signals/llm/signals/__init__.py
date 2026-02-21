"""LLM signal pool — response quality analysis via Kimi K2.5.

Signals:
- ResponseDepthSignal — elaboration quantity (1-5)
- SpecificitySignal — concreteness of language (1-5)
- CertaintySignal — epistemic confidence (1-5)
- ValenceSignal — emotional tone (1-5)
- EngagementSignal — willingness to engage (1-5)
- IntellectualEngagementSignal — analytical reasoning and motivational depth (1-5)
"""

from src.signals.llm.signals.depth import ResponseDepthSignal
from src.signals.llm.signals.specificity import SpecificitySignal
from src.signals.llm.signals.certainty import CertaintySignal
from src.signals.llm.signals.valence import ValenceSignal
from src.signals.llm.signals.engagement import EngagementSignal
from src.signals.llm.signals.intellectual_engagement import IntellectualEngagementSignal

__all__ = [
    "ResponseDepthSignal",
    "SpecificitySignal",
    "CertaintySignal",
    "ValenceSignal",
    "EngagementSignal",
    "IntellectualEngagementSignal",
]
