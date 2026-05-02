#!/usr/bin/env python3
"""Edge extraction diff harness: compare flag OFF (baseline) vs ON (new path).

Produces a side-by-side markdown report comparing strategy distribution,
chain density, and stage timings between baseline (flag OFF) and new
(flag ON) runs.

Per D11: no hard latency threshold. Raw numbers are reported; human sets
the threshold after reviewing the report.

Usage:
    # Smoke test: one methodology, 5 turns
    uv run python scripts/diagnostics/edge_extraction_diff.py \\
        --concept coffee_jtbd_v2 --persona baseline_cooperative --max-turns 5

    # Full comparison: all 6 active methodologies
    uv run python scripts/diagnostics/edge_extraction_diff.py \\
        --all-methodologies --persona baseline_cooperative --max-turns 10
"""

import argparse
import asyncio
import statistics
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# Active methodology → concept mapping (one concept per methodology for baseline)
_METHODOLOGY_CONCEPTS: dict[str, str] = {
    "means_end_chain_v2_strict": "glp1_food_mec_strict",
    "means_end_chain_v3_flex": "glp1_food_mec_flex",
    "jobs_to_be_done_v2": "coffee_jtbd_v2",
    "critical_incident_v2": "zerofizz_beverage_cit",
    "customer_journey_mapping_v2": "zerofizz_beverage_cjm",
    "repertory_grid_v2": "plant_milk_comparison_rg",
}

# Methodology display names for reports
_METHODOLOGY_DISPLAY: dict[str, str] = {
    "means_end_chain_v2_strict": "MEC Strict",
    "means_end_chain_v3_flex": "MEC Flex",
    "jobs_to_be_done_v2": "JTBD",
    "critical_incident_v2": "CIT",
    "customer_journey_mapping_v2": "CJM",
    "repertory_grid_v2": "Repertory Grid",
}


def _set_feature_flag(enabled: bool) -> None:
    """Monkey-patch the edge extraction feature flag in the loaded config."""
    from src.core.config import interview_config

    interview_config.features.enable_edge_extraction_stage = enabled


async def _run_one_simulation(
    concept_id: str,
    persona_id: str,
    max_turns: int,
    flag_enabled: bool,
) -> dict[str, Any]:
    """Run a single simulation and return structured metrics.

    Monkey-patches the feature flag before creating the session service,
    so the pipeline picks up the correct flag state.
    """
    import aiosqlite

    from src.core.config import settings
    from src.core.logging import configure_logging
    from src.api.dependencies import (
        get_shared_extraction_client,
        get_shared_generation_client,
    )
    from src.persistence.repositories.session_repo import SessionRepository
    from src.persistence.repositories.graph_repo import GraphRepository
    from src.services.session_service import SessionService
    from src.services.simulation_service import SimulationService

    configure_logging()

    _set_feature_flag(flag_enabled)

    db = await aiosqlite.connect(str(settings.database_path))
    try:
        session_repo = SessionRepository(str(settings.database_path))
        graph_repo = GraphRepository(db)

        session_service = SessionService(
            session_repo=session_repo,
            graph_repo=graph_repo,
            extraction_llm_client=get_shared_extraction_client(),
            generation_llm_client=get_shared_generation_client(),
        )

        simulation_service = SimulationService(session_service=session_service)

        result = await simulation_service.simulate_interview(
            concept_id=concept_id,
            persona_id=persona_id,
            max_turns=max_turns,
        )
    finally:
        await db.close()

    return _extract_metrics(result, flag_enabled)


