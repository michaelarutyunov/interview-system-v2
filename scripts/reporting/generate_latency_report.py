#!/usr/bin/env python3
"""Analyze an interview log file for pipeline timing and LLM call metrics.

Produces structured output suitable for the interview export pipeline:
  - summary.md   — human-readable markdown report
  - llm_calls.csv — per-LLM-call data (model, tokens, latency, cost)
  - stages.csv    — per-stage timing data

Usage:
    # Analyze latest log (auto-detect)
    uv run python scripts/reporting/generate_latency_report.py

    # Analyze specific log file
    uv run python scripts/reporting/generate_latency_report.py --log-file logs/interview_20260424_183318.log

    # Write to specific output directory
    uv run python scripts/reporting/generate_latency_report.py --output-dir reports/interviews/20260424_183318/05_latency/
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path


# ── Pricing ───────────────────────────────────────────────────────────────────

# Pricing per million tokens (input, output)
# These are defaults; actual pricing comes from .env in production
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "kimi-k2-0905-preview": (0.60, 2.50),
    "kimi-k2": (0.60, 2.50),
}


def _calculate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Calculate cost in USD for a given model and token usage."""
    model_key = model
    for key in MODEL_PRICING:
        if key in model:
            model_key = key
            break

    if model_key not in MODEL_PRICING:
        return 0.0

    input_price, output_price = MODEL_PRICING[model_key]
    input_cost = (tokens_in / 1_000_000) * input_price
    output_cost = (tokens_out / 1_000_000) * output_price
    return input_cost + output_cost


# ── Utilities ─────────────────────────────────────────────────────────────────


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def _calc_stats(values: list[float]) -> dict[str, float]:
    """Calculate statistics for a list of values."""
    if not values:
        return {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0, "total": 0.0}
    return {
        "count": len(values),
        "mean": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
        "total": sum(values),
    }


def _find_latest_log(logs_dir: str = "logs") -> Path | None:
    """Find the most recent log file in the logs directory."""
    log_path = Path(logs_dir)
    if not log_path.exists():
        return None

    log_files = [
        f
        for f in log_path.iterdir()
        if f.is_file() and f.name.startswith("interview_") and f.name.endswith(".log")
    ]

    if not log_files:
        return None

    log_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return log_files[0]


# ── Analysis ──────────────────────────────────────────────────────────────────


