"""
Sensitivity Analysis (Approach 2): Decision Impact.

For each signal weight in the scoring data, measures how often *removing* that
signal would change which strategy gets selected. This reveals which signals
are "load-bearing" (flip decisions) vs "decorative" (never change the winner).

The analysis replays existing scoring data — no new LLM calls required.

Method:
  For each turn in each simulation:
    1. Identify the actually-selected strategy (rank=0 or selected=True)
    2. For each signal present in that turn:
       a. Subtract its weighted_contribution from all strategies' base_scores
       b. Re-apply phase adjustments (multiplier + bonus)
       c. Re-rank strategies
       d. If the winner changes → record a "decision flip"
    3. Aggregate flip counts per signal per methodology

Usage:
    uv run python explorations/sigopt/sensitivity_analysis.py [--output-csv]
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
class TurnCandidate:
    """One strategy candidate in a turn's scoring."""

    strategy: str
    node_id: str
    base_score: float
    phase_multiplier: float
    phase_bonus: float
    final_score: float
    selected: bool
    # signal_name → weighted_contribution
    signal_contributions: dict[str, float] = field(default_factory=dict)


@dataclass
class SensitivityResult:
    """Aggregated sensitivity for one signal across all turns."""

    signal_name: str
    total_turns_present: int = 0
    decision_flips: int = 0
    # When it flips, what does it flip FROM → TO?
    flip_details: list[tuple[str, str]] = field(default_factory=list)

    @property
    def flip_rate(self) -> float:
        return (
            self.decision_flips / self.total_turns_present
            if self.total_turns_present
            else 0.0
        )


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
    return dict(grouped)


def parse_turn_candidates(csv_path: Path) -> dict[int, list[TurnCandidate]]:
    """Parse CSV into per-turn candidate lists.

    Returns: dict keyed by turn_number → list of TurnCandidate
    """
    # Group rows by (turn_number) → then by (strategy, node_id)
    # Each unique (turn, strategy, node_id) is one candidate
    turn_rows: dict[int, dict[tuple[str, str], TurnCandidate]] = defaultdict(dict)

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            turn_num = int(row["turn_number"])
            strategy = row["strategy"]
            node_id = row.get("node_id", "")
            signal_name = row["signal_name"]

            try:
                contribution = float(row["weighted_contribution"])
            except (ValueError, KeyError):
                contribution = 0.0

            candidate_key = (strategy, node_id)

            if candidate_key not in turn_rows[turn_num]:
                try:
                    base_score = float(row["base_score"])
                except (ValueError, KeyError):
                    base_score = 0.0
                try:
                    phase_mult = float(row["phase_multiplier"])
                except (ValueError, KeyError):
                    phase_mult = 1.0
                try:
                    phase_bonus = float(row["phase_bonus"])
                except (ValueError, KeyError):
                    phase_bonus = 0.0
                try:
                    final_score = float(row["final_score"])
                except (ValueError, KeyError):
                    final_score = 0.0

                selected = row.get("selected", "False").strip().lower() == "true"

                turn_rows[turn_num][candidate_key] = TurnCandidate(
                    strategy=strategy,
                    node_id=node_id,
                    base_score=base_score,
                    phase_multiplier=phase_mult,
                    phase_bonus=phase_bonus,
                    final_score=final_score,
                    selected=selected,
                )

            turn_rows[turn_num][candidate_key].signal_contributions[signal_name] = (
                contribution
            )

    return {
        turn_num: list(candidates.values())
        for turn_num, candidates in turn_rows.items()
    }


def find_winner(candidates: list[TurnCandidate]) -> Optional[TurnCandidate]:
    """Find the selected candidate, falling back to highest final_score."""
    selected = [c for c in candidates if c.selected]
    if selected:
        return selected[0]
    if candidates:
        return max(candidates, key=lambda c: c.final_score)
    return None


