"""Eval harness: display aggregated scoreboard with CI and delta-vs-baseline.

Usage:
    uv run python scripts/show_scoreboard.py --methodology mec
    uv run python scripts/show_scoreboard.py --config-hash abc123 --compare-to def456
    uv run python scripts/show_scoreboard.py --label mec_baseline_2026_04
"""

import argparse
import math
import sqlite3
from pathlib import Path

DB_PATH = str(Path(__file__).parent.parent / "data" / "interview.db")

METRIC_COLUMNS = [
    "structural_completeness",
    "ontology_breadth",
    "exploration_depth",
    "node_count",
    "orphan_ratio",
    "canonical_slot_coverage",
    "total_turns",
]


def query_runs(
    db_path: str,
    methodology: str | None = None,
    config_hash: str | None = None,
    label: str | None = None,
) -> list[dict]:
    """Fetch eval runs matching filters."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    conditions = ["error_flag = 0"]
    params: list[str] = []

    if methodology:
        conditions.append("methodology = ?")
        params.append(methodology)
    if config_hash:
        conditions.append("config_hash = ?")
        params.append(config_hash)
    if label:
        conditions.append("run_label = ?")
        params.append(label)

    where = " AND ".join(conditions)
    query = f"SELECT * FROM eval_runs WHERE {where} ORDER BY timestamp"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def compute_aggregates(runs: list[dict]) -> list[dict]:
    """Aggregate runs by (config_hash, persona_id). Returns list of summary dicts."""
    from collections import defaultdict

    groups: dict[tuple, list[dict]] = defaultdict(list)
    for run in runs:
        key = (run["config_hash"], run["persona_id"])
        groups[key].append(run)

    results = []
    for (ch, persona), group in sorted(groups.items()):
        n = len(group)
        agg = {
            "config_hash": ch,
            "persona_id": persona,
            "n": n,
            "label": group[0].get("run_label", ""),
        }
        for col in METRIC_COLUMNS:
            values = [r[col] for r in group if r.get(col) is not None]
            if not values:
                agg[f"{col}_mean"] = 0.0
                agg[f"{col}_std"] = 0.0
                agg[f"{col}_ci"] = 0.0
                continue
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / max(len(values) - 1, 1)
            std = math.sqrt(variance)
            ci = 1.96 * std / math.sqrt(len(values))
            agg[f"{col}_mean"] = mean
            agg[f"{col}_std"] = std
            agg[f"{col}_ci"] = ci
        results.append(agg)
    return results


def compute_config_aggregates(runs: list[dict]) -> list[dict]:
    """Aggregate runs by config_hash only (across all personas)."""
    from collections import defaultdict

    groups: dict[str, list[dict]] = defaultdict(list)
    for run in runs:
        groups[run["config_hash"]].append(run)

    results = []
    for ch, group in sorted(groups.items()):
        n = len(group)
        agg = {
            "config_hash": ch,
            "n": n,
            "label": group[0].get("run_label", ""),
        }
        for col in METRIC_COLUMNS:
            values = [r[col] for r in group if r.get(col) is not None]
            if not values:
                agg[f"{col}_mean"] = 0.0
                agg[f"{col}_std"] = 0.0
                agg[f"{col}_ci"] = 0.0
                continue
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / max(len(values) - 1, 1)
            std = math.sqrt(variance)
            ci = 1.96 * std / math.sqrt(len(values))
            agg[f"{col}_mean"] = mean
            agg[f"{col}_std"] = std
            agg[f"{col}_ci"] = ci
        results.append(agg)
    return results


def print_aggregates(aggregates: list[dict], baseline_agg: dict | None = None) -> None:
    """Pretty-print aggregated results as a table."""
    if not aggregates:
        print("No results found.")
        return

    # Header
    cols = ["label", "config_hash", "n"]
    for metric in [
        "structural_completeness",
        "exploration_depth",
        "ontology_breadth",
        "node_count",
    ]:
        cols.append(f"{metric}_mean")
        cols.append(f"{metric}_ci")
        if baseline_agg:
            cols.append(f"{metric}_delta")

    # Print header row
    header_parts = []
    for c in cols:
        if c.endswith("_mean"):
            short = c.replace("_mean", "")[:8]
            header_parts.append(f"{short:>8s}")
        elif c.endswith("_ci"):
            header_parts.append(f"{'±CI':>6s}")
        elif c.endswith("_delta"):
            header_parts.append(f"{'Δ':>7s}")
        else:
            header_parts.append(f"{c[:15]:>15s}")

    print("  ".join(header_parts))
    print("-" * len("  ".join(header_parts)))

    for agg in aggregates:
        row_parts = []
        for c in cols:
            if c.endswith("_mean"):
                val = agg.get(c, 0.0)
                row_parts.append(f"{val:8.2f}")
            elif c.endswith("_ci"):
                val = agg.get(c, 0.0)
                row_parts.append(f"±{val:4.2f}")
            elif c.endswith("_delta"):
                metric = c.replace("_delta", "_mean")
                val = agg.get(metric, 0.0)
                base_val = baseline_agg.get(metric, 0.0) if baseline_agg else 0.0
                delta = val - base_val
                sign = "+" if delta >= 0 else ""
                row_parts.append(f"{sign}{delta:6.2f}")
            elif c == "n":
                row_parts.append(f"{agg.get(c, 0):>15d}")
            else:
                row_parts.append(f"{str(agg.get(c, ''))[:15]:>15s}")
        print("  ".join(row_parts))


def print_config_registry(db_path: str) -> None:
    """Print all registered configs."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT config_hash, label, methodology, registered_at FROM eval_config_registry ORDER BY registered_at DESC"
    ).fetchall()
    conn.close()

    if not rows:
        print("No configs registered yet.")
        return

    print("\nRegistered configs:")
    print(f"  {'Hash':<18s} {'Label':<30s} {'Methodology':<30s} {'Registered':<20s}")
    print(f"  {'-' * 18} {'-' * 30} {'-' * 30} {'-' * 20}")
    for r in rows:
        print(
            f"  {r['config_hash']:<18s} {r['label']:<30s} {r['methodology']:<30s} {r['registered_at'][:19]:<20s}"
        )