def analyze_log(log_file: Path) -> dict:
    """Analyze a log file and return timing metrics."""
    pipeline_times: list[float] = []
    stage_times: dict[str, list[float]] = defaultdict(list)
    llm_calls: dict[str, dict] = {}

    # Regex patterns
    stage_completed_pattern = re.compile(
        r"stage_completed\s+duration_ms=([\d\.]+)\s+stage_name=(\S+)"
    )
    llm_completed_pattern = re.compile(
        r"llm_call_complete\s+.*?client_type=(\S+)"
        r".*?input_tokens=(\d+).*?latency_ms=([\d\.]+)"
        r".*?model=(\S+).*?output_tokens=(\d+)"
    )
    cache_pattern = re.compile(
        r"cache_(creation_input_tokens|read_input_tokens)=(\d+)"
    )
    pipeline_completed_pattern = re.compile(
        r"pipeline_completed\s+.*?latency_ms=([\d\.]+)"
    )

    with open(log_file, "r", encoding="utf-8") as f:
        content = f.read()
        clean_content = _strip_ansi(content)

    # Stage completion
    for match in stage_completed_pattern.finditer(clean_content):
        duration = float(match.group(1))
        stage_name = match.group(2)
        stage_times[stage_name].append(duration)

    # LLM call completion
    # call_concurrency is an optional structured field — present on calls fired
    # from llm_prefetch_stage.py (concurrent with stages 4–4.5), absent on
    # serial/inline calls. Parsed via a secondary lookup on the matched line.
    concurrency_pattern = re.compile(r"call_concurrency=(\S+)")
    for match in llm_completed_pattern.finditer(clean_content):
        module = match.group(1)
        tokens_in = int(match.group(2))
        duration = float(match.group(3))
        model = match.group(4)
        tokens_out = int(match.group(5))
        cost = _calculate_cost(model, tokens_in, tokens_out)
        line_start = clean_content.rfind("\n", 0, match.start()) + 1
        line_end = clean_content.find("\n", match.end())
        line = clean_content[line_start : line_end if line_end != -1 else None]
        conc_match = concurrency_pattern.search(line)
        concurrency = conc_match.group(1) if conc_match else "inline"
        if module not in llm_calls:
            llm_calls[module] = {
                "durations": [],
                "tokens_in": [],
                "tokens_out": [],
                "count": 0,
                "models": set(),
                "costs": [],
                "concurrency": set(),
                "prefetch_duration": 0.0,
                "inline_duration": 0.0,
                "cache_created_tokens": 0,
                "cache_read_tokens": 0,
            }
        llm_calls[module]["durations"].append(duration)
        llm_calls[module]["tokens_in"].append(tokens_in)
        llm_calls[module]["tokens_out"].append(tokens_out)
        llm_calls[module]["costs"].append(cost)
        llm_calls[module]["count"] = llm_calls[module]["count"] + 1
        llm_calls[module]["models"].add(model)
        llm_calls[module]["concurrency"].add(concurrency)
        if concurrency == "prefetch":
            llm_calls[module]["prefetch_duration"] += duration
        else:
            llm_calls[module]["inline_duration"] += duration

        # Track prompt cache hits
        for cache_match in cache_pattern.finditer(line):
            if cache_match.group(1) == "creation_input_tokens":
                llm_calls[module]["cache_created_tokens"] += int(cache_match.group(2))
            elif cache_match.group(1) == "read_input_tokens":
                llm_calls[module]["cache_read_tokens"] += int(cache_match.group(2))

    # Pipeline completion
    for match in pipeline_completed_pattern.finditer(clean_content):
        duration = float(match.group(1))
        pipeline_times.append(duration)

    return {
        "pipeline_times": pipeline_times,
        "stage_times": dict(stage_times),
        "llm_calls": llm_calls,
        "log_file": log_file.name,
    }


# ── Report generation ─────────────────────────────────────────────────────────


