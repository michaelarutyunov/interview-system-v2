#!/usr/bin/env python3
"""Generate a scoring summary markdown from a scoring decomposition CSV.

Reads the per-signal, per-candidate CSV produced by generate_scoring_csv.py
and produces a markdown file with aggregated tables: firing rates, global
signals, dead signals, always-firing signals, phase multiplier analysis,
signal budget decomposition, node selection frequency, and gate analysis.

Usage:
    python scripts/reporting/generate_scoring_summary.py <scoring_csv> [--output <path>]
"""

import argparse
import sys
from pathlib import Path

import pandas as pd


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_v = sorted(values)
    idx = min(int(len(sorted_v) * pct / 100), len(sorted_v) - 1)
    return sorted_v[idx]


def generate_summary(csv_path: Path) -> str:
    """Generate markdown summary from scoring CSV."""
    df_raw = pd.read_csv(csv_path)

    gated = df_raw[df_raw["gated"].astype(str).isin(["True", "1"])]
    df = df_raw[~df_raw["gated"].astype(str).isin(["True", "1"])].copy()

    df["fired"] = df["signal_value"].astype(str).isin(["True", "1"]) | (
        pd.to_numeric(df["signal_value"], errors="coerce").fillna(0) > 0
    )

    lines: list[str] = []

    def L(text: str = "") -> None:
        lines.append(text)

    L("# Scoring Summary")
    L()
    L(f"Source: `{csv_path.name}`")
    L(f"Total rows: {len(df_raw):,} (gated: {len(gated):,})")
    L()

    # --- Signal Firing Rates ---
    L("## Signal Firing Rates")
    L()
    signal_total = df.groupby("signal_name").size().rename("total")
    fired_agg = (
        df[df["fired"]]
        .groupby("signal_name")
        .agg(
            fired_count=("signal_name", "count"),
            avg_contribution=("weighted_contribution", "mean"),
        )
    )
    rates = (
        fired_agg.join(signal_total)
        .assign(pct=lambda x: (x["fired_count"] / x["total"] * 100).round(1))
        .sort_values("fired_count", ascending=False)
    )

    L("| Signal | Fired | Total | % | Avg Contribution |")
    L("|--------|-------|-------|---|------------------|")
    for sig, row in rates.iterrows():
        L(
            f"| {sig} | {row['fired_count']:.0f} | {row['total']:.0f} "
            f"| {row['pct']:.0f}% | {row['avg_contribution']:.3f} |"
        )
    L()

    # --- Global Signals ---
    L("## Global Signals")
    L()
    strategy_level = df[df["node_id"].fillna("") == ""]
    globals_found: list[str] = []
    for signal in strategy_level["signal_name"].unique():
        signal_df = strategy_level[strategy_level["signal_name"] == signal][
            ["turn_number", "strategy", "signal_value"]
        ]
        turn_variance = signal_df.groupby("turn_number")["signal_value"].nunique()
        if (turn_variance == 1).all() and len(turn_variance) > 0:
            globals_found.append(signal)

    if globals_found:
        for g in globals_found:
            L(f"- `{g}`")
    else:
        L("None detected.")
    L()

    # --- Dead Signals ---
    L("## Dead Signals")
    L()
    signal_totals = df.groupby("signal_name").agg(
        total_contribution=("weighted_contribution", "sum"),
        max_weight=("signal_weight", lambda x: x.abs().max()),
    )
    dead = signal_totals[
        (signal_totals["total_contribution"] == 0) & (signal_totals["max_weight"] > 0)
    ]
    if not dead.empty:
        L("| Signal | Max Weight |")
        L("|--------|-----------|")
        for sig, row in dead.iterrows():
            L(f"| {sig} | {row['max_weight']:.2f} |")
    else:
        L("None detected.")
    L()

    # --- Always-Firing Signals ---
    L("## Always-Firing Signals (>80%)")
    L()
    always = rates[rates["pct"] > 80]
    if not always.empty:
        L("| Signal | Fired | Total | % |")
        L("|--------|-------|-------|---|")
        for sig, row in always.iterrows():
            L(
                f"| {sig} | {row['fired_count']:.0f} | {row['total']:.0f} "
                f"| {row['pct']:.0f}% |"
            )
    else:
        L("None detected.")
    L()

    # --- Phase Multiplier Differential ---
    L("## Phase Multiplier Differential")
    L()
    winner = (
        df[df["selected"] & (df["rank"] == 1)][
            [
                "turn_number",
                "phase",
                "strategy",
                "node_id",
                "phase_multiplier",
                "base_score",
                "final_score",
            ]
        ]
        .drop_duplicates(subset=["turn_number"])
        .copy()
    )
    runner_up = (
        df[df["rank"] == 2][
            [
                "turn_number",
                "strategy",
                "node_id",
                "phase_multiplier",
                "base_score",
                "final_score",
            ]
        ]
        .drop_duplicates(subset=["turn_number"])
        .copy()
    )
    if not winner.empty and not runner_up.empty:
        merged = winner.merge(
            runner_up, on="turn_number", suffixes=("_winner", "_runner")
        )
        merged["multiplier_effect"] = (
            merged["phase_multiplier_winner"] - merged["phase_multiplier_runner"]
        ) * merged["base_score_winner"]
        widened = int((merged["multiplier_effect"] > 0.1).sum())
        total = len(merged)
        L(f"Gap widened by multiplier: {widened}/{total} turns")
        L()
        L(
            "| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |"
        )
        L(
            "|------|-------|--------|-----------|-------------------|---------------------|--------|"
        )
        for _, row in merged.iterrows():
            L(
                f"| {row['turn_number']:.0f} | {row['phase']} | {row['strategy_winner']} "
                f"| {row['strategy_runner']} | {row['phase_multiplier_winner']:.2f} "
                f"| {row['phase_multiplier_runner']:.2f} | {row['multiplier_effect']:.3f} |"
            )
    else:
        L("Insufficient data (need both winner and runner-up per turn).")
    L()

    # --- Signal Budget Decomposition ---
    L("## Signal Budget Decomposition")
    L()
    budget = (
        df.groupby(["strategy", df["weighted_contribution"] > 0])
        .agg(total_contribution=("weighted_contribution", "sum"))
        .unstack(fill_value=0)
    )
    budget.columns = ["negative_mass", "positive_mass"]
    budget["net"] = budget["positive_mass"] + budget["negative_mass"]
    budget = budget.sort_values("net", ascending=False)

    L("| Strategy | Positive Mass | Negative Mass | Net |")
    L("|----------|--------------|--------------|-----|")
    for strategy, row in budget.iterrows():
        L(
            f"| {strategy} | {row['positive_mass']:.3f} | {row['negative_mass']:.3f} "
            f"| {row['net']:.3f} |"
        )
    L()

    # --- Node Selection Frequency ---
    L("## Node Selection Frequency")
    L()
    node_wins = (
        df[df["selected"] & (df["rank"] == 1)]
        .groupby(["node_id", "node_label"])["turn_number"]
        .nunique()
        .sort_values(ascending=False)
    )
    if len(node_wins):
        L("| Node Label | Node ID | Turns Selected |")
        L("|------------|---------|----------------|")
        for (nid, label), count in node_wins.head(10).items():
            short_id = nid[:8] if nid else "—"
            L(f"| {label or '—'} | {short_id} | {count} |")
    else:
        L("No node-level selections found.")
    L()

    # --- Gate Analysis ---
    L("## Gate Analysis")
    L()
    if not gated.empty:
        gate_summary = (
            gated.groupby(["strategy", "gate_signal"])
            .agg(
                nodes_gated=("node_id", "nunique"),
                turns_affected=("turn_number", "nunique"),
            )
            .sort_values("nodes_gated", ascending=False)
        )
        L("| Strategy | Gate Signal | Nodes Gated | Turns Affected |")
        L("|----------|-------------|-------------|----------------|")
        for (strategy, gate_signal), row in gate_summary.iterrows():
            L(
                f"| {strategy} | {gate_signal} | {row['nodes_gated']:.0f} "
                f"| {row['turns_affected']:.0f} |"
            )
    else:
        L("No gated pairs — all strategies eligible for all nodes.")
    L()

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate scoring summary markdown from decomposition CSV."
    )
    parser.add_argument("csv_file", type=Path, help="Path to scoring CSV file")
    parser.add_argument(
        "-o", "--output", type=Path, help="Output markdown path (default: stdout)"
    )
    args = parser.parse_args()

    if not args.csv_file.exists():
        print(f"File not found: {args.csv_file}", file=sys.stderr)
        sys.exit(1)

    summary = generate_summary(args.csv_file)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(summary)
        print(f"Summary written to: {args.output}", file=sys.stderr)
    else:
        print(summary)


if __name__ == "__main__":
    main()