def simulate_removal(
    candidates: list[TurnCandidate],
    signal_name: str,
) -> Optional[str]:
    """Re-score candidates with a signal removed. Returns new winner's strategy+node_id."""
    adjusted: list[tuple[str, str, float]] = []

    for c in candidates:
        removed_contribution = c.signal_contributions.get(signal_name, 0.0)
        new_base = c.base_score - removed_contribution
        new_final = (new_base * c.phase_multiplier) + c.phase_bonus
        adjusted.append((c.strategy, c.node_id, new_final))

    if not adjusted:
        return None

    # Sort by score descending, break ties by strategy name for stability
    adjusted.sort(key=lambda x: (-x[2], x[0], x[1]))
    winner = adjusted[0]
    return f"{winner[0]}|{winner[1]}"


def analyze_methodology(csv_files: list[Path]) -> dict[str, SensitivityResult]:
    """Run sensitivity analysis across all CSVs for one methodology."""
    results: dict[str, SensitivityResult] = {}

    for csv_path in csv_files:
        turns = parse_turn_candidates(csv_path)

        for _turn_num, candidates in sorted(turns.items()):
            if not candidates:
                continue

            original_winner = find_winner(candidates)
            if not original_winner:
                continue

            original_key = f"{original_winner.strategy}|{original_winner.node_id}"

            # Collect all signals present in this turn
            all_signals_in_turn: set[str] = set()
            for c in candidates:
                all_signals_in_turn.update(c.signal_contributions.keys())

            for signal_name in all_signals_in_turn:
                if signal_name not in results:
                    results[signal_name] = SensitivityResult(signal_name=signal_name)

                r = results[signal_name]
                r.total_turns_present += 1

                new_winner_key = simulate_removal(candidates, signal_name)

                if new_winner_key and new_winner_key != original_key:
                    r.decision_flips += 1
                    orig_strategy = original_key.split("|")[0]
                    new_strategy = new_winner_key.split("|")[0]
                    r.flip_details.append((orig_strategy, new_strategy))

    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def print_report(
    methodology: str,
    results: dict[str, SensitivityResult],
    n_files: int,
) -> None:
    """Print human-readable sensitivity report."""
    # Sort by flip rate descending
    sorted_signals = sorted(
        results.values(),
        key=lambda r: (-r.flip_rate, -r.decision_flips, r.signal_name),
    )

    total_turns = (
        max(r.total_turns_present for r in sorted_signals) if sorted_signals else 0
    )

    # Classify
    load_bearing = [r for r in sorted_signals if r.flip_rate >= 0.10]
    moderate = [r for r in sorted_signals if 0.01 <= r.flip_rate < 0.10]
    decorative = [r for r in sorted_signals if r.flip_rate < 0.01]

    print(f"\n{'=' * 90}")
    print(f"  {methodology.upper()} — Sensitivity Analysis")
    print(f"  ({n_files} simulation(s), ~{total_turns} turns analyzed)")
    print(f"{'=' * 90}")
    print()
    print(
        f"  Summary: {len(load_bearing)} load-bearing (≥10%), "
        f"{len(moderate)} moderate (1-10%), "
        f"{len(decorative)} decorative (<1%)"
    )
    print()

    header = f"  {'Signal':<45} {'Flips':>6} {'Turns':>6} {'FlipRate':>9} {'Impact'}"
    print(header)
    print(f"  {'─' * 85}")

    for r in sorted_signals:
        if r.flip_rate >= 0.10:
            impact = "LOAD-BEARING"
        elif r.flip_rate >= 0.01:
            impact = "moderate"
        else:
            impact = "decorative   ✂"

        print(
            f"  {r.signal_name:<45} {r.decision_flips:>6} {r.total_turns_present:>6} "
            f"{r.flip_rate:>8.1%}  {impact}"
        )

    # Show top flip patterns for load-bearing signals
    if load_bearing:
        print(f"\n  {'─' * 85}")
        print("  Flip patterns for load-bearing signals:")
        for r in load_bearing[:10]:
            if r.flip_details:
                # Count flip patterns
                pattern_counts: dict[tuple[str, str], int] = defaultdict(int)
                for from_s, to_s in r.flip_details:
                    pattern_counts[(from_s, to_s)] += 1
                top_patterns = sorted(pattern_counts.items(), key=lambda x: -x[1])[:3]
                patterns_str = ", ".join(
                    f"{fr}→{to} ({cnt}x)" for (fr, to), cnt in top_patterns
                )
                print(f"    {r.signal_name:<43} {patterns_str}")

    print()


