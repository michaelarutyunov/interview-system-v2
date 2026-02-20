"""Generate a scoring decomposition CSV from a simulation JSON artifact.

Recomputes per-signal contributions post-hoc using:
- Signal values from the JSON turn (signals dict + node_signals)
- Signal weights from the methodology YAML config
- Phase adjustments (multipliers, bonuses) from the YAML config

Output schema (one row per turn × strategy × active_signal):
    turn_number, phase, strategy, node_id, signal_name, signal_value,
    signal_weight, weighted_contribution, phase_multiplier, phase_bonus,
    base_score, final_score, rank, selected
"""

import csv
import json
import sys
from pathlib import Path
from typing import Any

# Allow running from scripts/ or from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.methodologies.registry import MethodologyRegistry, StrategyConfig
from src.methodologies.scoring import _get_signal_value


def _compute_signal_contributions(
    strategy_config: StrategyConfig,
    signals: dict[str, Any],
) -> list[tuple[str, Any, float, float]]:
    """Return per-signal contributions for a strategy.

    Returns:
        List of (signal_key, signal_value, weight, weighted_contribution)
        Only includes signals that matched (signal_value is not None).
    """
    rows: list[tuple[str, Any, float, float]] = []
    for signal_key, weight in strategy_config.signal_weights.items():
        signal_value = _get_signal_value(signal_key, signals)
        if signal_value is None:
            continue

        if isinstance(signal_value, bool):
            contribution = weight if signal_value else 0.0
        elif isinstance(signal_value, (int, float)):
            contribution = weight * signal_value
        else:
            contribution = 0.0

        rows.append((signal_key, signal_value, weight, contribution))

    return rows


def _recompute_turn_scores(
    turn: dict[str, Any],
    strategies: list[StrategyConfig],
    phase_weights: dict[str, float],
    phase_bonuses: dict[str, float],
) -> list[dict[str, Any]]:
    """Recompute scoring decomposition for a single turn.

    Returns list of row dicts for the CSV.
    """
    signals: dict[str, Any] = turn.get("signals") or {}
    phase: str = signals.get("meta.interview.phase", "unknown")
    strategy_selected: str | None = turn.get("strategy_selected")
    turn_number: int = turn.get("turn_number", 0)

    # Collect strategy_alternatives from turn to get node_ids
    # Format: [{strategy, score}, ...] or [{strategy, node_id, score}, ...]
    alternatives: list[dict[str, Any]] = turn.get("strategy_alternatives") or []

    # Build set of (strategy, node_id) pairs visible in alternatives
    # to detect joint (strategy, node) scoring
    node_id_by_strategy: dict[str, str | None] = {}
    for alt in alternatives:
        strat = alt.get("strategy", "")
        nid = alt.get("node_id")  # None for non-joint scoring
        # Keep only first occurrence per strategy (highest ranked)
        if strat not in node_id_by_strategy:
            node_id_by_strategy[strat] = nid

    # For joint scoring: build per-node signal dicts from turn
    # The JSON doesn't store per-node signal values in turns (bead gaf8 handles that),
    # so we use the global signals dict for recomputation.
    # This is accurate for global strategies; node-specific scores will be approximated
    # using global signals (node signal values were the inputs but aren't in the JSON yet).
    # When bead gaf8 adds node_signals to the JSON, this function can be updated.

    # Compute base score and final score for every strategy
    strategy_scores: dict[str, tuple[float, float, float, float]] = {}
    # (base_score, multiplier, bonus, final_score)
    for strategy_config in strategies:
        base_score = sum(
            contrib
            for _, _, _, contrib in _compute_signal_contributions(
                strategy_config, signals
            )
        )
        multiplier = phase_weights.get(strategy_config.name, 1.0)
        bonus = phase_bonuses.get(strategy_config.name, 0.0)
        final_score = (base_score * multiplier) + bonus
        strategy_scores[strategy_config.name] = (
            base_score,
            multiplier,
            bonus,
            final_score,
        )

    # Rank strategies by final_score descending
    ranked_names = sorted(
        strategy_scores.keys(),
        key=lambda n: strategy_scores[n][3],
        reverse=True,
    )
    rank_by_strategy = {name: idx + 1 for idx, name in enumerate(ranked_names)}

    rows: list[dict[str, Any]] = []
    for strategy_config in strategies:
        strat_name = strategy_config.name
        base_score, multiplier, bonus, final_score = strategy_scores[strat_name]
        rank = rank_by_strategy[strat_name]
        selected = strat_name == strategy_selected
        node_id = node_id_by_strategy.get(strat_name)

        signal_rows = _compute_signal_contributions(strategy_config, signals)

        if signal_rows:
            for sig_key, sig_value, weight, contribution in signal_rows:
                rows.append(
                    {
                        "turn_number": turn_number,
                        "phase": phase,
                        "strategy": strat_name,
                        "node_id": node_id or "",
                        "signal_name": sig_key,
                        "signal_value": sig_value,
                        "signal_weight": round(weight, 4),
                        "weighted_contribution": round(contribution, 4),
                        "phase_multiplier": round(multiplier, 4),
                        "phase_bonus": round(bonus, 4),
                        "base_score": round(base_score, 4),
                        "final_score": round(final_score, 4),
                        "rank": rank,
                        "selected": selected,
                    }
                )
        else:
            # Strategy had no matching signals — emit one placeholder row so the
            # strategy is still visible in the CSV (all-zero contributions).
            rows.append(
                {
                    "turn_number": turn_number,
                    "phase": phase,
                    "strategy": strat_name,
                    "node_id": node_id or "",
                    "signal_name": "",
                    "signal_value": "",
                    "signal_weight": 0.0,
                    "weighted_contribution": 0.0,
                    "phase_multiplier": round(multiplier, 4),
                    "phase_bonus": round(bonus, 4),
                    "base_score": round(base_score, 4),
                    "final_score": round(final_score, 4),
                    "rank": rank,
                    "selected": selected,
                }
            )

    return rows


