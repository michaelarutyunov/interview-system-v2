"""Strategy scoring package - Two-tier architecture.

Architecture (ADR-006):
- Tier 1: Hard constraint vetoes (tier1/)
- Tier 2: Weighted additive scoring (tier2/)
- Two-tier orchestration (two_tier/)
"""

# Two-tier engine
from src.services.scoring.two_tier import TwoTierScoringEngine, Tier1Scorer, Tier1Output, Tier2Scorer, Tier2Output
from src.services.scoring.two_tier.config import create_scoring_engine, load_config

# Tier 1 scorers
from src.services.scoring.tier1.knowledge_ceiling import KnowledgeCeilingScorer
from src.services.scoring.tier1.element_exhausted import ElementExhaustedScorer
from src.services.scoring.tier1.recent_redundancy import RecentRedundancyScorer

# Tier 2 scorers
from src.services.scoring.tier2.coverage_gap import CoverageGapScorer
from src.services.scoring.tier2.ambiguity import AmbiguityScorer
from src.services.scoring.tier2.depth_breadth_balance import DepthBreadthBalanceScorer
from src.services.scoring.tier2.engagement import EngagementScorer
from src.services.scoring.tier2.strategy_diversity import StrategyDiversityScorer
from src.services.scoring.tier2.novelty import NoveltyScorer

# Graph utilities
from src.services.scoring.graph_utils import (
    get_clusters,
    clear_cluster_cache,
    local_cluster_density,
    cluster_size,
    has_peripheral_candidates,
    has_opposite_stance_node,
    median_cluster_degree,
)

__all__ = [
    # Engine
    "TwoTierScoringEngine",
    "create_scoring_engine",
    "load_config",
    # Base classes
    "Tier1Scorer",
    "Tier1Output",
    "Tier2Scorer",
    "Tier2Output",
    # Tier 1 scorers
    "KnowledgeCeilingScorer",
    "ElementExhaustedScorer",
    "RecentRedundancyScorer",
    # Tier 2 scorers
    "CoverageGapScorer",
    "AmbiguityScorer",
    "DepthBreadthBalanceScorer",
    "EngagementScorer",
    "StrategyDiversityScorer",
    "NoveltyScorer",
    # Graph utilities
    "get_clusters",
    "clear_cluster_cache",
    "local_cluster_density",
    "cluster_size",
    "has_peripheral_candidates",
    "has_opposite_stance_node",
    "median_cluster_degree",
]
