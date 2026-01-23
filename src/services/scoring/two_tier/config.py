"""Configuration loader for two-tier scoring system.

Loads scorer configurations from YAML and initializes the TwoTierScoringEngine.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
import yaml

from src.services.scoring.two_tier import TwoTierScoringEngine, Tier1Scorer, Tier2Scorer
from src.services.scoring.tier1 import (
    KnowledgeCeilingScorer,
    ElementExhaustedScorer,
    RecentRedundancyScorer,
)
from src.services.scoring.tier2 import (
    CoverageGapScorer,
    AmbiguityScorer,
    DepthBreadthBalanceScorer,
    EngagementScorer,
    StrategyDiversityScorer,
    NoveltyScorer,
)

logger = structlog.get_logger(__name__)


# Tier 1 scorer class mapping
TIER1_SCORER_CLASSES = {
    "KnowledgeCeilingScorer": KnowledgeCeilingScorer,
    "ElementExhaustedScorer": ElementExhaustedScorer,
    "RecentRedundancyScorer": RecentRedundancyScorer,
}

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

    config_path_obj = Path(config_path).resolve()

    if not config_path_obj.exists():
        logger.warning(f"Config file not found: {config_path_obj}, using defaults")
        return _get_default_config()

    with open(str(config_path_obj)) as f:
        config = yaml.safe_load(f)

    logger.info(f"Loaded configuration from {config_path_obj}")
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
                    "strategy_weights": {
                        "deepen": 0.30,
                        "broaden": 0.24,
                        "cover_element": 0.30,
                        "default": 0.20,
                    },
                    "params": {},
                },
                {
                    "id": "ambiguity",
                    "class": "AmbiguityScorer",
                    "enabled": True,
                    "strategy_weights": {
                        "deepen": 0.20,
                        "default": 0.15,
                    },
                    "params": {},
                },
                {
                    "id": "depth_breadth_balance",
                    "class": "DepthBreadthBalanceScorer",
                    "enabled": True,
                    "strategy_weights": {
                        "deepen": 0.20,
                        "broaden": 0.20,
                        "default": 0.15,
                    },
                    "params": {},
                },
                {
                    "id": "engagement",
                    "class": "EngagementScorer",
                    "enabled": True,
                    "strategy_weights": {
                        "default": 0.15,
                    },
                    "params": {},
                },
                {
                    "id": "strategy_diversity",
                    "class": "StrategyDiversityScorer",
                    "enabled": True,
                    "strategy_weights": {
                        "default": 0.15,
                    },
                    "params": {},
                },
                {
                    "id": "novelty",
                    "class": "NoveltyScorer",
                    "enabled": True,
                    "strategy_weights": {
                        "default": 0.15,
                    },
                    "params": {},
                },
            ],
            "validation": {
                "require_strategy_weights": True,
            },
        },
        "engine": {
            "veto_on_first": True,
            "score_precision": 4,
            "alternatives_count": 3,
            "alternatives_min_score": 0.3,
            "phase_profiles": {
                "exploratory": {
                    "deepen": 0.8,
                    "broaden": 1.2,
                    "cover_element": 1.1,
                    "closing": 0.0,
                    "reflection": 0.3,
                },
                "focused": {
                    "deepen": 1.3,
                    "broaden": 0.4,
                    "cover_element": 1.1,
                    "closing": 0.5,
                    "reflection": 0.7,
                },
                "closing": {
                    "deepen": 0.3,
                    "broaden": 0.2,
                    "cover_element": 0.5,
                    "closing": 1.5,
                    "reflection": 0.3,
                },
            },
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

        # Ensure strategy_weights exists in config (new format)
        if "strategy_weights" not in scorer_config:
            # Migrate from old weight format to new strategy_weights format
            # For backward compatibility, set default weights
            old_weight = scorer_config.get("weight", 0.15)
            scorer_config["strategy_weights"] = {
                "default": old_weight
            }
            logger.debug(
                f"Migrated scorer {scorer_config['id']} from old 'weight' format "
                f"to new 'strategy_weights' format (default={old_weight})"
            )

        # Create scorer instance with config
        scorer = scorer_class(config=scorer_config)
        scorers.append(scorer)

        logger.debug(
            f"Created Tier 2 scorer: {scorer}",
            strategy_weights=list(scorer.config.get("strategy_weights", {}).keys())
        )

    return scorers


def create_tier1_scorers(config: Dict[str, Any]) -> List[Tier1Scorer]:
    """Create Tier 1 scorer instances from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        List of initialized Tier 1 scorers
    """
    scorers = []

    tier1_configs = config.get("scoring", {}).get("tier1_scorers", [])

    for scorer_config in tier1_configs:
        if not scorer_config.get("enabled", True):
            continue

        class_name = scorer_config.get("class")
        scorer_class = TIER1_SCORER_CLASSES.get(class_name)

        if scorer_class is None:
            logger.warning(f"Unknown Tier 1 scorer class: {class_name}")
            continue

        # Create scorer instance with config
        scorer = scorer_class(config=scorer_config)
        scorers.append(scorer)

        logger.debug(f"Created Tier 1 scorer: {scorer}")

    return scorers


def validate_weights(scorers: List[Tier2Scorer], config: Dict[str, Any]) -> bool:
    """Validate strategy_weights configuration.

    With the new formula (scorer_sum × phase_multiplier), we don't require
    weights to sum to 1.0. Instead, we validate that each scorer has
    strategy_weights properly configured.

    Args:
        scorers: List of Tier 2 scorers
        config: Configuration dictionary

    Returns:
        True if weights are valid, False otherwise

    Raises:
        ValueError: If strategy_weights are misconfigured
    """
    if not scorers:
        logger.warning("No Tier 2 scorers to validate")
        return True

    # Check that each scorer has strategy_weights with at least a default
    for scorer in scorers:
        strategy_weights = scorer.config.get("strategy_weights", {})

        if not strategy_weights:
            raise ValueError(
                f"Scorer {scorer.scorer_id} has no 'strategy_weights' configured. "
                f"Each scorer must have strategy_weights with at least a 'default' key."
            )

        if "default" not in strategy_weights:
            raise ValueError(
                f"Scorer {scorer.scorer_id} has no 'default' weight in strategy_weights. "
                f"Each scorer must have a default weight as fallback."
            )

        # Validate that weights are numeric and reasonable
        for strategy_id, weight in strategy_weights.items():
            if not isinstance(weight, (int, float)):
                raise ValueError(
                    f"Scorer {scorer.scorer_id} has non-numeric weight for "
                    f"strategy '{strategy_id}': {weight}"
                )
            if weight < 0 or weight > 2.0:
                logger.warning(
                    f"Scorer {scorer.scorer_id} has unusual weight for "
                    f"strategy '{strategy_id}': {weight} (expected 0-2 range)"
                )

    logger.info(
        f"Tier 2 strategy_weights validated: {len(scorers)} scorers with proper config"
    )
    return True


def create_scoring_engine(
    config_path: Optional[str] = None,
    tier1_scorers: Optional[List[Tier1Scorer]] = None,
) -> TwoTierScoringEngine:
    """Create and initialize TwoTierScoringEngine from configuration.

    Args:
        config_path: Path to YAML config file. If None, uses default path.
        tier1_scorers: Optional list of Tier 1 scorers (overrides config if provided)

    Returns:
        Initialized TwoTierScoringEngine
    """
    # Load configuration
    config = load_config(config_path)

    # Create Tier 1 scorers from config (unless overridden)
    if tier1_scorers is None:
        tier1_scorers = create_tier1_scorers(config)

    # Create Tier 2 scorers
    tier2_scorers = create_tier2_scorers(config)

    if not tier2_scorers:
        logger.warning("No Tier 2 scorers enabled")

    # Validate weights
    if tier2_scorers:
        validate_weights(tier2_scorers, config)

    # Get engine configuration (includes phase_profiles)
    engine_config = config.get("engine", {})

    # Add phase_profiles to engine_config if present
    phase_profiles = config.get("engine", {}).get("phase_profiles", {})
    if phase_profiles:
        engine_config["phase_profiles"] = phase_profiles
        logger.info(
            f"Loaded phase_profiles: {list(phase_profiles.keys())}"
        )
    else:
        logger.warning("No phase_profiles found in engine config")

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
        has_phase_profiles=bool(phase_profiles),
    )

    return engine