def write_csv_report(
    output_path: Path,
    all_results: dict[str, dict[str, SensitivityResult]],
) -> None:
    """Write combined CSV report for all methodologies."""
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "methodology",
                "signal_name",
                "decision_flips",
                "total_turns_present",
                "flip_rate",
                "impact_class",
                "top_flip_pattern",
            ]
        )
        for methodology, results in sorted(all_results.items()):
            for name in sorted(results.keys()):
                r = results[name]
                if r.flip_rate >= 0.10:
                    impact = "load-bearing"
                elif r.flip_rate >= 0.01:
                    impact = "moderate"
                else:
                    impact = "decorative"

                # Top flip pattern
                if r.flip_details:
                    pattern_counts: dict[tuple[str, str], int] = defaultdict(int)
                    for from_s, to_s in r.flip_details:
                        pattern_counts[(from_s, to_s)] += 1
                    top = max(pattern_counts.items(), key=lambda x: x[1])
                    top_pattern = f"{top[0][0]}→{top[0][1]} ({top[1]}x)"
                else:
                    top_pattern = ""

                writer.writerow(
                    [
                        methodology,
                        name,
                        r.decision_flips,
                        r.total_turns_present,
                        round(r.flip_rate, 4),
                        impact,
                        top_pattern,
                    ]
                )
    print(f"\n  CSV report saved to: {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sensitivity analysis for signal weights"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("synthetic_interviews"),
        help="Directory containing scoring CSVs (default: synthetic_interviews/)",
    )
    parser.add_argument(
        "--output-csv",
        action="store_true",
        help="Also write results to explorations/sigopt/sensitivity_report.csv",
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

    all_results: dict[str, dict[str, SensitivityResult]] = {}

    for methodology, csv_files in sorted(grouped.items()):
        results = analyze_methodology(csv_files)
        print_report(methodology, results, len(csv_files))
        all_results[methodology] = results

    # Cross-methodology summary
    if len(all_results) > 1:
        print(f"\n{'=' * 90}")
        print("  CROSS-METHODOLOGY SUMMARY")
        print(f"{'=' * 90}\n")

        all_signals: set[str] = set()
        for results in all_results.values():
            all_signals.update(results.keys())

        # Find universally decorative signals
        universally_decorative = []
        for sig in sorted(all_signals):
            rates = []
            for results in all_results.values():
                if sig in results:
                    rates.append(results[sig].flip_rate)
            if rates and all(r < 0.01 for r in rates):
                universally_decorative.append(sig)

        # Find universally load-bearing signals
        universally_load_bearing = []
        for sig in sorted(all_signals):
            rates = []
            for results in all_results.values():
                if sig in results:
                    rates.append(results[sig].flip_rate)
            if rates and all(r >= 0.10 for r in rates):
                universally_load_bearing.append(sig)

        if universally_load_bearing:
            print(
                f"  Load-bearing across ALL methodologies ({len(universally_load_bearing)}):"
            )
            for sig in universally_load_bearing:
                avg_rate = sum(
                    all_results[m][sig].flip_rate
                    for m in all_results
                    if sig in all_results[m]
                ) / len(all_results)
                print(f"    ★ {sig:<45} avg flip rate: {avg_rate:.1%}")

        if universally_decorative:
            print(
                f"\n  Decorative across ALL methodologies ({len(universally_decorative)}):"
            )
            for sig in universally_decorative:
                print(f"    ✂ {sig}")

    if args.output_csv:
        out_path = Path("explorations/sigopt/sensitivity_report.csv")
        write_csv_report(out_path, all_results)


if __name__ == "__main__":
    main()