def main():
    parser = argparse.ArgumentParser(description="Show eval scoreboard")
    parser.add_argument("--methodology", help="Filter by methodology")
    parser.add_argument("--config-hash", help="Filter by config hash")
    parser.add_argument("--label", help="Filter by config label")
    parser.add_argument(
        "--compare-to", help="Baseline config hash for delta comparison"
    )
    parser.add_argument(
        "--by-persona", action="store_true", help="Group by persona instead of config"
    )
    parser.add_argument(
        "--list-configs", action="store_true", help="List registered configs"
    )
    args = parser.parse_args()

    if args.list_configs:
        print_config_registry(DB_PATH)
        return

    runs = query_runs(
        DB_PATH,
        methodology=args.methodology,
        config_hash=args.config_hash,
        label=args.label,
    )

    if not runs:
        print("No matching runs found.")
        print_config_registry(DB_PATH)
        return

    baseline_agg = None
    if args.compare_to:
        baseline_runs = query_runs(DB_PATH, config_hash=args.compare_to)
        if baseline_runs:
            baseline_aggs = compute_config_aggregates(baseline_runs)
            if baseline_aggs:
                baseline_agg = baseline_aggs[0]
        else:
            print(f"Warning: no runs found for baseline hash {args.compare_to}")

    if args.by_persona:
        aggregates = compute_aggregates(runs)
    else:
        aggregates = compute_config_aggregates(runs)

    print(f"\nEval Scoreboard ({len(runs)} runs, {len(aggregates)} groups)")
    print("=" * 80)
    print_aggregates(aggregates, baseline_agg)

    if baseline_agg:
        print(
            f"\nBaseline: {baseline_agg.get('label', args.compare_to)} ({args.compare_to})"
        )


if __name__ == "__main__":
    main()
