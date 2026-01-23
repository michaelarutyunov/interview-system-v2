"""Tier 1 hard constraint scorers for two-tier system.

These scorers perform boolean veto checks before Tier 2 scoring:
- KnowledgeCeilingScorer: Checks for knowledge lack signals
- ElementExhaustedScorer: Checks for overmentioned elements
- RecentRedundancyScorer: Checks for question similarity
"""

from typing import Any, Dict, List

import structlog

from src.domain.models.knowledge_graph import GraphState
from src.services.scoring.two_tier.base import Tier1Scorer, Tier1Output
from src.services.scoring.tier1.knowledge_ceiling import KnowledgeCeilingScorer
from src.services.scoring.tier1.element_exhausted import ElementExhaustedScorer
from src.services.scoring.tier1.recent_redundancy import RecentRedundancyScorer

__all__ = [
    "KnowledgeCeilingScorer",
    "ElementExhaustedScorer",
    "RecentRedundancyScorer",
]
