"""Audit signal redundancy across simulation data.

Reads scoring.parquet (from extract_simulation_data.py) or raw simulation JSONs
and produces a ranked report of signal activity and decisiveness.

Three metrics per signal:
  fire_rate     — fraction of turns where contribution != 0
  avg_magnitude — mean |contribution| when fired
  decisive_rate — fraction of turns where removing this signal would flip
                  the winning strategy (rank 1 changes)

Classification:
  DEAD      — fire_rate == 0 across all data
  DORMANT   — fire_rate < 0.05
  MARGINAL  — fire_rate >= 0.05 but decisive_rate == 0
  ACTIVE    — decisive_rate > 0

Usage:
    # From pre-extracted parquet:
    uv run python scripts/diagnostics/analyze_signal_redundancy.py analysis/simulation_extract/

    # From raw simulation JSONs (extracts on the fly):
    uv run python scripts/diagnostics/analyze_signal_redundancy.py synthetic_interviews/v2/

    # Filter to one methodology:
    uv run python scripts/diagnostics/analyze_signal_redundancy.py analysis/simulation_extract/ --methodology means_end_chain_v3_flex

    # Filter to one or more personas:
    uv run python scripts/diagnostics/analyze_signal_redundancy.py analysis/simulation_extract/ --personas health_conscious skeptical_analyst
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


# ── Data loading ──────────────────────────────────────────────────────────────


def _load_from_parquet(parquet_dir: Path) -> pd.DataFrame:
    scoring_path = parquet_dir / "scoring.parquet"
    if not scoring_path.exists():
        sys.exit(
            f"scoring.parquet not found in {parquet_dir}. Run extract_simulation_data.py first."
        )
    return pd.read_parquet(scoring_path)


def _load_from_jsons(json_dir: Path) -> pd.DataFrame:
    """Extract scoring rows from raw simulation JSONs without writing parquet."""
    records: list[dict] = []
    for path in sorted(json_dir.glob("*.json")):
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception as e:
            print(f"WARN: skipping {path.name}: {e}", file=sys.stderr)
            continue

        meta = data.get("metadata", {})
        interview_id = meta.get("session_id", path.stem)
        persona = meta.get("persona_id", "unknown")
        concept = meta.get("concept_id", "unknown")
        methodology = meta.get("methodology", "unknown")

        for turn in data.get("turns", []):
            turn_num = turn.get("turn_number", 0)
            signals = turn.get("signals") or {}
            phase = signals.get("meta.interview.phase", "unknown")

            for entry in turn.get("score_decomposition") or []:
                for sc in entry.get("signal_contributions") or []:
                    records.append(
                        {
                            "interview_id": interview_id,
                            "persona": persona,
                            "concept": concept,
                            "methodology": methodology,
                            "turn": turn_num,
                            "phase": phase,
                            "strategy": entry["strategy"],
                            "node_id": entry.get("node_id", ""),
                            "signal_name": sc["name"],
                            "signal_value": str(sc["value"]),
                            "signal_weight": sc["weight"],
                            "contribution": sc["contribution"],
                            "base_score": entry["base_score"],
                            "phase_multiplier": entry["phase_multiplier"],
                            "phase_bonus": entry["phase_bonus"],
                            "final_score": entry["final_score"],
                            "rank": entry["rank"],
                            "selected": entry["selected"],
                        }
                    )

    if not records:
        sys.exit(f"No score_decomposition data found in {json_dir}.")
    return pd.DataFrame(records)


def load_scoring(input_path: Path) -> pd.DataFrame:
    if (input_path / "scoring.parquet").exists():
        return _load_from_parquet(input_path)
    if list(input_path.glob("*.json")):
        return _load_from_jsons(input_path)
    sys.exit(f"No scoring.parquet or JSON files found in {input_path}.")


# ── Knockout analysis ─────────────────────────────────────────────────────────


def compute_decisiveness(df: pd.DataFrame) -> pd.Series:
    """For each signal, compute the fraction of turns where removing it flips the winner.

    A signal is decisive on a given turn if:
      - The signal has non-zero contribution to any strategy on that turn
      - Re-ranking strategies without that signal's contribution changes rank 1
    """
    # Stage 1 only: node_id == "" (strategy-level scoring)
    stage1 = df[df["node_id"] == ""].copy()

    # Compute per-turn per-strategy final scores
    # final_score already includes phase modifiers; contribution is the additive
    # delta from this signal. Without the signal: adjusted = final_score - contribution.
    # But phase multiplier complicates this: contribution is pre-multiplier in the
    # base_score, then multiplied. We re-derive: contribution_in_final = contribution * phase_multiplier.
    stage1 = stage1.copy()
    stage1["contribution_in_final"] = (
        stage1["contribution"] * stage1["phase_multiplier"]
    )

    decisive_counts: dict[str, int] = {}
    total_turns_per_signal: dict[str, int] = {}

    # Group by turn (interview_id + turn uniquely identifies a scoring event)
    turn_keys = ["interview_id", "turn"]

    all_signals = stage1["signal_name"].unique()

    for signal in all_signals:
        sig_rows = stage1[stage1["signal_name"] == signal]
        # Turns where this signal appears (was evaluated)
        turns_with_signal = sig_rows[turn_keys].drop_duplicates()
        total = len(turns_with_signal)
        total_turns_per_signal[signal] = total

        if total == 0:
            decisive_counts[signal] = 0
            continue

        decisive = 0
        for _, trow in turns_with_signal.iterrows():
            iid, tnum = trow["interview_id"], trow["turn"]
            turn_data = stage1[
                (stage1["interview_id"] == iid) & (stage1["turn"] == tnum)
            ]

            # Original winner
            strategy_scores = turn_data.groupby("strategy")["final_score"].first()
            if strategy_scores.empty:
                continue
            original_winner = strategy_scores.idxmax()

            # Signal's contribution per strategy on this turn
            sig_contribs = (
                turn_data[turn_data["signal_name"] == signal]
                .groupby("strategy")["contribution_in_final"]
                .sum()
            )

            # Adjusted scores
            adjusted = strategy_scores.copy()
            for strat, delta in sig_contribs.items():
                if strat in adjusted.index:
                    adjusted[strat] -= delta

            new_winner = adjusted.idxmax()
            if new_winner != original_winner:
                decisive += 1

        decisive_counts[signal] = decisive

    return pd.Series(decisive_counts), pd.Series(total_turns_per_signal)


# ── Report ────────────────────────────────────────────────────────────────────


def classify(row: pd.Series) -> str:
    if row["fire_rate"] == 0:
        return "DEAD"
    if row["fire_rate"] < 0.05:
        return "DORMANT"
    if row["decisive_rate"] == 0:
        return "MARGINAL"
    return "ACTIVE"


def build_report(df: pd.DataFrame) -> pd.DataFrame:
    # Fire rate: fraction of appearances where contribution != 0
    fire = (
        df.groupby("signal_name")["contribution"]
        .agg(
            appearances="count",
            fired=lambda x: (x != 0).sum(),
        )
        .reset_index()
    )
    fire["fire_rate"] = fire["fired"] / fire["appearances"]
    mag = (
        df[df["contribution"] != 0]
        .groupby("signal_name")["contribution"]
        .apply(lambda x: x.abs().mean())
        .rename("avg_magnitude")
        .reset_index()
    )
    fire = fire.merge(mag, on="signal_name", how="left")
    fire["avg_magnitude"] = fire["avg_magnitude"].fillna(0.0)

    # Knockout decisiveness
    decisive_counts, total_turns = compute_decisiveness(df)
    fire["decisive_turns"] = (
        fire["signal_name"].map(decisive_counts).fillna(0).astype(int)
    )
    fire["signal_turns"] = fire["signal_name"].map(total_turns).fillna(0).astype(int)
    fire["decisive_rate"] = fire.apply(
        lambda r: (
            r["decisive_turns"] / r["signal_turns"] if r["signal_turns"] > 0 else 0.0
        ),
        axis=1,
    )

    fire["verdict"] = fire.apply(classify, axis=1)

    return fire.sort_values(["verdict", "fire_rate"], ascending=[True, True])


def print_report(
    report: pd.DataFrame, methodology: str | None, personas: list[str] | None
) -> None:
    filters = []
    if methodology:
        filters.append(f"methodology={methodology}")
    if personas:
        filters.append(f"personas={','.join(personas)}")
    filter_str = f" [{', '.join(filters)}]" if filters else ""

    total_turns = report["appearances"].sum()
    print(f"\n{'=' * 70}")
    print(f"SIGNAL REDUNDANCY AUDIT{filter_str}")
    print(f"{'=' * 70}")
    print(f"Total signal×strategy×turn rows: {total_turns:,}")
    print(f"Unique signals: {len(report)}")
    print()

    for verdict in ["DEAD", "DORMANT", "MARGINAL", "ACTIVE"]:
        subset = report[report["verdict"] == verdict]
        if subset.empty:
            continue

        label = {
            "DEAD": "DEAD — never fires (contribution always 0)",
            "DORMANT": "DORMANT — fires <5% of turns",
            "MARGINAL": "MARGINAL — fires but never decisive (no rank flip)",
            "ACTIVE": "ACTIVE — at least occasionally decisive",
        }[verdict]

        print(f"── {label} ({len(subset)}) {'─' * max(0, 60 - len(label))}")
        for _, row in subset.iterrows():
            decisive_str = (
                f"decisive {row['decisive_rate']:.0%} ({row['decisive_turns']}/{row['signal_turns']} turns)"
                if row["signal_turns"] > 0
                else "no stage-1 data"
            )
            print(
                f"  {row['signal_name']:<50} "
                f"fire={row['fire_rate']:.0%}  "
                f"mag={row['avg_magnitude']:.3f}  "
                f"{decisive_str}"
            )
        print()

    # Removal candidates summary
    removable = report[report["verdict"].isin(["DEAD", "DORMANT", "MARGINAL"])]
    print(f"{'=' * 70}")
    print(f"REMOVAL CANDIDATES: {len(removable)}/{len(report)} signals")
    print(
        f"  DEAD:     {len(report[report['verdict'] == 'DEAD'])} — safe to remove immediately"
    )
    print(
        f"  DORMANT:  {len(report[report['verdict'] == 'DORMANT'])} — verify edge case intent, then remove"
    )
    print(
        f"  MARGINAL: {len(report[report['verdict'] == 'MARGINAL'])} — fires but adds no selectivity; review"
    )
    print()
    print(
        "NOTE: 'no stage-1 data' means the signal is node-scoped (graph.node.*, meta.node.*,"
    )
    print(
        "technique.node.*) and only applies in Stage 2 (node selection), not strategy ranking."
    )
    print(
        "Decisive rate is not computable for these from strategy-level scoring alone."
    )
    print(
        "For node-scoped signals, fire_rate and avg_magnitude are the primary quality indicators."
    )
    print(f"{'=' * 70}\n")


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit signal redundancy in simulation scoring data."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Directory containing scoring.parquet (from extract_simulation_data.py) or raw *.json files.",
    )
    parser.add_argument(
        "--methodology",
        default=None,
        help="Filter to a single methodology (e.g. means_end_chain_v3_flex).",
    )
    parser.add_argument(
        "--personas",
        nargs="+",
        default=None,
        help="Filter to one or more personas (e.g. health_conscious skeptical_analyst).",
    )
    parser.add_argument(
        "--min-turns",
        type=int,
        default=0,
        help="Exclude signals appearing in fewer than N turns (avoids noise from rare configs).",
    )
    args = parser.parse_args()

    df = load_scoring(args.input)

    if args.methodology:
        if "methodology" not in df.columns:
            print(
                "WARN: methodology column not found in data — filter ignored.",
                file=sys.stderr,
            )
        else:
            df = df[df["methodology"] == args.methodology]
            if df.empty:
                sys.exit(f"No data for methodology '{args.methodology}'.")

    if args.personas:
        if "persona" not in df.columns:
            print(
                "WARN: persona column not found in data — filter ignored.",
                file=sys.stderr,
            )
        else:
            df = df[df["persona"].isin(args.personas)]
            if df.empty:
                sys.exit(f"No data for personas {args.personas}.")

    if args.min_turns > 0:
        counts = df.groupby("signal_name")["turn"].nunique()
        keep = counts[counts >= args.min_turns].index
        df = df[df["signal_name"].isin(keep)]

    report = build_report(df)
    print_report(report, args.methodology, args.personas)


if __name__ == "__main__":
    main()
