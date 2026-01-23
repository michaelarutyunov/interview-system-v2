"""
Turn processing pipeline - ADR-008 Phase 3

This package implements a composable pipeline pattern for processing interview turns,
breaking up the monolithic SessionService.process_turn() method into testable stages.
"""

from .base import TurnStage
from .context import TurnContext
from .pipeline import TurnPipeline
from .result import TurnResult

__all__ = [
    "TurnStage",
    "TurnContext",
    "TurnPipeline",
    "TurnResult",
]
