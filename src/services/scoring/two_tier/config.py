"""Configuration loader for two-tier scoring system.

Loads scorer configurations from YAML and initializes the TwoTierScoringEngine.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
import yaml

from src.services.scoring.two_tier import TwoTierScoringEngine, Tier1Scorer, Tier2Scorer
from src.services.scoring.tier2 import (
    CoverageGapScorer,
    AmbiguityScorer,
    DepthBreadthBalanceScorer,
    EngagementScorer,
    StrategyDiversityScorer,
    NoveltyScorer,
)

logger = structlog.get_logger(__name__)


# Tier 2 scorer class mapping
TIER2_SCORER_CLASSES = {
    "CoverageGapScorer": CoverageGapScorer,
    "AmbiguityScorer": AmbiguityScorer,
    "DepthBreadthBalanceScorer": DepthBreadthBalanceScorer,
    "EngagementScorer": EngagementScorer,
    "StrategyDiversityScorer": StrategyDiversityScorer,
    "NoveltyScorer": NoveltyScorer,
}


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load scoring configuration from YAML file.

    Args:
        config_path: Path to YAML config file. If None, uses default path.

    Returns:
        Configuration dictionary
    """
    if config_path is None:
        # Default path: config/scoring.yaml relative to project root
        # Use a more robust path resolution that works with sys.path manipulation
        try:
            # Try to find project root by looking for the config directory
            current = Path(__file__).resolve().parent

            # Go up directories until we find config/scoring.yaml or reach a limit
            for _ in range(6):  # Max 6 levels up
                check_path = current / "config" / "scoring.yaml"
                if check_path.exists():
                    config_path = str(check_path)
                    break
                current = current.parent

            if config_path is None:
                # Fallback to current working directory / config / scoring.yaml
                cwd_config = Path.cwd() / "config" / "scoring.yaml"
                if cwd_config.exists():
                    config_path = str(cwd_config)
        except Exception:
            pass

    # If still None, use default config
    if config_path is None:
        logger.warning("Config file not found, using defaults")
        return _get_default_config()

    config_path = Path(config_path).resolve()

    if not config_path.exists():
        logger.warning(f"Config file not found: {config_path}, using defaults")
        return _get_default_config()

    with open(config_path) as f:
        config = yaml.safe_load(f)

    logger.info(f"Loaded configuration from {config_path}")
    return config


def _get_default_config() -> Dict[str, Any]:
    """Get default configuration when no config file exists.

    Returns:
        Default configuration dictionary
    """
    return {
        "scoring": {
            "tier1_scorers": [],  # No Tier 1 scorers by default
            "tier2_scorers": [
                {
                    "id": "coverage_gap",
                    "class": "CoverageGapScorer",
                    "enabled": True,
                    "weight": 0.20,
                    "params": {},
                },
                {
                    "id": "ambiguity",
                    "class": "AmbiguityScorer",
                    "enabled": True,
                    "weight": 0.15,
                    "params": {},
                },
                {
                    "id": "depth_breadth_balance",
                    "class": "DepthBreadthBalanceScorer",
                    "enabled": True,
                    "weight": 0.20,
                    "params": {},
                },
                {
                    "id": "engagement",
                    "class": "EngagementScorer",
                    "enabled": True,
                    "weight": 0.15,
                    "params": {},
                },
                {
                    "id": "strategy_diversity",
                    "class": "StrategyDiversityScorer",
                    "enabled": True,
                    "weight": 0.15,
                    "params": {},
                },
                {
                    "id": "novelty",
                    "class": "NoveltyScorer",
                    "enabled": True,
                    "weight": 0.15,
                    "params": {},
                },
            ],
            "validation": {
                "tier2_weights_must_sum_to": 1.0,
                "tolerance": 0.01,
            },
        },
        "engine": {
            "veto_on_first": True,
            "score_precision": 4,
            "alternatives_count": 3,
            "alternatives_min_score": 0.3,
        },
    }


def create_tier2_scorers(config: Dict[str, Any]) -> List[Tier2Scorer]:
    """Create Tier 2 scorer instances from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        List of initialized Tier 2 scorers
    """
    scorers = []

    tier2_configs = config.get("scoring", {}).get("tier2_scorers", [])

    for scorer_config in tier2_configs:
        if not scorer_config.get("enabled", True):
            continue

        class_name = scorer_config.get("class")
        scorer_class = TIER2_SCORER_CLASSES.get(class_name)

        if scorer_class is None:
            logger.warning(f"Unknown Tier 2 scorer class: {class_name}")
            continue

        # Create scorer instance with config
        scorer = scorer_class(config=scorer_config)
        scorers.append(scorer)

        logger.debug(f"Created Tier 2 scorer: {scorer}")

    return scorers


def validate_weights(scorers: List[Tier2Scorer], config: Dict[str, Any]) -> bool:
    """Validate that Tier 2 scorer weights sum to 1.0.

    Args:
        scorers: List of Tier 2 scorers
        config: Configuration dictionary

    Returns:
        True if weights are valid, False otherwise

    Raises:
        ValueError: If weights don't sum to 1.0
    """
    validation = config.get("scoring", {}).get("validation", {})
    target_sum = validation.get("tier2_weights_must_sum_to", 1.0)
    tolerance = validation.get("tolerance", 0.01)

    total_weight = sum(s.weight for s in scorers)

    if abs(total_weight - target_sum) > tolerance:
        raise ValueError(
            f"Tier 2 weights must sum to {target_sum} (current: {total_weight:.4f}). "
            f"Scorers: {[(s.scorer_id, s.weight) for s in scorers]}"
        )

    logger.info(f"Tier 2 weights validated: total={total_weight:.4f}")
    return True


def create_scoring_engine(
    config_path: Optional[str] = None,
    tier1_scorers: Optional[List[Tier1Scorer]] = None,
) -> TwoTierScoringEngine:
    """Create and initialize TwoTierScoringEngine from configuration.

    Args:
        config_path: Path to YAML config file. If None, uses default path.
        tier1_scorers: Optional list of Tier 1 scorers (not yet implemented)

    Returns:
        Initialized TwoTierScoringEngine
    """
    # Load configuration
    config = load_config(config_path)

    # Create Tier 2 scorers
    tier2_scorers = create_tier2_scorers(config)

    if not tier2_scorers:
        logger.warning("No Tier 2 scorers enabled")

    # Validate weights
    if tier2_scorers:
        validate_weights(tier2_scorers, config)

    # Tier 1 scorers (empty for now - will be implemented separately)
    tier1_scorers = tier1_scorers or []

    # Get engine configuration
    engine_config = config.get("engine", {})

    # Create engine
    engine = TwoTierScoringEngine(
        tier1_scorers=tier1_scorers,
        tier2_scorers=tier2_scorers,
        config=engine_config,
    )

    logger.info(
        "TwoTierScoringEngine created from config",
        num_tier1=len(tier1_scorers),
        num_tier2=len(tier2_scorers),
        config_path=config_path,
    )

    return engine