def _write_summary_md(data: dict, output_dir: Path) -> Path:
    """Write human-readable markdown summary."""
    pipeline_times = data["pipeline_times"]
    stage_times = data["stage_times"]
    llm_calls = data["llm_calls"]
    log_file = data["log_file"]

    # Calculate stage stats
    stage_stats = []
    for stage, times in stage_times.items():
        stats = _calc_stats(times)
        stage_stats.append((stage, stats))
    stage_stats.sort(key=lambda x: x[1]["total"], reverse=True)

    # Calculate LLM stats
    llm_stats = []
    for module, module_data in llm_calls.items():
        stats = _calc_stats(module_data["durations"])
        tokens_in_stats = _calc_stats(module_data["tokens_in"])
        tokens_out_stats = _calc_stats(module_data["tokens_out"])
        cost_stats = _calc_stats(module_data["costs"])
        models = module_data["models"]
        cache_created = module_data.get("cache_created_tokens", 0)
        cache_read = module_data.get("cache_read_tokens", 0)
        llm_stats.append(
            (module, stats, tokens_in_stats, tokens_out_stats, models, cost_stats,
             cache_created, cache_read)
        )
    llm_stats.sort(key=lambda x: x[1]["total"], reverse=True)

    total_stage_time = sum(s[1]["total"] for s in stage_stats)
    total_llm_time = sum(s[1]["total"] for s in llm_stats)
    total_llm_calls = sum(s[1]["count"] for s in llm_stats)
    total_tokens_in = sum(s[2]["total"] for s in llm_stats)
    total_tokens_out = sum(s[3]["total"] for s in llm_stats)
    total_cost = sum(s[5]["total"] for s in llm_stats)

    # Wall-clock from pipeline_completed events. This is the truthful denominator
    # for percentages: Σ stage durations overstates wall-clock when stages run
    # concurrently with the prefetched LLM call (stages 4–4.5 overlap with the
    # llm_prefetch_stage task).
    wall_clock_total = sum(pipeline_times) if pipeline_times else 0.0

    # Split LLM time into inline (serial) vs prefetch (concurrent with stages).
    inline_llm_time = sum(m.get("inline_duration", 0.0) for m in llm_calls.values())
    prefetch_llm_time = sum(m.get("prefetch_duration", 0.0) for m in llm_calls.values())

    # Real concurrency savings: prefetched LLM time that was fully absorbed by
    # the pipeline stages running in parallel. The portion that ISN'T absorbed
    # is the time spent in bridge stages awaiting prefetched tasks.
    # Bridge stages: LLMSignalBridgeStage (awaits signal detection prefetch)
    #                EdgeExtractionBridgeStage (awaits edge extraction prefetch)
    signal_bridge_ms = sum(
        s[1]["total"] for s in stage_stats if s[0] == "LLMSignalBridgeStage"
    )
    edge_bridge_ms = sum(
        s[1]["total"] for s in stage_stats if s[0] == "EdgeExtractionBridgeStage"
    )
    bridge_await_total_ms = signal_bridge_ms + edge_bridge_ms
    # prefetch_llm_time is also in ms (sum of latency_ms values)
    concurrency_savings_ms = max(0.0, prefetch_llm_time - bridge_await_total_ms)

    lines = [
        "# Pipeline Timing Analysis",
        "",
        f"- **Log file**: `{log_file}`",
        f"- **Pipeline runs**: {len(pipeline_times)}",
    ]

    if pipeline_times:
        stats = _calc_stats(pipeline_times)
        lines.append(
            f"- **Avg pipeline**: {stats['mean'] / 1000:.2f}s "
            f"(range: {stats['min'] / 1000:.2f}s – {stats['max'] / 1000:.2f}s)"
        )

    lines.extend(["", "## Wall-Clock vs. Stage Sum", ""])
    if wall_clock_total:
        lines.append(
            f"- **Wall-clock pipeline total**: {wall_clock_total / 1000:.2f}s "
            f"(authoritative — from `pipeline_completed` events)"
        )
        lines.append(
            f"- **Σ stage durations**: {total_stage_time / 1000:.2f}s "
            f"(overstates wall-clock when stages overlap)"
        )
        lines.append(
            f"- **Prefetched LLM time**: {prefetch_llm_time / 1000:.2f}s "
            f"(runs in background during stages 4–4.6)"
        )
        lines.append(
            f"- **Bridge await time**: {bridge_await_total_ms / 1000:.2f}s "
            f"(un-overlapped portion on critical path: "
            f"SignalBridge={signal_bridge_ms / 1000:.1f}s, "
            f"EdgeBridge={edge_bridge_ms / 1000:.1f}s)"
        )
        lines.append(
            f"- **Concurrency savings**: {concurrency_savings_ms / 1000:.2f}s "
            f"(prefetched LLM time fully absorbed by parallel stage execution)"
        )
    else:
        lines.append(
            "- No `pipeline_completed` events found — percentages below use "
            "Σ stages and may overstate wall-clock contribution."
        )

    lines.extend(["", "## Stage Timing (by total time)", ""])
    pct_denom = wall_clock_total if wall_clock_total else total_stage_time
    pct_label = "%wall" if wall_clock_total else "%sum"
    lines.append(
        f"| {'Stage':<38} | {'Calls':>6} | {'Total(s)':>10} | {'Mean(ms)':>10} | {pct_label:>6} |"
    )
    lines.append(f"|{'-' * 40}|{'-' * 8}|{'-' * 12}|{'-' * 12}|{'-' * 8}|")

    for stage, stats in stage_stats:
        pct = (stats["total"] / pct_denom * 100) if pct_denom else 0
        lines.append(
            f"| {stage:<38} | {stats['count']:>6} | "
            f"{stats['total'] / 1000:>10.2f} | {stats['mean']:>10.1f} | {pct:>6.1f} |"
        )

    lines.append(
        f"| {'TOTAL':<38} | {'':>6} | {total_stage_time / 1000:>10.2f} | {'':>10} | {'':>6} |"
    )
    if wall_clock_total:
        lines.append(
            f"\n_Stage `%wall` columns sum to >100% by design — overlap with "
            f"the prefetched LLM call shows up as the gap between Σ stages "
            f"({total_stage_time / 1000:.2f}s) and wall-clock "
            f"({wall_clock_total / 1000:.2f}s)._"
        )

    lines.extend(["", "## LLM Calls by Module (by total time)", ""])
    lines.append(
        f"| {'Module':<20} | {'Model':<16} | {'Calls':>5} | "
        f"{'Time(s)':>8} | {'Cost($)':>8} | {'TokIn':>7} | {'TokOut':>7} |"
    )
    lines.append(
        f"|{'-' * 22}|{'-' * 18}|{'-' * 7}|{'-' * 10}|{'-' * 10}|{'-' * 9}|{'-' * 9}|"
    )

    for module, stats, tok_in, tok_out, models, cost_stats, _, _ in llm_stats:
        model_str = ", ".join(sorted(models)) if models else "unknown"
        if len(model_str) > 15:
            model_str = model_str[:12] + ".."
        lines.append(
            f"| {module:<20} | {model_str:<16} | {stats['count']:>5} | "
            f"{stats['total'] / 1000:>8.2f} | {cost_stats['total']:>8.4f} | "
            f"{tok_in['mean']:>7.0f} | {tok_out['mean']:>7.0f} |"
        )

    lines.append(
        f"| {'TOTAL':<20} | {'':<16} | {total_llm_calls:>5} | "
        f"{total_llm_time / 1000:>8.2f} | {total_cost:>8.4f} | {'':>7} | {'':>7} |"
    )

    if prefetch_llm_time or inline_llm_time:
        lines.extend(["", "### LLM Time by Concurrency", ""])
        lines.append(
            f"- **Inline (serial)**: {inline_llm_time / 1000:.2f}s — on the "
            f"critical path, fully visible in wall-clock"
        )
        lines.append(
            f"- **Prefetched (background)**: "
            f"{prefetch_llm_time / 1000:.2f}s — runs in parallel with pipeline "
            f"stages; only the un-overlapped bridge await ({bridge_await_total_ms:.2f}s) "
            f"is on the critical path"
        )
        lines.append(
            f"- **Concurrency savings**: {concurrency_savings_ms / 1000:.2f}s "
            f"({concurrency_savings_ms / max(prefetch_llm_time, 0.001) * 100:.0f}% "
            f"of prefetched LLM time absorbed by parallel execution)"
        )
        lines.append(
            f"- **Σ LLM latency**: {total_llm_time / 1000:.2f}s "
            f"(sum of all LLM calls; overlaps with itself — do not use as wall-clock)"
        )

    # Prompt caching section
    total_cache_created = sum(s[6] for s in llm_stats)
    total_cache_read = sum(s[7] for s in llm_stats)
    if total_cache_created or total_cache_read:
        lines.extend(["", "### Prompt Caching", ""])
        lines.append(
            f"| {'Module':<20} | {'Cache Created':>13} | {'Cache Read':>11} | {'Cache Hit %':>11} |"
        )
        lines.append(f"|{'-' * 22}|{'-' * 15}|{'-' * 13}|{'-' * 13}|")
        for module, stats, tok_in, _, _, _, cache_created, cache_read in llm_stats:
            total_in = tok_in["total"]
            hit_pct = (cache_read / total_in * 100) if total_in > 0 else 0
            lines.append(
                f"| {module:<20} | {cache_created:>13,} | {cache_read:>11,} | {hit_pct:>10.1f}% |"
            )
        lines.append("")
        lines.append(
            "**Cache write cost**: 1.25× base input price per token written. "
            "**Cache read savings**: 0.10× base input price — 90% discount on cached prefix."
        )

    lines.extend(["", "## Key Findings", "", "### Top Bottlenecks"])
    for i, (stage, stats) in enumerate(stage_stats[:3], 1):
        pct = stats["total"] / pct_denom * 100 if pct_denom else 0
        lines.append(
            f"{i}. **{stage}**: {stats['total'] / 1000:.1f}s ({pct:.1f}{pct_label[1:]})"
        )

    lines.extend(["", "### LLM Cost Breakdown"])
    for module, stats, _, _, models, cost_stats, _, _ in llm_stats:
        pct = stats["total"] / total_llm_time * 100 if total_llm_time else 0
        model_info = f" `[{', '.join(sorted(models))}]`" if models else ""
        lines.append(
            f"- **{module}**: ${cost_stats['total']:.4f} "
            f"({stats['count']} calls){model_info}"
        )

    lines.extend(
        [
            "",
            f"**Total estimated cost: ${total_cost:.4f}**",
            "",
            "### Token Usage",
            f"- Input:  {total_tokens_in:,.0f} tokens",
            f"- Output: {total_tokens_out:,.0f} tokens",
            f"- Total:  {total_tokens_in + total_tokens_out:,.0f} tokens",
        ]
    )

    out_path = output_dir / "summary.md"
    out_path.write_text("\n".join(lines) + "\n")
    return out_path