CSV_FIELDNAMES = [
    "turn_number",
    "phase",
    "strategy",
    "node_id",
    "signal_name",
    "signal_value",
    "signal_weight",
    "weighted_contribution",
    "phase_multiplier",
    "phase_bonus",
    "base_score",
    "final_score",
    "rank",
    "selected",
]


def generate_scoring_csv(json_path: Path) -> Path:
    """Generate a scoring decomposition CSV from a simulation JSON artifact.

    Args:
        json_path: Path to the simulation JSON file.

    Returns:
        Path to the written CSV file.
    """
    with open(json_path) as f:
        data = json.load(f)

    methodology_name: str = data["metadata"]["methodology"]
    registry = MethodologyRegistry()
    config = registry.get_methodology(methodology_name)

    strategies = config.strategies

    all_rows: list[dict[str, Any]] = []

    for turn in data.get("turns", []):
        signals: dict[str, Any] = turn.get("signals") or {}
        phase: str = signals.get("meta.interview.phase", "unknown")

        # Resolve phase weights and bonuses
        phase_weights: dict[str, float] = {}
        phase_bonuses: dict[str, float] = {}
        if config.phases and phase in config.phases:
            phase_weights = config.phases[phase].signal_weights
            phase_bonuses = config.phases[phase].phase_bonuses

        turn_rows = _recompute_turn_scores(
            turn, strategies, phase_weights, phase_bonuses
        )
        all_rows.extend(turn_rows)

    # Derive CSV path from JSON path: replace .json suffix with _scoring.csv
    csv_path = json_path.with_name(json_path.stem + "_scoring.csv")

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)

    return csv_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_scoring_csv.py <path_to_simulation.json>")
        sys.exit(1)

    json_file = Path(sys.argv[1])
    if not json_file.exists():
        print(f"File not found: {json_file}")
        sys.exit(1)

    csv_file = generate_scoring_csv(json_file)
    print(f"Scoring CSV written to: {csv_file}")
