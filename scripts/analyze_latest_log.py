#!/usr/bin/env python3
"""
Analyze the latest interview log file for pipeline timing and LLM call metrics.

Usage:
    uv run python scripts/analyze_latest_log.py
"""

import re
from collections import defaultdict
from pathlib import Path


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def calc_stats(values: list) -> dict:
    """Calculate statistics for a list of values."""
    if not values:
        return {"count": 0, "mean": 0, "min": 0, "max": 0, "total": 0}
    return {
        "count": len(values),
        "mean": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
        "total": sum(values)
    }


def find_latest_log(logs_dir: str = "logs") -> Path | None:
    """Find the most recent log file in the logs directory."""
    log_path = Path(logs_dir)
    if not log_path.exists():
        return None

    log_files = [
        f for f in log_path.iterdir()
        if f.is_file() and f.name.startswith("interview_") and f.name.endswith(".log")
    ]

    if not log_files:
        return None

    # Sort by modification time (most recent first)
    log_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return log_files[0]


def analyze_log(log_file: Path) -> dict:
    """Analyze a log file and return timing metrics."""

    # Data structures
    pipeline_times: list[float] = []
    stage_times: dict[str, list[float]] = defaultdict(list)
    llm_calls: dict[str, dict] = {}

    # Regex patterns
    stage_completed_pattern = re.compile(
        r'stage_completed\s+duration_ms=([\d\.]+)\s+stage_name=(\S+)'
    )
    llm_completed_pattern = re.compile(
        r'llm_call_complete\s+.*?client_type=(\S+)'
        r'.*?input_tokens=(\d+).*?latency_ms=([\d\.]+).*?output_tokens=(\d+)'
    )
    pipeline_completed_pattern = re.compile(
        r'pipeline_completed\s+total_duration_ms=([\d\.]+)'
    )

    with open(log_file, 'r', encoding='utf-8') as f:
        content = f.read()
        clean_content = strip_ansi(content)

    # Stage completion
    for match in stage_completed_pattern.finditer(clean_content):
        duration = float(match.group(1))
        stage_name = match.group(2)
        stage_times[stage_name].append(duration)

    # LLM call completion
    for match in llm_completed_pattern.finditer(clean_content):
        module = match.group(1)
        tokens_in = int(match.group(2))
        duration = float(match.group(3))
        tokens_out = int(match.group(4))
        if module not in llm_calls:
            llm_calls[module] = {"durations": [], "tokens_in": [], "tokens_out": [], "count": 0}
        llm_calls[module]["durations"].append(duration)  # type: ignore
        llm_calls[module]["tokens_in"].append(tokens_in)  # type: ignore
        llm_calls[module]["tokens_out"].append(tokens_out)  # type: ignore
        llm_calls[module]["count"] = llm_calls[module]["count"] + 1  # type: ignore

    # Pipeline completion
    for match in pipeline_completed_pattern.finditer(clean_content):
        duration = float(match.group(1))
        pipeline_times.append(duration)

    return {
        "pipeline_times": pipeline_times,
        "stage_times": stage_times,
        "llm_calls": llm_calls,
        "log_file": log_file.name
    }


