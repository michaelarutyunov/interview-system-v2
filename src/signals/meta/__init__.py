"""
Meta signals (composite - depend on multiple signal sources).

These signals integrate information from multiple other signals.
They provide higher-level insights about the interview state.

Example signals:
- InterviewPhaseSignal: Current interview phase (early/mid/late)
- NodeOpportunitySignal: What action to take for each node
"""

from src.signals.meta.interview_phase import InterviewPhaseSignal
from src.signals.meta.node_opportunity import NodeOpportunitySignal
from src.signals.meta.conversation_saturation import ConversationSaturationSignal
from src.signals.meta.canonical_saturation import CanonicalSaturationSignal

__all__ = [
    "InterviewPhaseSignal",
    "NodeOpportunitySignal",
    "ConversationSaturationSignal",
    "CanonicalSaturationSignal",
]
