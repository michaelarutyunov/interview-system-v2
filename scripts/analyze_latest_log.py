#!/usr/bin/env python3
"""
Analyze the latest interview log file for pipeline timing and LLM call metrics.

Usage:
    uv run python scripts/analyze_latest_log.py
"""

import re
from collections import defaultdict
from pathlib import Path


def load_env_file(env_path: Path = Path(".env")) -> dict[str, str]:
    """Load environment variables from .env file."""
    env_vars = {}
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    env_vars[key] = value.strip('"\'')
    return env_vars


# Load environment variables for pricing
_env_vars = load_env_file()

# Pricing per million tokens (input, output)
MODEL_PRICING: dict[str, tuple[float, float]] = {
    # Anthropic models
    "claude-sonnet-4-6": (
        float(_env_vars.get("ANTHROPIC_SONNET_INPUT", "3.00")),
        float(_env_vars.get("ANTHROPIC_SONNET_OUTPUT", "15.00"))
    ),
    "claude-haiku-4-5": (
        float(_env_vars.get("ANTHROPIC_HAIKU_INPUT", "1.00")),
        float(_env_vars.get("ANTHROPIC_HAIKU_OUTPUT", "5.00"))
    ),
    # Kimi models
    "kimi-k2-0905-preview": (
        float(_env_vars.get("KIMI_K2_INPUT", "0.60")),
        float(_env_vars.get("KIMI_K2_OUTPUT", "2.50"))
    ),
    "kimi-k2": (
        float(_env_vars.get("KIMI_K2_INPUT", "0.60")),
        float(_env_vars.get("KIMI_K2_OUTPUT", "2.50"))
    ),
}


def calculate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Calculate cost in USD for a given model and token usage."""
    # Normalize model name (handle prefixes)
    model_key = model
    for key in MODEL_PRICING:
        if key in model:
            model_key = key
            break

    if model_key not in MODEL_PRICING:
        # Unknown model, return 0 cost
        return 0.0

    input_price, output_price = MODEL_PRICING[model_key]
    input_cost = (tokens_in / 1_000_000) * input_price
    output_cost = (tokens_out / 1_000_000) * output_price
    return input_cost + output_cost


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
        r'.*?input_tokens=(\d+).*?latency_ms=([\d\.]+)'
        r'.*?model=(\S+).*?output_tokens=(\d+)'
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
        model = match.group(4)
        tokens_out = int(match.group(5))
        cost = calculate_cost(model, tokens_in, tokens_out)
        if module not in llm_calls:
            llm_calls[module] = {
                "durations": [], "tokens_in": [], "tokens_out": [],
                "count": 0, "models": set(), "costs": []
            }
        llm_calls[module]["durations"].append(duration)  # type: ignore
        llm_calls[module]["tokens_in"].append(tokens_in)  # type: ignore
        llm_calls[module]["tokens_out"].append(tokens_out)  # type: ignore
        llm_calls[module]["costs"].append(cost)  # type: ignore
        llm_calls[module]["count"] = llm_calls[module]["count"] + 1  # type: ignore
        llm_calls[module]["models"].add(model)  # type: ignore

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
        cost_stats = calc_stats(data_item["costs"])
        models = data_item["models"]
        llm_stats.append((module, stats, tokens_in_stats, tokens_out_stats, models, cost_stats))
    llm_stats.sort(key=lambda x: x[1]["total"], reverse=True)

    total_stage_time = sum(s[1]["total"] for s in stage_stats)
    total_llm_time = sum(s[1]["total"] for s in llm_stats)
    total_llm_calls = sum(s[1]["count"] for s in llm_stats)
    total_tokens_in = sum(s[2]["total"] for s in llm_stats)
    total_tokens_out = sum(s[3]["total"] for s in llm_stats)
    total_cost = sum(s[5]["total"] for s in llm_stats)

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
    print(f"{'Module':<20} {'Model':<16} {'Calls':>5} {'Time(s)':>8} {'Cost($)':>8} {'TokIn':>7} {'TokOut':>7}")
    print("-" * width)

    for module, stats, tok_in, tok_out, models, cost_stats in llm_stats:
        model_str = ", ".join(sorted(models)) if models else "unknown"
        if len(model_str) > 15:
            model_str = model_str[:12] + ".."
        print(f"{module:<20} {model_str:<16} {stats['count']:>5} {stats['total']/1000:>8.2f} {cost_stats['total']:>8.4f} {tok_in['mean']:>7.0f} {tok_out['mean']:>7.0f}")

    print("-" * width)
    print(f"{'TOTAL':<20} {'':<16} {total_llm_calls:>5} {total_llm_time/1000:>8.2f} {total_cost:>8.4f}")

    print("\n" + "=" * width)
    print("KEY FINDINGS")
    print("=" * width)

    print("\n1. TOP BOTTLENECKS:")
    for i, (stage, stats) in enumerate(stage_stats[:3], 1):
        pct = (stats['total'] / total_stage_time * 100)
        print(f"   {i}. {stage}: {stats['total']/1000:.1f}s ({pct:.1f}%)")

    print("\n2. LLM COST BREAKDOWN:")
    for module, stats, _, _, models, cost_stats in llm_stats:
        pct = (stats['total'] / total_llm_time * 100)
        model_info = f" [{', '.join(sorted(models))}]" if models else ""
        print(f"   - {module}: ${cost_stats['total']:.4f} ({stats['count']} calls){model_info}")

    print(f"\n   TOTAL ESTIMATED COST: ${total_cost:.4f}")

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
