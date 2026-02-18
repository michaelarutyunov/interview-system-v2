"""Strategy scoring using signal weights from YAML configs.

Scores strategies based on detected signals and strategy weights
defined in methodology YAML configs. All signals are expected to be
normalized at source to [0, 1] or bool.
"""

import structlog
from typing import List, Tuple, Dict, Any, Optional
from src.methodologies.registry import StrategyConfig

log = structlog.get_logger(__name__)


def score_strategy(
    strategy_config: StrategyConfig,
    signals: Dict[str, Any],
) -> float:
    """
    Score a strategy based on current signals using YAML weights.

    Args:
        strategy_config: Strategy config with signal_weights from YAML
        signals: Dict of detected signals (namespaced, normalized to [0,1] or bool)

    Returns:
        Weighted score (can be negative or > 1 depending on weights)
    """
    weights = strategy_config.signal_weights
    score = 0.0

    for signal_key, weight in weights.items():
        signal_value = _get_signal_value(signal_key, signals)

        if signal_value is None:
            continue

        if isinstance(signal_value, bool):
            contribution = weight if signal_value else 0.0
        elif isinstance(signal_value, (int, float)):
            contribution = weight * signal_value  # Already [0,1]
        else:
            contribution = 0.0

        score += contribution

    return score


def _get_signal_value(signal_key: str, signals: Dict[str, Any]) -> Any:
    """Get signal value by key, handling compound keys.

    Examples:
        - "graph.max_depth" -> signals.get("graph.max_depth")
        - "llm.response_depth.surface" -> Check if signals["llm.response_depth"] == "surface"
    """
    # Direct match
    if signal_key in signals:
        return signals[signal_key]

    # Compound key (e.g., "llm.response_depth.surface")
    # This means: signal "llm.response_depth" should have value "surface"
    if "." in signal_key:
        parts = signal_key.split(".")
        base_signal = ".".join(parts[:-1])  # e.g., "llm.response_depth"
        expected_value = parts[-1]  # e.g., "surface"

        if base_signal in signals:
            actual_value = signals[base_signal]

            # Bool coercion: match Python bool against "true"/"false" strings
            if isinstance(actual_value, bool) and expected_value in (
                "true",
                "false",
            ):
                return actual_value == (expected_value == "true")

            # Threshold binning for normalized [0,1] signals
            # Note: bool check must come first since bool is a subclass of int
            if (
                isinstance(actual_value, (int, float))
                and not isinstance(actual_value, bool)
                and expected_value
                in (
                    "low",
                    "mid",
                    "high",
                )
            ):
                if expected_value == "low":
                    return actual_value <= 0.25
                elif expected_value == "mid":
                    return 0.25 < actual_value < 0.75
                elif expected_value == "high":
                    return actual_value >= 0.75

            # Return True if values match (for string enum scoring)
            return actual_value == expected_value

    return None


def rank_strategies(
    strategy_configs: List[StrategyConfig],
    signals: Dict[str, Any],
    phase_weights: Optional[Dict[str, float]] = None,
    phase_bonuses: Optional[Dict[str, float]] = None,
) -> List[Tuple[StrategyConfig, float]]:
    """
    Rank all strategies by score.

    Args:
        strategy_configs: List of strategy configs from YAML
        signals: Dict of detected signals
        phase_weights: Optional dict of phase-based weight multipliers (e.g., {"deepen": 1.5, "reflect": 0.5})
        phase_bonuses: Optional dict of phase-based additive bonuses (e.g., {"reflect": 0.3})
                        Applied additively: final_score = (base_score * multiplier) + bonus

    Returns:
        List of (strategy_config, score) sorted descending by score
    """
    import structlog

    log = structlog.get_logger(__name__)

    scored = []
    for strategy_config in strategy_configs:
        # Score strategy using signal weights
        base_score = score_strategy(strategy_config, signals)

        # Apply phase weight multiplier if available
        if phase_weights and strategy_config.name in phase_weights:
            multiplier = phase_weights[strategy_config.name]
        else:
            multiplier = 1.0

        # Apply phase bonus additively if available
        bonus = 0.0
        if phase_bonuses and strategy_config.name in phase_bonuses:
            bonus = phase_bonuses[strategy_config.name]

        # Final score: (base_score * multiplier) + bonus
        final_score = (base_score * multiplier) + bonus

        scored.append((strategy_config, final_score))

    # Sort by score descending
    scored.sort(key=lambda x: x[1], reverse=True)

    # Log scores for debugging
    log.info(
        "strategies_ranked",
        phase=signals.get("meta.interview.phase", "unknown"),
        phase_weights=phase_weights,
        phase_bonuses=phase_bonuses,
        ranked=[(s.name, score) for s, score in scored],
    )

    return scored


def rank_strategy_node_pairs(
    strategies: List[StrategyConfig],
    global_signals: Dict[str, Any],
    node_signals: Dict[str, Dict[str, Any]],
    node_tracker=None,
    phase_weights: Optional[Dict[str, float]] = None,
    phase_bonuses: Optional[Dict[str, float]] = None,
) -> List[Tuple[StrategyConfig, str, float]]:
    """
    Rank (strategy, node) pairs by joint score.

    This function implements the D1 architecture for joint strategy-node
    scoring. It scores each strategy for each node, combining global signals
    with node-specific signals.

    Args:
        strategies: List of strategy configs from YAML
        global_signals: Dict of global detected signals
        node_signals: Dict mapping node_id to node-specific signals
                     {node_id: {signal_name: value}}
        node_tracker: Optional NodeStateTracker for future use
        phase_weights: Optional dict of phase-based weight multipliers
                      {strategy_name: multiplier}
        phase_bonuses: Optional dict of phase-based additive bonuses
                      {strategy_name: bonus}
                      Applied additively: final_score = (base_score * multiplier) + bonus

    Returns:
        List of (strategy_config, node_id, score) sorted descending by score
    """
    current_phase = global_signals.get("meta.interview.phase", "unknown")

    scored_pairs: List[Tuple[StrategyConfig, str, float]] = []

    for strategy in strategies:
        for node_id, node_signal_dict in node_signals.items():
            # Merge global + node signals
            # Node signals take precedence when keys overlap
            combined_signals = {**global_signals, **node_signal_dict}

            # Score strategy for this specific node
            base_score = score_strategy(strategy, combined_signals)

            # Apply phase weight multiplier if available
            multiplier = 1.0
            if phase_weights and strategy.name in phase_weights:
                multiplier = phase_weights[strategy.name]

            # Apply phase bonus additively if available
            bonus = 0.0
            if phase_bonuses and strategy.name in phase_bonuses:
                bonus = phase_bonuses[strategy.name]

            # Final score: (base_score * multiplier) + bonus
            final_score = (base_score * multiplier) + bonus

            scored_pairs.append((strategy, node_id, final_score))

            log.debug(
                "strategy_node_pair_scored",
                strategy=strategy.name,
                node_id=node_id,
                base_score=round(base_score, 4),
                phase_multiplier=multiplier,
                phase_bonus=bonus,
                final_score=round(final_score, 4),
                phase=current_phase,
            )

    # Sort by score descending
    ranked = sorted(scored_pairs, key=lambda x: x[2], reverse=True)

    log.info(
        "joint_scoring_top5",
        phase=current_phase,
        phase_weights=phase_weights,
        phase_bonuses=phase_bonuses,
        top5=[
            {"strategy": s.name, "node_id": nid, "score": round(sc, 4)}
            for s, nid, sc in ranked[:5]
        ],
    )

    return ranked
