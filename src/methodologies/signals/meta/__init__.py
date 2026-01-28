"""
Meta signals (composite - depend on multiple signal sources).

These signals integrate information from multiple other signals.
They provide higher-level insights about the interview state.

Example signals:
- InterviewProgressSignal: How far along the interview is
- StrategyDiversitySignal: How diverse the strategies have been
"""

from src.methodologies.signals.meta.progress import InterviewProgressSignal

__all__ = [
    "InterviewProgressSignal",
]
