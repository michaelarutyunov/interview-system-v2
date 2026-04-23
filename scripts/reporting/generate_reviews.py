import json
import pandas as pd
from pathlib import Path

BASE_DIR = Path("/home/mikhailarutyunov/projects/interview-system-v2/synthetic_interviews")

runs = [
    ("20260415_073616_coffee_subscription_cjm_baseline_cooperative", "CJM"),
    ("20260415_073210_plant_milk_comparison_rg_baseline_cooperative", "RG"),
    ("20260415_072701_cold_brew_discovery_cit_baseline_cooperative", "CIT"),
    ("20260415_000720_glp1_food_jtbd_baseline_cooperative", "JTBD"),
    ("20260415_000322_glp1_food_mec_strict_baseline_cooperative", "MEC"),
]

def analyze_run(stem, method):
    json_path = BASE_DIR / f"{stem}.json"
    csv_path = BASE_DIR / f"{stem}_scoring.csv"
    out_path = BASE_DIR / f"review_{stem}.md"

    with open(json_path) as f:
        data = json.load(f)

    turns = data["turns"]
    signals_turns = [t for t in turns if t.get("signals")]

    # --- Part 1: Transcript summary ---
    strategy_counts = {}
    for t in turns:
        s = t.get("strategy_selected", "—")
        strategy_counts[s] = strategy_counts.get(s, 0) + 1

    # --- Part 2: Signal table ---
    signal_rows = []
    for t in signals_turns:
        s = t["signals"]
        alts = [a for a in t.get("strategy_alternatives", []) if a.get("score") not in (None, "score", "")]
        top2 = alts[:2]
        scores = " / ".join(f'{float(x["score"]):.2f}' for x in top2)
        signal_rows.append({
            "turn": t["turn_number"],
            "phase": s.get("meta.interview.phase", "—"),
            "depth": s.get("llm.response_depth", "—"),
            "eng": s.get("llm.engagement", "—"),
            "val": s.get("llm.valence", "—"),
            "spc": s.get("llm.specificity", "—"),
            "cert": s.get("llm.certainty", "—"),
            "trend": s.get("llm.global_response_trend", "—"),
            "strategy": t.get("strategy_selected", "—"),
            "top_scores": scores,
        })

    # Strategy distribution
    total_turns = len(signals_turns)
    strat_dist = []
    for s, c in sorted(strategy_counts.items(), key=lambda x: -x[1]):
        s_name = s or "—"
        strat_dist.append(f"| {s_name:20} | {c:3} | {c/total_turns*100:5.1f}% |")

    # Check streaks
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
    nodes_traj = [t["signals"]["graph.node_count"] for t in signals_turns]
    orphans_traj = [t["signals"]["graph.orphan_count"] for t in signals_turns]
    g = data["graph"]["summary"]
    c = data["canonical_graph"]["summary"]
    final_orphans = orphans_traj[-1] if orphans_traj else 0
    surf_density = g["total_edges"] / g["total_nodes"] if g["total_nodes"] else 0
    can_density = c["total_edges"] / c["total_slots"] if c["total_slots"] else 0
    compression = c["total_slots"] / g["total_nodes"] * 100 if g["total_nodes"] else 0

    # --- Part 4: CSV analysis ---
    df_raw = pd.read_csv(csv_path)
    gated = df_raw[df_raw["gated"].astype(str).isin(["True", "1"])]
    df = df_raw[~df_raw["gated"].astype(str).isin(["True", "1"])]

    df["fired"] = df["signal_value"].astype(str).isin(["True", "1"]) | (
        pd.to_numeric(df["signal_value"], errors="coerce").fillna(0) > 0
    )

    signal_total_rows = df.groupby("signal_name").size().rename("total")
    fired_agg = (
        df[df["fired"]]
        .groupby("signal_name")
        .agg(fired_count=("signal_name", "count"), avg_contribution=("weighted_contribution", "mean"))
    )
    rates = fired_agg.join(signal_total_rows).assign(
        pct=lambda x: (x["fired_count"] / x["total"] * 100).round(1)
    ).sort_values("fired_count", ascending=False)

    # Global signals
    strategy_level = df[df["node_id"].fillna("") == ""]
    globals_ = []
    for signal in strategy_level["signal_name"].unique():
        signal_df = strategy_level[strategy_level["signal_name"] == signal][["turn_number", "strategy", "signal_value"]]
        turn_variance = signal_df.groupby("turn_number")["signal_value"].nunique()
        if (turn_variance == 1).all() and len(turn_variance) > 0:
            globals_.append(signal)

    # Dead signals
    signal_totals = df.groupby("signal_name").agg(
        total_contribution=("weighted_contribution", "sum"),
        max_weight=("signal_weight", lambda x: x.abs().max())
    )
    dead = signal_totals[(signal_totals["total_contribution"] == 0) & (signal_totals["max_weight"] > 0)]

    # Always firing
    always = rates[rates["pct"] > 80]

    # Phase multiplier diff
    winner = (
        df[df["selected"] & (df["rank"] == 1)]
        [["turn_number", "phase", "strategy", "node_id", "phase_multiplier", "base_score", "final_score"]]
        .drop_duplicates(subset=["turn_number"])
    )
    runner_up = (
        df[df["rank"] == 2]
        [["turn_number", "strategy", "node_id", "phase_multiplier", "base_score", "final_score"]]
        .drop_duplicates(subset=["turn_number"])
    )
    merged = winner.merge(runner_up, on="turn_number", suffixes=("_winner", "_runner"))
    merged["multiplier_effect"] = (merged["phase_multiplier_winner"] - merged["phase_multiplier_runner"]) * merged["base_score_winner"]
    gap_widened = (merged["multiplier_effect"] > 0.1).sum()

    # Budget decomposition
    budget = df.groupby(["strategy", df["weighted_contribution"] > 0]).agg(
        total_contribution=("weighted_contribution", "sum")
    ).unstack(fill_value=0)
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
    top_node = node_wins.index[0] if len(node_wins) else (None, None)
    top_node_turns = node_wins.iloc[0] if len(node_wins) else 0

    # Gate analysis
    gate_lines = []
    if not gated.empty:
        gate_summary = gated.groupby(["strategy", "gate_signal"]).agg(
            nodes_gated=("node_id", "nunique"),
            turns_affected=("turn_number", "nunique"),
        ).sort_values("nodes_gated", ascending=False)
        for (strategy, gate_signal), row in gate_summary.iterrows():
            gate_lines.append(f"| {strategy:20} | {gate_signal:25} | {row['nodes_gated']:4} | {row['turns_affected']:4} |")
    else:
        gate_lines.append("No gated pairs — all strategies eligible for all nodes")

    # Build markdown
    lines = []
    lines.append(f"# Simulation Review: {method} ({stem})")
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
    lines.append(f"- Surface: {g['total_nodes']} nodes, {g['total_edges']} edges, density={surf_density:.2f}, orphans={final_orphans} ({final_orphans/g['total_nodes']*100:.1f}%)")
    lines.append(f"- Canonical: {c['total_slots']} slots, {c['total_edges']} edges, density/slot={can_density:.1f}, compression={compression:.0f}%")
    lines.append(f"- Nodes by type: {g['nodes_by_type']}")
    lines.append("")
    lines.append("## CSV Diagnostics")
    lines.append("")
    lines.append("### Top Firing Signals")
    lines.append("| Signal                              | Fired  | %   | Avg Contribution |")
    lines.append("|-------------------------------------|--------|-----|------------------|")
    for sig, row in rates.head(10).iterrows():
        lines.append(f"| {sig:35} | {row['fired_count']:.0f}/{row['total']:.0f} | {row['pct']:.0f}% | {row['avg_contribution']:.3f}          |")
    lines.append("")
    lines.append("### Global Signals")
    if globals_:
        lines.extend(f"- `{g}`" for g in globals_)
    else:
        lines.append("None detected.")
    lines.append("")
    lines.append("### Dead Signals")
    if not dead.empty:
        for sig, row in dead.iterrows():
            lines.append(f"- `{sig}` (max_weight={row['max_weight']:.2f})")
    else:
        lines.append("None detected.")
    lines.append("")
    lines.append("### Always-Firing Signals (>80%)")
    if not always.empty:
        for sig, row in always.iterrows():
            lines.append(f"- `{sig}` ({row['pct']:.0f}%)")
    else:
        lines.append("None detected.")
    lines.append("")
    lines.append(f"### Phase Multiplier Gap Widened: {gap_widened}/{len(merged)} turns")
    lines.append("")
    lines.append("### Top Node Selection")
    if top_node[0]:
        lines.append(f"- `{top_node[1]}` ({top_node[0][:8]}): selected {top_node_turns} turns")
    lines.append("")
    lines.append("### Gate Analysis")
    if gate_lines[0].startswith("No gated"):
        lines.append(gate_lines[0])
    else:
        lines.append("| Strategy             | Gate Signal               | Nodes Gated | Turns Affected |")
        lines.append("|----------------------|---------------------------|-------------|----------------|")
        lines.extend(gate_lines)

    out_path.write_text("\n".join(lines))

    # Return summary dict
    return {
        "method": method,
        "stem": stem,
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
        "top_firing_signals": rates.head(5).to_dict(),
        "global_signals": globals_,
        "dead_signals": list(dead.index),
        "always_firing": list(always.index),
        "gap_widened": gap_widened,
        "gap_total": len(merged),
        "top_node": {"label": top_node[1], "turns": top_node_turns},
        "budget": budget.to_dict(),
    }


results = []
for stem, method in runs:
    print(f"Analyzing {method} ...")
    results.append(analyze_run(stem, method))

summary_path = BASE_DIR / "review_summary_20260415.json"
with open(summary_path, "w") as f:
    json.dump(results, f, indent=2, default=str)

print(f"Done. Saved summary to {summary_path}")