def _extract_metrics(result: Any, flag_enabled: bool) -> dict[str, Any]:
    """Extract comparison metrics from a SimulationResult."""
    turns = result.turns

    # Strategy distribution
    strategy_counts: Counter[str] = Counter()
    for turn in turns:
        strategy_counts[turn.strategy_selected or "unknown"] += 1

    # Chain density
    total_nodes = len(result.nodes)
    total_edges = len(result.edges)
    edge_node_ratio = total_edges / max(total_nodes, 1)

    # Chain-relevant edges
    chain_relevant_count = 0
    for edge in result.edges:
        if edge.get("edge_type") in (
            "leads_to",
            "triggers",
            "addresses",
            "enables",
            "supports",
            "implies",
            "causes",
            "results_in",
        ):
            chain_relevant_count += 1
    chain_edge_ratio = chain_relevant_count / max(total_edges, 1)

    # Per-stage timings
    stage_timings: dict[str, list[float]] = {}
    for turn in turns:
        if turn.stage_timings:
            for stage_name, ms in turn.stage_timings.items():
                if stage_name not in stage_timings:
                    stage_timings[stage_name] = []
                stage_timings[stage_name].append(ms)

    # Stage timing summaries
    stage_summaries: dict[str, dict[str, float]] = {}
    for stage_name, values in stage_timings.items():
        sorted_vals = sorted(values)
        stage_summaries[stage_name] = {
            "p50": _percentile(sorted_vals, 50),
            "p90": _percentile(sorted_vals, 90),
            "mean": statistics.mean(values),
            "min": min(values),
            "max": max(values),
        }

    # Total turn latency (sum of all stage timings per turn)
    # Note: SimulationTurn.latency_ms is synthetic responder latency, not pipeline.
    turn_latencies: list[float] = []
    for turn in turns:
        if turn.stage_timings:
            total = sum(turn.stage_timings.values())
            if total > 0:
                turn_latencies.append(total)
    turn_latencies.sort()

    return {
        "flag": "ON" if flag_enabled else "OFF",
        "total_turns": result.total_turns,
        "strategy_distribution": dict(strategy_counts),
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "edge_node_ratio": round(edge_node_ratio, 3),
        "chain_relevant_edges": chain_relevant_count,
        "chain_edge_ratio": round(chain_edge_ratio, 3),
        "stage_summaries": stage_summaries,
        "latency_p50": _percentile(turn_latencies, 50) if turn_latencies else 0,
        "latency_p90": _percentile(turn_latencies, 90) if turn_latencies else 0,
        "latency_mean": statistics.mean(turn_latencies) if turn_latencies else 0,
    }


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Compute percentile from sorted list."""
    if not sorted_values:
        return 0.0
    idx = int(len(sorted_values) * pct / 100.0)
    idx = min(idx, len(sorted_values) - 1)
    return sorted_values[idx]


def _generate_markdown_report(
    baseline: dict[str, Any],
    new: dict[str, Any],
    methodology: str,
    concept_id: str,
    persona_id: str,
) -> str:
    """Generate a side-by-side markdown comparison report."""
    display = _METHODOLOGY_DISPLAY.get(methodology, methodology)

    lines: list[str] = []
    lines.append("# Edge Extraction Diff Report")
    lines.append("")
    lines.append(f"**Methodology:** {display} (`{methodology}`)  ")
    lines.append(f"**Concept:** `{concept_id}`  ")
    lines.append(f"**Persona:** `{persona_id}`  ")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}  ")
    lines.append("")

    # Summary table
    lines.append("## Summary Metrics")
    lines.append("")
    lines.append("| Metric | Baseline (OFF) | New (ON) | Delta |")
    lines.append("|--------|---------------|----------|-------|")

    for metric, label, fmt in [
        ("total_turns", "Total Turns", "d"),
        ("total_nodes", "Total Nodes", "d"),
        ("total_edges", "Total Edges", "d"),
        ("edge_node_ratio", "Edge/Node Ratio", ".3f"),
        ("chain_relevant_edges", "Chain-Relevant Edges", "d"),
        ("chain_edge_ratio", "Chain Edge Ratio", ".3f"),
    ]:
        b_val = baseline[metric]
        n_val = new[metric]
        if fmt == "d":
            delta = f"{n_val - b_val:+d}"
        else:
            delta = f"{n_val - b_val:+.3f}"
        lines.append(f"| {label} | {b_val:{fmt}} | {n_val:{fmt}} | {delta} |")

    # Latency
    lines.append("")
    lines.append("## Latency (ms)")
    lines.append("")
    lines.append("| Metric | Baseline (OFF) | New (ON) | Delta |")
    lines.append("|--------|---------------|----------|-------|")
    for metric, label in [
        ("latency_p50", "P50 Turn Latency"),
        ("latency_p90", "P90 Turn Latency"),
        ("latency_mean", "Mean Turn Latency"),
    ]:
        b_val = baseline[metric]
        n_val = new[metric]
        delta = n_val - b_val
        lines.append(f"| {label} | {b_val:.0f} | {n_val:.0f} | {delta:+.0f} |")

    # Stage timings
    all_stages = set(baseline["stage_summaries"]) | set(new["stage_summaries"])
    if all_stages:
        lines.append("")
        lines.append("## Per-Stage Timing (P50 ms)")
        lines.append("")
        lines.append("| Stage | Baseline (OFF) | New (ON) | Delta |")
        lines.append("|-------|---------------|----------|-------|")
        for stage in sorted(all_stages):
            b_p50 = baseline["stage_summaries"].get(stage, {}).get("p50", 0)
            n_p50 = new["stage_summaries"].get(stage, {}).get("p50", 0)
            delta = n_p50 - b_p50
            lines.append(f"| {stage} | {b_p50:.1f} | {n_p50:.1f} | {delta:+.1f} |")

    # Strategy distribution
    lines.append("")
    lines.append("## Strategy Distribution")
    lines.append("")
    lines.append("| Strategy | Baseline (OFF) | New (ON) | Delta |")
    lines.append("|----------|---------------|----------|-------|")
    all_strategies = set(baseline["strategy_distribution"]) | set(
        new["strategy_distribution"]
    )
    for strategy in sorted(all_strategies):
        b_count = baseline["strategy_distribution"].get(strategy, 0)
        n_count = new["strategy_distribution"].get(strategy, 0)
        delta = n_count - b_count
        lines.append(f"| {strategy} | {b_count} | {n_count} | {delta:+d} |")

    return "\n".join(lines)


async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Edge extraction diff harness: compare flag OFF vs ON."
    )
    parser.add_argument(
        "--concept",
        default=None,
        help="Concept ID for single-methodology run",
    )
    parser.add_argument(
        "--persona",
        default="baseline_cooperative",
        help="Persona ID (default: baseline_cooperative)",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=10,
        help="Max turns (default: 10)",
    )
    parser.add_argument(
        "--all-methodologies",
        action="store_true",
        help="Run all 6 active methodologies",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: reports/edge_extraction_diff/<timestamp>/)",
    )
    args = parser.parse_args()

    if not args.all_methodologies and not args.concept:
        parser.error("Must specify --concept or --all-methodologies")

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_dir = Path("reports") / "edge_extraction_diff" / ts
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build run list
    runs: list[tuple[str, str]] = []
    if args.all_methodologies:
        for methodology, concept_id in _METHODOLOGY_CONCEPTS.items():
            runs.append((methodology, concept_id))
    else:
        # Resolve methodology from concept config
        concept_config_path = Path("config") / "concepts" / f"{args.concept}.yaml"
        if not concept_config_path.exists():
            print(f"Error: concept config not found: {concept_config_path}")
            sys.exit(1)
        import yaml

        with open(concept_config_path) as f:
            concept_config = yaml.safe_load(f)
        methodology = concept_config.get("methodology", "unknown")
        runs.append((methodology, args.concept))

    all_reports: list[str] = []

    for methodology, concept_id in runs:
        display = _METHODOLOGY_DISPLAY.get(methodology, methodology)
        print(f"\n{'=' * 60}")
        print(f"Running: {display} ({methodology})")
        print(f"  Concept: {concept_id}")
        print(f"  Persona: {args.persona}")
        print(f"  Max turns: {args.max_turns}")
        print(f"{'=' * 60}")

        print("  Baseline (flag OFF)...", end=" ", flush=True)
        t0 = time.perf_counter()
        baseline = await _run_one_simulation(
            concept_id, args.persona, args.max_turns, flag_enabled=False
        )
        print(f"done ({time.perf_counter() - t0:.1f}s)")

        print("  New path (flag ON)...", end=" ", flush=True)
        t0 = time.perf_counter()
        new = await _run_one_simulation(
            concept_id, args.persona, args.max_turns, flag_enabled=True
        )
        print(f"done ({time.perf_counter() - t0:.1f}s)")

        report = _generate_markdown_report(
            baseline, new, methodology, concept_id, args.persona
        )

        # Write report
        safe_name = methodology.replace("/", "_")
        report_path = output_dir / f"{safe_name}.md"
        report_path.write_text(report)
        all_reports.append(str(report_path))

        # Print quick summary
        print(f"\n  Quick summary for {display}:")
        print(
            f"    Edges: {baseline['total_edges']} → {new['total_edges']} "
            f"({new['total_edges'] - baseline['total_edges']:+d})"
        )
        print(
            f"    Chain-relevant: {baseline['chain_relevant_edges']} → "
            f"{new['chain_relevant_edges']} "
            f"({new['chain_relevant_edges'] - baseline['chain_relevant_edges']:+d})"
        )
        print(
            f"    P50 latency: {baseline['latency_p50']:.0f}ms → "
            f"{new['latency_p50']:.0f}ms "
            f"({new['latency_p50'] - baseline['latency_p50']:+.0f}ms)"
        )
        print(f"    Report: {report_path}")

    # Write index
    index_path = output_dir / "index.md"
    index_lines = [
        "# Edge Extraction Diff Reports",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}  ",
        f"**Persona:** `{args.persona}`  ",
        f"**Max turns:** {args.max_turns}  ",
        "",
        "## Reports",
        "",
    ]
    for path in all_reports:
        name = Path(path).stem
        index_lines.append(f"- [{name}]({Path(path).name})")
    index_path.write_text("\n".join(index_lines))

    print(f"\n{'=' * 60}")
    print(f"All reports saved to: {output_dir}")
    print(f"Index: {index_path}")


if __name__ == "__main__":
    asyncio.run(_main())