def print_report(data: dict) -> None:
    """Print formatted analysis report."""

    pipeline_times = data["pipeline_times"]
    stage_times = data["stage_times"]
    llm_calls = data["llm_calls"]
    log_file = data["log_file"]

    # Calculate stage stats
    stage_stats = []
    for stage, times in stage_times.items():
        stats = calc_stats(times)
        stage_stats.append((stage, stats))
    stage_stats.sort(key=lambda x: x[1]["total"], reverse=True)

    # Calculate LLM stats
    llm_stats = []
    for module, data_item in llm_calls.items():
        stats = calc_stats(data_item["durations"])
        tokens_in_stats = calc_stats(data_item["tokens_in"])
        tokens_out_stats = calc_stats(data_item["tokens_out"])
        llm_stats.append((module, stats, tokens_in_stats, tokens_out_stats))
    llm_stats.sort(key=lambda x: x[1]["total"], reverse=True)

    total_stage_time = sum(s[1]["total"] for s in stage_stats)
    total_llm_time = sum(s[1]["total"] for s in llm_stats)
    total_llm_calls = sum(s[1]["count"] for s in llm_stats)
    total_tokens_in = sum(s[2]["total"] for s in llm_stats)
    total_tokens_out = sum(s[3]["total"] for s in llm_stats)

    # Print report
    width = 85
    print("=" * width)
    print("PIPELINE TIMING ANALYSIS".center(width))
    print("=" * width)
    print(f"\nLog file: {log_file}")
    print(f"Pipeline runs: {len(pipeline_times)}")

    if pipeline_times:
        stats = calc_stats(pipeline_times)
        print(f"Avg pipeline: {stats['mean']/1000:.2f}s (range: {stats['min']/1000:.2f}s - {stats['max']/1000:.2f}s)")

    print("\n" + "-" * width)
    print("STAGE TIMING (by total time)")
    print("-" * width)
    print(f"{'Stage':<38} {'Calls':>6} {'Total(s)':>10} {'Mean(ms)':>10} {'%':>6}")
    print("-" * width)

    for stage, stats in stage_stats:
        pct = (stats['total'] / total_stage_time * 100) if total_stage_time else 0
        print(f"{stage:<38} {stats['count']:>6} {stats['total']/1000:>10.2f} {stats['mean']:>10.1f} {pct:>6.1f}")

    print("-" * width)
    print(f"{'TOTAL':<38} {'':>6} {total_stage_time/1000:>10.2f}")

    print("\n" + "=" * width)
    print("LLM CALLS BY MODULE (by total time)")
    print("=" * width)
    print(f"{'Module':<25} {'Calls':>6} {'Total(s)':>10} {'Mean(ms)':>10} {'AvgIn':>8} {'AvgOut':>8}")
    print("-" * width)

    for module, stats, tok_in, tok_out in llm_stats:
        print(f"{module:<25} {stats['count']:>6} {stats['total']/1000:>10.2f} {stats['mean']:>10.1f} {tok_in['mean']:>8.0f} {tok_out['mean']:>8.0f}")

    print("-" * width)
    avg_llm = total_llm_time/total_llm_calls if total_llm_calls else 0
    print(f"{'TOTAL':<25} {total_llm_calls:>6} {total_llm_time/1000:>10.2f} {avg_llm:>10.1f}")

    print("\n" + "=" * width)
    print("KEY FINDINGS")
    print("=" * width)

    print("\n1. TOP BOTTLENECKS:")
    for i, (stage, stats) in enumerate(stage_stats[:3], 1):
        pct = (stats['total'] / total_stage_time * 100)
        print(f"   {i}. {stage}: {stats['total']/1000:.1f}s ({pct:.1f}%)")

    print("\n2. LLM COST DISTRIBUTION:")
    for module, stats, _, _ in llm_stats:
        pct = (stats['total'] / total_llm_time * 100)
        print(f"   - {module}: {pct:.1f}% ({stats['count']} calls)")

    print("\n3. TOKEN USAGE:")
    print(f"   - Input:  {total_tokens_in:,.0f} tokens")
    print(f"   - Output: {total_tokens_out:,.0f} tokens")
    print(f"   - Total:  {total_tokens_in + total_tokens_out:,.0f} tokens")

    print("\n" + "=" * width)


def main():
    """Main entry point."""
    log_file = find_latest_log()

    if not log_file:
        print("ERROR: No log files found in logs/ directory")
        print("Expected files matching: interview_*.log")
        return 1

    print(f"Analyzing: {log_file}\n")

    try:
        data = analyze_log(log_file)
        print_report(data)
        return 0
    except Exception as e:
        print(f"ERROR: Failed to analyze log: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
