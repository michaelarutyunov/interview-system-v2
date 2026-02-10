"""
Interview mode enumeration.

Defines available interview modes:
- EXPLORATORY: Emergent discovery for exploratory research (graph-driven)

Note: The dual-mode architecture (ADR-005) was deprecated in favor of
single exploratory mode. Previous coverage-driven mode was removed
(bead qce, 2026-01-30).
"""

from enum import Enum


class InterviewMode(str, Enum):
    """Interview mode."""

    EXPLORATORY = "exploratory"
    """Emergent discovery for exploratory research (graph-driven)."""
