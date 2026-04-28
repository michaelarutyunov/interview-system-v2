"""Generate simulation review reports from JSON + CSV artifacts.

Reads a simulation JSON and its companion _scoring.csv to produce a markdown
review with strategy distribution, graph health, signal diagnostics, and gate
analysis. Uses the current signal taxonomy (convgraph.*, response.semantic.llm.*,
meta.saturation.*, interview.*).

Usage:
    # Single run
    uv run python scripts/reporting/generate_reviews.py synthetic_interviews/20260424_*.json

    # All runs in a directory
    uv run python scripts/reporting/generate_reviews.py synthetic_interviews/*.json

    # Explicit output directory
    uv run python scripts/reporting/generate_reviews.py synthetic_interviews/*.json -o reviews/
"""

import json
import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path("synthetic_interviews")


def _to_float(val: object) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def analyze_run(json_path: Path, output_dir: Path | None = None) -> dict:
    csv_path = json_path.with_name(json_path.stem + "_scoring.csv")
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"review_{json_path.stem}.md"
    else:
        out_path = json_path.with_name(f"review_{json_path.stem}.md")

    with open(json_path) as f:
        data = json.load(f)

    meta = data.get("metadata", {})
    methodology = meta.get("methodology", "unknown")
    turns = data["turns"]
    signals_turns = [t for t in turns if t.get("signals")]

    # --- Part 1: Strategy distribution ---
    strategy_counts: dict[str, int] = {}
    for t in turns:
        s = t.get("strategy_selected") or "—"
        strategy_counts[s] = strategy_counts.get(s, 0) + 1

    # --- Part 2: Signal table ---
    signal_rows = []
    for t in signals_turns:
        s = t["signals"]
        alts = [
            a
            for a in t.get("strategy_alternatives", [])
            if _to_float(a.get("score")) is not None
        ]
        top2 = alts[:2]
        scores = " / ".join(f"{_to_float(x['score']):.2f}" for x in top2 if x)
        signal_rows.append(
            {
                "turn": t["turn_number"],
                "phase": s.get("interview.phase", "—"),
                "engagement": s.get("response.semantic.llm.engagement", "—"),
                "certainty": s.get("response.semantic.llm.certainty", "—"),
                "response_depth": s.get("response.semantic.llm.response_depth", "—"),
                "engagement_trend": s.get(
                    "response.semantic.llm.engagement.trend", "—"
                ),
                "strategy": t.get("strategy_selected", "—"),
                "top_scores": scores,
            }
        )

    # Strategy distribution table
    total_turns = len(signals_turns)
    strat_dist = []
    for s, c in sorted(strategy_counts.items(), key=lambda x: -x[1]):
        strat_dist.append(f"| {s:20} | {c:3} | {c / total_turns * 100:5.1f}% |")

    # Streaks
    streaks = []
    last_s = None
    streak = 0
    for t in signals_turns:
        s = t.get("strategy_selected")
        if s == last_s:
            streak += 1
        else:
            if streak >= 4:
                streaks.append(f"- {last_s}: {streak} consecutive turns")
            streak = 1
            last_s = s
    if streak >= 4:
        streaks.append(f"- {last_s}: {streak} consecutive turns")

    # --- Part 3: Graph health ---
    nodes_traj = [
        s.get("convgraph.state.node.count", 0)
        for t in signals_turns
        if (s := t.get("signals", {}))
    ]
    orphans_traj = [
        s.get("convgraph.state.node.orphan_count", 0)
        for t in signals_turns
        if (s := t.get("signals", {}))
    ]
    g = data["graph"]["summary"]
    c = data["canonical_graph"]["summary"]
    final_orphans = orphans_traj[-1] if orphans_traj else 0
    surf_density = g["total_edges"] / g["total_nodes"] if g["total_nodes"] else 0
    can_density = c["total_edges"] / c["total_slots"] if c["total_slots"] else 0
    compression = c["total_slots"] / g["total_nodes"] * 100 if g["total_nodes"] else 0

    # --- Part 4: CSV analysis (if scoring CSV exists) ---
    csv_lines: list[str] = []
    rates = None
    globals_: list[str] = []
    dead = None
    always = None
    gap_widened = 0
    gap_total = 0
    top_node = (None, None)
    top_node_turns = 0
    budget = None

    if csv_path.exists():
        df_raw = pd.read_csv(csv_path)
        gated = df_raw[df_raw["gated"].astype(str).isin(["True", "1"])]
        df = df_raw[~df_raw["gated"].astype(str).isin(["True", "1"])].copy()

        df["fired"] = df["signal_value"].astype(str).isin(["True", "1"]) | (
            pd.to_numeric(df["signal_value"], errors="coerce").fillna(0) > 0
        )

        signal_total_rows = df.groupby("signal_name").size().rename("total")
        fired_agg = (
            df[df["fired"]]
            .groupby("signal_name")
            .agg(
                fired_count=("signal_name", "count"),
                avg_contribution=("weighted_contribution", "mean"),
            )
        )
        rates = (
            fired_agg.join(signal_total_rows)
            .assign(pct=lambda x: (x["fired_count"] / x["total"] * 100).round(1))
            .sort_values("fired_count", ascending=False)
        )

        # Global signals (same value across all strategies in a turn)
        strategy_level = df[df["node_id"].fillna("") == ""]
        for signal in strategy_level["signal_name"].unique():
            signal_df = strategy_level[strategy_level["signal_name"] == signal][
                ["turn_number", "strategy", "signal_value"]
            ]
            turn_variance = signal_df.groupby("turn_number")["signal_value"].nunique()
            if (turn_variance == 1).all() and len(turn_variance) > 0:
                globals_.append(signal)

        # Dead signals
        signal_totals = df.groupby("signal_name").agg(
            total_contribution=("weighted_contribution", "sum"),
            max_weight=("signal_weight", lambda x: x.abs().max()),
        )
        dead = signal_totals[
            (signal_totals["total_contribution"] == 0)
            & (signal_totals["max_weight"] > 0)
        ]

        # Always firing
        always = rates[rates["pct"] > 80] if rates is not None else None

        # Phase multiplier gap
        winner = df[df["selected"] & (df["rank"] == 1)][
            [
                "turn_number",
                "phase",
                "strategy",
                "node_id",
                "phase_multiplier",
                "base_score",
                "final_score",
            ]
        ].drop_duplicates(subset=["turn_number"])
        runner_up = df[df["rank"] == 2][
            [
                "turn_number",
                "strategy",
                "node_id",
                "phase_multiplier",
                "base_score",
                "final_score",
            ]
        ].drop_duplicates(subset=["turn_number"])
        if not winner.empty and not runner_up.empty:
            merged = winner.merge(
                runner_up, on="turn_number", suffixes=("_winner", "_runner")
            )
            merged["multiplier_effect"] = (
                merged["phase_multiplier_winner"] - merged["phase_multiplier_runner"]
            ) * merged["base_score_winner"]
            gap_widened = int((merged["multiplier_effect"] > 0.1).sum())
            gap_total = len(merged)

        # Budget decomposition
        budget = (
            df.groupby(["strategy", df["weighted_contribution"] > 0])
            .agg(total_contribution=("weighted_contribution", "sum"))
            .unstack(fill_value=0)
        )
        budget.columns = ["negative_mass", "positive_mass"]
        budget["net"] = budget["positive_mass"] + budget["negative_mass"]
        budget = budget.sort_values("net", ascending=False)

        # Node wins
        node_wins = (
            df[df["selected"] & (df["rank"] == 1)]
            .groupby(["node_id", "node_label"])["turn_number"]
            .nunique()
            .sort_values(ascending=False)
        )
        if len(node_wins):
            top_node = node_wins.index[0]
            top_node_turns = int(node_wins.iloc[0])

        # Gate analysis
        if not gated.empty:
            gate_summary = (
                gated.groupby(["strategy", "gate_signal"])
                .agg(
                    nodes_gated=("node_id", "nunique"),
                    turns_affected=("turn_number", "nunique"),
                )
                .sort_values("nodes_gated", ascending=False)
            )
            for (strategy, gate_signal), row in gate_summary.iterrows():
                csv_lines.append(
                    f"| {strategy:20} | {gate_signal:25} | {row['nodes_gated']:4} | {row['turns_affected']:4} |"
                )
        else:
            csv_lines.append("No gated pairs — all strategies eligible for all nodes")
    else:
        csv_lines.append(f"No scoring CSV found at {csv_path}")

    # --- Build markdown ---
    lines = []
    lines.append(f"# Simulation Review: {methodology} ({json_path.stem})")
    lines.append("")
    lines.append("## Strategy Distribution")
    lines.append("| Strategy               | Count |  %    |")
    lines.append("|------------------------|-------|-------|")
    lines.extend(strat_dist)
    lines.append("")
    if streaks:
        lines.append("**Streaks:**")
        lines.extend(streaks)
    else:
        lines.append("**Streaks:** None >= 4 consecutive turns.")
    lines.append("")
    lines.append("## Graph Health")
    lines.append(f"- Node growth: {'→'.join(str(n) for n in nodes_traj)}")
    lines.append(f"- Orphan trajectory: {'→'.join(str(o) for o in orphans_traj)}")
    lines.append(
        f"- Surface: {g['total_nodes']} nodes, {g['total_edges']} edges, "
        f"density={surf_density:.2f}, orphans={final_orphans} "
        f"({final_orphans / g['total_nodes'] * 100:.1f}%)"
    )
    lines.append(
        f"- Canonical: {c['total_slots']} slots, {c['total_edges']} edges, "
        f"density/slot={can_density:.1f}, compression={compression:.0f}%"
    )
    lines.append(f"- Nodes by type: {g['nodes_by_type']}")
    lines.append("")

    if rates is not None:
        lines.append("## CSV Diagnostics")
        lines.append("")
        lines.append("### Top Firing Signals")
        lines.append(
            "| Signal                              | Fired  | %   | Avg Contribution |"
        )
        lines.append(
            "|-------------------------------------|--------|-----|------------------|"
        )
        for sig, row in rates.head(10).iterrows():
            lines.append(
                f"| {sig:35} | {row['fired_count']:.0f}/{row['total']:.0f} "
                f"| {row['pct']:.0f}% | {row['avg_contribution']:.3f}          |"
            )
        lines.append("")

        lines.append("### Global Signals")
        if globals_:
            lines.extend(f"- `{g}`" for g in globals_)
        else:
            lines.append("None detected.")
        lines.append("")

        lines.append("### Dead Signals")
        if dead is not None and not dead.empty:
            for sig, row in dead.iterrows():
                lines.append(f"- `{sig}` (max_weight={row['max_weight']:.2f})")
        else:
            lines.append("None detected.")
        lines.append("")

        lines.append("### Always-Firing Signals (>80%)")
        if always is not None and not always.empty:
            for sig, row in always.iterrows():
                lines.append(f"- `{sig}` ({row['pct']:.0f}%)")
        else:
            lines.append("None detected.")
        lines.append("")

        lines.append(
            f"### Phase Multiplier Gap Widened: {gap_widened}/{gap_total} turns"
        )
        lines.append("")

        lines.append("### Top Node Selection")
        if top_node[0]:
            lines.append(
                f"- `{top_node[1]}` ({top_node[0][:8]}): selected {top_node_turns} turns"
            )
        lines.append("")
    else:
        lines.append("## CSV Diagnostics")
        lines.append("")
        lines.append("*No scoring CSV available for this run.*")
        lines.append("")

    lines.append("### Gate Analysis")
    lines.extend(csv_lines)

    out_path.write_text("\n".join(lines))
    print(f"Review saved to: {out_path}")

    return {
        "method": methodology,
        "stem": json_path.stem,
        "total_turns": total_turns,
        "strategy_counts": strategy_counts,
        "streaks": streaks,
        "nodes_traj": nodes_traj,
        "orphans_traj": orphans_traj,
        "surface_density": surf_density,
        "canonical_density": can_density,
        "compression": compression,
        "final_nodes": g["total_nodes"],
        "final_edges": g["total_edges"],
        "final_orphans": final_orphans,
        "nodes_by_type": g["nodes_by_type"],
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate simulation review reports from JSON + CSV artifacts."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="One or more simulation JSON files (or globs expanded by shell).",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for review output files (default: same dir as JSON).",
    )
    args = parser.parse_args()

    results = []
    for path in args.inputs:
        if not path.exists():
            print(f"SKIP: {path} not found", file=sys.stderr)
            continue
        print(f"Analyzing {path.name} ...")
        try:
            results.append(analyze_run(path, args.output_dir))
        except Exception as e:
            print(f"ERROR: {path.name}: {e}", file=sys.stderr)

    if results and len(results) > 1:
        summary_path = (
            args.output_dir or args.inputs[0].parent
        ) / "review_summary.json"
        with open(summary_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nSummary saved to: {summary_path}")


if __name__ == "__main__":
    main()