def _write_stages_csv(data: dict, output_dir: Path) -> Path:
    """Write per-stage timing CSV."""
    out_path = output_dir / "stages.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["stage_name", "call_count", "total_ms", "mean_ms", "min_ms", "max_ms"]
        )
        for stage, times in data["stage_times"].items():
            stats = _calc_stats(times)
            writer.writerow(
                [
                    stage,
                    int(stats["count"]),
                    round(stats["total"], 2),
                    round(stats["mean"], 2),
                    round(stats["min"], 2),
                    round(stats["max"], 2),
                ]
            )
    return out_path


def _write_llm_calls_csv(data: dict, output_dir: Path) -> Path:
    """Write per-LLM-call aggregated CSV (one row per module)."""
    out_path = output_dir / "llm_calls.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "module",
                "model",
                "call_count",
                "total_latency_ms",
                "mean_latency_ms",
                "total_tokens_in",
                "mean_tokens_in",
                "total_tokens_out",
                "mean_tokens_out",
                "total_cost_usd",
            ]
        )
        for module, module_data in data["llm_calls"].items():
            dur_stats = _calc_stats(module_data["durations"])
            tok_in_stats = _calc_stats(module_data["tokens_in"])
            tok_out_stats = _calc_stats(module_data["tokens_out"])
            cost_stats = _calc_stats(module_data["costs"])
            models = (
                ", ".join(sorted(module_data["models"]))
                if module_data["models"]
                else "unknown"
            )
            writer.writerow(
                [
                    module,
                    models,
                    int(dur_stats["count"]),
                    round(dur_stats["total"], 2),
                    round(dur_stats["mean"], 2),
                    int(tok_in_stats["total"]),
                    round(tok_in_stats["mean"], 1),
                    int(tok_out_stats["total"]),
                    round(tok_out_stats["mean"], 1),
                    round(cost_stats["total"], 6),
                ]
            )
    return out_path


def write_report(data: dict, output_dir: Path) -> dict[str, Path]:
    """Write all report artifacts to output_dir.

    Returns:
        Dict mapping artifact name to file path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    return {
        "summary": _write_summary_md(data, output_dir),
        "stages": _write_stages_csv(data, output_dir),
        "llm_calls": _write_llm_calls_csv(data, output_dir),
    }


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze an interview log file for pipeline timing and LLM metrics."
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Path to specific log file (default: most recent in logs/)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/latency"),
        help="Output directory for report files (default: reports/latency)",
    )
    args = parser.parse_args()

    log_file = args.log_file
    if log_file is None:
        log_file = _find_latest_log()
        if not log_file:
            print("ERROR: No log files found in logs/ directory", file=sys.stderr)
            return 1

    if not log_file.exists():
        print(f"ERROR: Log file not found: {log_file}", file=sys.stderr)
        return 1

    print(f"Analyzing: {log_file}")

    try:
        data = analyze_log(log_file)
        paths = write_report(data, args.output_dir)
        for name, path in paths.items():
            print(f"  Wrote {name}: {path}")
        return 0
    except Exception as e:
        print(f"ERROR: Failed to analyze log: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
