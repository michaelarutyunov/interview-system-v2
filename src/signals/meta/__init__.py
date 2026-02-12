"""
Meta signals (composite - depend on multiple signal sources).

These signals integrate information from multiple other signals.
They provide higher-level insights about the interview state.

Example signals:
- InterviewProgressSignal: How far along the interview is
- InterviewPhaseSignal: Current interview phase (early/mid/late)
- NodeOpportunitySignal: What action to take for each node
"""

from src.signals.meta.progress import InterviewProgressSignal
from src.signals.meta.interview_phase import InterviewPhaseSignal
from src.signals.meta.node_opportunity import NodeOpportunitySignal

__all__ = [
    "InterviewProgressSignal",
    "InterviewPhaseSignal",
    "NodeOpportunitySignal",
]
