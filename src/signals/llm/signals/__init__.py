"""LLM signal pool — per-concept and global response rating.

Per-concept (scored for each extracted concept):
- ElaborationSignal — substantive content about the concept (1-5)
- ChargeSignal — emotional tone toward the concept (1-5)

Global (scored once per response):
- EngagementSignal — willingness to participate (1-5)
- CertaintySignal — expressed confidence in claims (1-5)
"""

from src.signals.llm.signals.charge import ChargeSignal
from src.signals.llm.signals.certainty import CertaintySignal
from src.signals.llm.signals.elaboration import ElaborationSignal
from src.signals.llm.signals.engagement import EngagementSignal

__all__ = [
    "ChargeSignal",
    "CertaintySignal",
    "ElaborationSignal",
    "EngagementSignal",
]
