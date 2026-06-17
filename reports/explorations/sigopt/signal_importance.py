"""
Signal Importance Analysis (Approach 1): Observational Pruning.

Reads scoring CSVs from synthetic interviews and identifies signals that
never contribute meaningfully to strategy selection. Produces a per-methodology
report classifying each signal weight as:

  - DEAD:       Signal never fires (value always 0/False) across all turns
  - CONSTANT:   Signal fires but contributes identically across all candidate
                strategies in a turn, so it never affects relative ranking
  - NEGLIGIBLE: |weighted_contribution| < threshold across all turns
  - ACTIVE:     Signal meaningfully contributes to at least some decisions

Usage:
    uv run python explorations/sigopt/signal_importance.py [--threshold 0.01]
                                                           [--output-csv]
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Methodology inference from filename
# ---------------------------------------------------------------------------

METHODOLOGY_SUFFIXES = {
    "_jtbd_": "jobs_to_be_done",
    "_mec_": "means_end_chain",
    "_ci_": "critical_incident",
    "_cjm_": "customer_journey_mapping",
    "_rg_": "repertory_grid",
}


def infer_methodology(filename: str) -> Optional[str]:
    for suffix, name in METHODOLOGY_SUFFIXES.items():
        if suffix in filename:
            return name
    return None


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class SignalStats:
    """Accumulates per-signal statistics across all turns."""

    signal_name: str
    weight: float = 0.0
    total_observations: int = 0
    times_nonzero_value: int = 0  # signal value != 0/False
    times_nonzero_contribution: int = 0  # weighted_contribution != 0
    max_abs_contribution: float = 0.0
    sum_abs_contribution: float = 0.0
    # Per-turn discrimination: does contribution vary across strategies?
    turns_with_variance: int = 0
    total_turns_seen: int = 0
    strategies_using: set = field(default_factory=set)


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------


def load_scoring_csvs(data_dir: Path) -> dict[str, list[Path]]:
    """Group scoring CSV files by methodology."""
    grouped: dict[str, list[Path]] = defaultdict(list)
    for csv_path in sorted(data_dir.glob("*_scoring.csv")):
        meth = infer_methodology(csv_path.name)
        if meth:
            grouped[meth].append(csv_path)
        else:
            print(
                f"  WARNING: Cannot infer methodology from {csv_path.name}",
                file=sys.stderr,
            )
    return dict(grouped)


def analyze_methodology(csv_files: list[Path]) -> dict[str, SignalStats]:
    """Analyze signal importance across all CSVs for one methodology."""
    stats: dict[str, SignalStats] = {}

    # Track per-turn contributions for variance analysis
    # Key: (file_idx, turn_number, signal_name) → list of contributions across strategies
    turn_contributions: dict[tuple, list[float]] = defaultdict(list)

    for file_idx, csv_path in enumerate(csv_files):
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                signal_name = row["signal_name"]
                strategy = row["strategy"]

                # Parse values
                raw_value = row["signal_value"]
                is_false = raw_value in ("False", "0", "0.0", "")
                try:
                    contribution = float(row["weighted_contribution"])
                except (ValueError, KeyError):
                    contribution = 0.0
                try:
                    weight = float(row["signal_weight"])
                except (ValueError, KeyError):
                    weight = 0.0

                # Initialize or update stats
                if signal_name not in stats:
                    stats[signal_name] = SignalStats(
                        signal_name=signal_name, weight=weight
                    )

                s = stats[signal_name]
                s.total_observations += 1
                s.strategies_using.add(strategy)

                if not is_false:
                    s.times_nonzero_value += 1

                abs_c = abs(contribution)
                if abs_c > 1e-9:
                    s.times_nonzero_contribution += 1
                if abs_c > s.max_abs_contribution:
                    s.max_abs_contribution = abs_c
                s.sum_abs_contribution += abs_c

                # Track for variance analysis
                turn_key = (file_idx, row["turn_number"], signal_name)
                turn_contributions[turn_key].append(contribution)

    # Compute per-turn variance (does the signal discriminate between strategies?)
    turn_signal_seen: dict[str, int] = defaultdict(int)
    turn_signal_varies: dict[str, int] = defaultdict(int)

    for (_, _, signal_name), contributions in turn_contributions.items():
        # Group by unique turn (file_idx + turn_number already does this)
        turn_signal_seen[signal_name] += 1
        # Check if contribution varies across strategies in this turn
        if len(set(round(c, 8) for c in contributions)) > 1:
            turn_signal_varies[signal_name] += 1

    for signal_name, s in stats.items():
        s.total_turns_seen = turn_signal_seen.get(signal_name, 0)
        s.turns_with_variance = turn_signal_varies.get(signal_name, 0)

    return stats


def classify_signal(s: SignalStats, threshold: float) -> str:
    """Classify a signal as DEAD, CONSTANT, NEGLIGIBLE, or ACTIVE."""
    if s.times_nonzero_value == 0:
        return "DEAD"
    if s.turns_with_variance == 0:
        return "CONSTANT"
    if s.max_abs_contribution < threshold:
        return "NEGLIGIBLE"
    return "ACTIVE"


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

CLASS_ORDER = {"DEAD": 0, "CONSTANT": 1, "NEGLIGIBLE": 2, "ACTIVE": 3}


def print_report(
    methodology: str,
    stats: dict[str, SignalStats],
    threshold: float,
    n_files: int,
) -> dict[str, str]:
    """Print human-readable report. Returns {signal_name: classification}."""
    classifications = {name: classify_signal(s, threshold) for name, s in stats.items()}

    # Sort: class order, then by name
    sorted_signals = sorted(
        stats.keys(),
        key=lambda n: (CLASS_ORDER.get(classifications[n], 99), n),
    )

    counts = defaultdict(int)
    for c in classifications.values():
        counts[c] += 1

    print(f"\n{'=' * 78}")
    print(f"  {methodology.upper()} — Signal Importance Report")
    print(f"  ({n_files} simulation(s), threshold={threshold})")
    print(f"{'=' * 78}")
    print()
    print(
        f"  Summary: {counts['DEAD']} dead, {counts['CONSTANT']} constant, "
        f"{counts['NEGLIGIBLE']} negligible, {counts['ACTIVE']} active "
        f"(of {len(stats)} total)"
    )
    print()

    # Print pruning candidates first
    prunable = counts["DEAD"] + counts["CONSTANT"] + counts["NEGLIGIBLE"]
    if prunable > 0:
        pct = prunable / len(stats) * 100
        print(
            f"  → {prunable}/{len(stats)} signal weights ({pct:.0f}%) are pruning candidates"
        )
    print()

    header = f"  {'Signal':<45} {'Class':<11} {'Weight':>7} {'MaxContrib':>11} {'FireRate':>9} {'DiscrimRate':>11}"
    print(header)
    print(f"  {'─' * 95}")

    for name in sorted_signals:
        s = stats[name]
        cls = classifications[name]
        fire_rate = (
            s.times_nonzero_value / s.total_observations if s.total_observations else 0
        )
        discrim_rate = (
            s.turns_with_variance / s.total_turns_seen if s.total_turns_seen else 0
        )

        marker = "" if cls == "ACTIVE" else " ✂"
        print(
            f"  {name:<45} {cls:<11} {s.weight:>7.2f} {s.max_abs_contribution:>11.4f} "
            f"{fire_rate:>8.1%} {discrim_rate:>10.1%}{marker}"
        )

    print()
    return classifications


def write_csv_report(
    output_path: Path,
    all_results: dict[str, tuple[dict[str, SignalStats], dict[str, str]]],
) -> None:
    """Write combined CSV report for all methodologies."""
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "methodology",
                "signal_name",
                "classification",
                "weight",
                "total_observations",
                "times_nonzero_value",
                "times_nonzero_contribution",
                "max_abs_contribution",
                "mean_abs_contribution",
                "fire_rate",
                "discrimination_rate",
                "total_turns_seen",
                "turns_with_variance",
                "n_strategies_using",
            ]
        )
        for methodology, (stats, classifications) in sorted(all_results.items()):
            for name in sorted(stats.keys()):
                s = stats[name]
                fire_rate = (
                    s.times_nonzero_value / s.total_observations
                    if s.total_observations
                    else 0
                )
                discrim_rate = (
                    s.turns_with_variance / s.total_turns_seen
                    if s.total_turns_seen
                    else 0
                )
                mean_abs = (
                    s.sum_abs_contribution / s.total_observations
                    if s.total_observations
                    else 0
                )
                writer.writerow(
                    [
                        methodology,
                        name,
                        classifications[name],
                        s.weight,
                        s.total_observations,
                        s.times_nonzero_value,
                        s.times_nonzero_contribution,
                        round(s.max_abs_contribution, 6),
                        round(mean_abs, 6),
                        round(fire_rate, 4),
                        round(discrim_rate, 4),
                        s.total_turns_seen,
                        s.turns_with_variance,
                        len(s.strategies_using),
                    ]
                )
    print(f"\n  CSV report saved to: {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Signal importance analysis for strategy scoring"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("synthetic_interviews"),
        help="Directory containing scoring CSVs (default: synthetic_interviews/)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.01,
        help="Max |contribution| below which a signal is NEGLIGIBLE (default: 0.01)",
    )
    parser.add_argument(
        "--output-csv",
        action="store_true",
        help="Also write results to explorations/sigopt/signal_importance_report.csv",
    )
    parser.add_argument(
        "--methodology",
        type=str,
        default=None,
        help="Analyze only this methodology (e.g., 'means_end_chain')",
    )
    args = parser.parse_args()

    grouped = load_scoring_csvs(args.data_dir)

    if not grouped:
        print("ERROR: No scoring CSVs found in", args.data_dir, file=sys.stderr)
        sys.exit(1)

    if args.methodology:
        if args.methodology not in grouped:
            print(
                f"ERROR: No data for methodology '{args.methodology}'", file=sys.stderr
            )
            print(f"  Available: {', '.join(sorted(grouped.keys()))}", file=sys.stderr)
            sys.exit(1)
        grouped = {args.methodology: grouped[args.methodology]}

    all_results: dict[str, tuple[dict[str, SignalStats], dict[str, str]]] = {}

    for methodology, csv_files in sorted(grouped.items()):
        stats = analyze_methodology(csv_files)
        classifications = print_report(
            methodology, stats, args.threshold, len(csv_files)
        )
        all_results[methodology] = (stats, classifications)

    # Cross-methodology summary
    if len(all_results) > 1:
        print(f"\n{'=' * 78}")
        print("  CROSS-METHODOLOGY SUMMARY")
        print(f"{'=' * 78}\n")

        # Find signals that are DEAD/CONSTANT/NEGLIGIBLE across ALL methodologies
        all_signals: set[str] = set()
        for stats, _ in all_results.values():
            all_signals.update(stats.keys())

        universally_prunable = []
        for sig in sorted(all_signals):
            classes = []
            for stats, classifications in all_results.values():
                if sig in classifications:
                    classes.append(classifications[sig])
            if classes and all(
                c in ("DEAD", "CONSTANT", "NEGLIGIBLE") for c in classes
            ):
                universally_prunable.append((sig, classes))

        if universally_prunable:
            print(
                f"  Signals prunable across ALL methodologies ({len(universally_prunable)}):"
            )
            for sig, classes in universally_prunable:
                class_str = ", ".join(
                    f"{m}={c}"
                    for (m, _), c in zip(sorted(all_results.items()), classes)
                )
                print(f"    ✂ {sig:<45} [{class_str}]")
        else:
            print("  No signals are universally prunable across all methodologies.")

    if args.output_csv:
        out_path = Path("explorations/sigopt/signal_importance_report.csv")
        write_csv_report(out_path, all_results)


if __name__ == "__main__":
    main()
