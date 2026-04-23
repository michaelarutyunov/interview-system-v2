#!/usr/bin/env python3
"""Latency audit: parse interview logs for per-stage timing and LLM call metrics.

Reads all logs/interview_*.log files and joins with synthetic_interviews/*.json
to produce a structured latency report with per-stage p50/p95, per-LLM-client
token/latency totals, cold-vs-warm split, and methodology breakdown.

Usage:
    uv run python scripts/eval/latency_audit.py
"""

import ast
import csv
import json
import re
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# --- Configuration ---
LOGS_DIR = Path("logs")
INTERVIEWS_DIR = Path("synthetic_interviews")
REPORTS_DIR = Path("reports/latency_audit")

STAGE_P95_THRESHOLD_MS = 2000
OUTPUT_TOKENS_THRESHOLD = 500

# --- Parsing ---
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
PIPELINE_COMPLETED_RE = re.compile(
    r"pipeline_completed\s+.*?latency_ms=(\d+\.?\d*).*?"
    r"stage_timings=(\{.*?\}).*?"
    r"turn_number=(\d+)"
)
LLM_CALL_RE = re.compile(
    r"llm_call_complete\s+.*?"
    r"client_type=(\S+).*?"
    r"input_tokens=(\d+).*?"
    r"latency_ms=(\d+\.?\d*).*?"
    r"model=(\S+).*?"
    r"output_tokens=(\d+).*?"
    r"provider=(\S+)"
)
SIM_STARTED_RE = re.compile(
    r"simulation_started\s+.*?"
    r"concept_id=(\S+).*?"
    r"session_id=(\S+)"
)

STAGE_ORDER = [
    "ContextLoadingStage",
    "UtteranceSavingStage",
    "SRLPreprocessingStage",
    "ExtractionStage",
    "GraphUpdateStage",
    "SlotDiscoveryStage",
    "StateComputationStage",
    "StrategySelectionStage",
    "ContinuationStage",
    "QuestionGenerationStage",
    "ResponseSavingStage",
    "ScoringPersistenceStage",
]


@dataclass
class TurnRecord:
    session_id: str
    turn_number: int
    total_latency_ms: float
    stage_timings: dict[str, float]
    methodology: str | None = None
    concept_id: str = ""
    persona_id: str = ""
    log_file: str = ""

    @property
    def is_cold_start(self) -> bool:
        return self.turn_number == 1


@dataclass
class LLMCallRecord:
    client_type: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    turn_number: int
    session_id: str
    log_file: str = ""

    @property
    def is_cold_start(self) -> bool:
        return self.turn_number == 1


@dataclass
class SessionMeta:
    session_id: str
    concept_id: str
    persona_id: str
    methodology: str | None = None


def strip_ansi(s: str) -> str:
    return ANSI_RE.sub("", s)


def parse_stage_timings(raw: str) -> dict[str, float]:
    """Parse a Python dict literal from the stage_timings field."""
    try:
        parsed = ast.literal_eval(raw)
        if isinstance(parsed, dict):
            return {k: float(v) for k, v in parsed.items()}
    except (ValueError, SyntaxError):
        pass
    return {}


def parse_log_file(
    log_path: Path,
) -> tuple[list[TurnRecord], list[LLMCallRecord], dict[str, SessionMeta]]:
    """Parse a single log file into turn records, LLM call records, and session metadata."""
    turns: list[TurnRecord] = []
    llm_calls: list[LLMCallRecord] = []
    sessions: dict[str, SessionMeta] = {}
    current_session_id: str | None = None
    current_concept: str = ""
    current_persona: str = ""
    current_turn: int = 0

    content = log_path.read_text()
    for line in content.splitlines():
        clean = strip_ansi(line)
        if not clean.strip():
            continue

        # Track session from simulation_started
        m = SIM_STARTED_RE.search(clean)
        if m:
            concept_id = m.group(1)
            sid = m.group(2)
            # Extract persona_id from remaining line
            pm = re.search(r"persona_id=(\S+)", clean)
            persona_id = pm.group(1) if pm else ""
            sessions[sid] = SessionMeta(
                session_id=sid, concept_id=concept_id, persona_id=persona_id
            )
            current_session_id = sid
            current_concept = concept_id
            current_persona = persona_id
            continue

        # Extract turn number from context_loaded or pipeline_completed
        tn = re.search(r"turn_number=(\d+)", clean)
        if tn:
            current_turn = int(tn.group(1))

        # Pipeline completed — full stage timings for this turn
        m = PIPELINE_COMPLETED_RE.search(clean)
        if m and current_session_id:
            total_latency = float(m.group(1))
            stage_timings = parse_stage_timings(m.group(2))
            turn_num = int(m.group(3))
            turns.append(
                TurnRecord(
                    session_id=current_session_id,
                    turn_number=turn_num,
                    total_latency_ms=total_latency,
                    stage_timings=stage_timings,
                    concept_id=current_concept,
                    persona_id=current_persona,
                    log_file=log_path.name,
                )
            )
            continue

        # LLM call complete
        m = LLM_CALL_RE.search(clean)
        if m and current_session_id:
            llm_calls.append(
                LLMCallRecord(
                    client_type=m.group(1),
                    input_tokens=int(m.group(2)),
                    latency_ms=float(m.group(3)),
                    model=m.group(4),
                    output_tokens=int(m.group(5)),
                    provider=m.group(6),
                    turn_number=current_turn,
                    session_id=current_session_id,
                    log_file=log_path.name,
                )
            )

    return turns, llm_calls, sessions


def join_methodology(
    sessions: dict[str, SessionMeta],
    turns: list[TurnRecord],
) -> None:
    """Enrich sessions/turns with methodology from interview JSON files."""
    session_methodology: dict[str, str] = {}
    for json_path in INTERVIEWS_DIR.glob("*.json"):
        try:
            data = json.loads(json_path.read_text())
            meta = data.get("metadata", {})
            sid = meta.get("session_id", "")
            meth = meta.get("methodology", "")
            if sid and meth:
                session_methodology[sid] = meth
        except (json.JSONDecodeError, KeyError):
            continue

    for sid, s in sessions.items():
        s.methodology = session_methodology.get(sid)
    for t in turns:
        t.methodology = session_methodology.get(t.session_id)


def percentile(values: list[float], pct: float) -> float:
    """Compute a percentile from a sorted list."""
    if not values:
        return 0.0
    sorted_v = sorted(values)
    idx = min(int(len(sorted_v) * pct / 100), len(sorted_v) - 1)
    return sorted_v[idx]


def compute_stats(values: list[float]) -> dict[str, float]:
    """Compute summary statistics for a list of values."""
    if not values:
        return {"p50": 0, "p95": 0, "mean": 0, "max": 0, "sum": 0, "count": 0}
    sorted_v = sorted(values)
    n = len(sorted_v)
    return {
        "p50": sorted_v[n // 2],
        "p95": percentile(values, 95),
        "mean": statistics.mean(sorted_v),
        "max": sorted_v[-1],
        "sum": sum(sorted_v),
        "count": n,
    }


def identify_optimization_candidates(
    all_turns: list[TurnRecord], all_llm_calls: list[LLMCallRecord]
) -> list[dict]:
    """Identify and rank optimization candidates based on thresholds."""
    candidates = []
    steady_turns = [t for t in all_turns if not t.is_cold_start]

    # 1. High-latency stages (steady-state p95 > threshold)
    stage_durations: dict[str, list[float]] = defaultdict(list)
    for t in steady_turns:
        for stage, dur in t.stage_timings.items():
            stage_durations[stage].append(dur)

    for stage in STAGE_ORDER:
        durs = stage_durations.get(stage, [])
        if not durs:
            continue
        p95 = percentile(durs, 95)
        mean = statistics.mean(durs)
        if p95 > STAGE_P95_THRESHOLD_MS:
            candidates.append(
                {
                    "rank": 0,
                    "type": "high_latency_stage",
                    "name": stage,
                    "metric": f"steady-state p95={p95:.0f}ms, mean={mean:.0f}ms",
                    "p95_ms": p95,
                    "mean_ms": mean,
                    "count": len(durs),
                    "impact": p95 * len(durs),
                }
            )

    # 2. High-output-token LLM calls (> threshold per call)
    client_outputs: dict[str, list[int]] = defaultdict(list)
    client_latencies: dict[str, list[float]] = defaultdict(list)
    for call in all_llm_calls:
        key = f"{call.client_type}/{call.model}"
        client_outputs[key].append(call.output_tokens)
        client_latencies[key].append(call.latency_ms)

    for key, tokens_list in client_outputs.items():
        mean_tokens = statistics.mean(tokens_list)
        if mean_tokens > OUTPUT_TOKENS_THRESHOLD:
            mean_lat = statistics.mean(client_latencies[key])
            candidates.append(
                {
                    "rank": 0,
                    "type": "high_output_tokens",
                    "name": key,
                    "metric": f"mean output_tokens={mean_tokens:.0f}, mean latency={mean_lat:.0f}ms",
                    "mean_tokens": mean_tokens,
                    "mean_latency_ms": mean_lat,
                    "count": len(tokens_list),
                    "impact": mean_lat * len(tokens_list),
                }
            )

    # 3. Multiple LLM calls per turn (count distinct client_types per turn-session)
    turn_calls: dict[tuple[str, int], set[str]] = defaultdict(set)
    for call in all_llm_calls:
        turn_calls[(call.session_id, call.turn_number)].add(call.client_type)
    multi_call_turns = [(k, v) for k, v in turn_calls.items() if len(v) > 1]
    if multi_call_turns:
        avg_calls = statistics.mean(len(v) for v in turn_calls.values())
        candidates.append(
            {
                "rank": 0,
                "type": "multi_llm_per_turn",
                "name": "pipeline LLM calls",
                "metric": f"{len(multi_call_turns)}/{len(turn_calls)} turns have >1 LLM client, avg={avg_calls:.1f}",
                "count": len(turn_calls),
                "impact": len(multi_call_turns),
            }
        )

    # Sort by impact (descending) and assign rank
    candidates.sort(key=lambda c: c.get("impact", 0), reverse=True)
    for i, c in enumerate(candidates):
        c["rank"] = i + 1

    return candidates[:5]


def generate_report(
    all_turns: list[TurnRecord],
    all_llm_calls: list[LLMCallRecord],
    sessions: dict[str, SessionMeta],
    candidates: list[dict],
    log_files: list[str],
) -> str:
    """Generate the markdown report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines: list[str] = []

    def L(text: str = "") -> None:
        lines.append(text)

    # Header
    L("# Latency Audit Report")
    L(f"Generated: {now}")
    L()
    L("## Summary")
    L(f"- **Log files parsed**: {len(log_files)}")
    L(f"- **Sessions found**: {len(sessions)}")
    L(f"- **Total turns**: {len(all_turns)}")
    L(f"  - Cold start (turn 1): {sum(1 for t in all_turns if t.is_cold_start)}")
    L(f"  - Steady state (turn 2+): {sum(1 for t in all_turns if not t.is_cold_start)}")
    L(f"- **LLM calls**: {len(all_llm_calls)}")

    methodologies = set()
    for t in all_turns:
        if t.methodology:
            methodologies.add(t.methodology)
    if methodologies:
        L(f"- **Methodologies**: {', '.join(sorted(methodologies))}")

    L()

    # Cold Start vs Steady State Overview
    cold_turns = [t for t in all_turns if t.is_cold_start]
    warm_turns = [t for t in all_turns if not t.is_cold_start]

    if cold_turns:
        cold_totals = [t.total_latency_ms for t in cold_turns]
        L("## Cold Start (Turn 1)")
        L(
            f"Total pipeline latency: p50={percentile(cold_totals, 50):.0f}ms, "
            f"p95={percentile(cold_totals, 95):.0f}ms, "
            f"max={max(cold_totals):.0f}ms (N={len(cold_totals)})"
        )
        L()

    if warm_turns:
        warm_totals = [t.total_latency_ms for t in warm_turns]
        L("## Steady State (Turn 2+)")
        L(
            f"Total pipeline latency: p50={percentile(warm_totals, 50):.0f}ms, "
            f"p95={percentile(warm_totals, 95):.0f}ms, "
            f"max={max(warm_totals):.0f}ms (N={len(warm_totals)})"
        )
        L()

    # Per-Stage Timing
    for label, turns_subset in [
        ("Cold Start (Turn 1)", cold_turns),
        ("Steady State (Turn 2+)", warm_turns),
    ]:
        if not turns_subset:
            continue
        L(f"### Per-Stage Timing — {label}")
        L()
        L("| Stage | p50 (ms) | p95 (ms) | Mean (ms) | Max (ms) | Total (ms) | N |")
        L("|-------|----------|----------|-----------|----------|-----------|---|")
        for stage in STAGE_ORDER:
            durs = [
                t.stage_timings.get(stage, 0)
                for t in turns_subset
                if stage in t.stage_timings
            ]
            if not durs:
                continue
            s = compute_stats(durs)
            L(
                f"| {stage} | {s['p50']:.0f} | {s['p95']:.0f} | {s['mean']:.0f} | "
                f"{s['max']:.0f} | {s['sum']:.0f} | {s['count']} |"
            )
        L()

    # LLM Call Metrics
    L("## LLM Call Metrics")
    L()
    L(
        "| Client Type | Model | Provider | Calls | Input Tokens | Output Tokens | "
        "Mean Latency (ms) | p95 Latency (ms) |"
    )
    L(
        "|-------------|-------|----------|-------|-------------|--------------|-------------------|------------------|"
    )

    client_groups: dict[str, list[LLMCallRecord]] = defaultdict(list)
    for c in all_llm_calls:
        key = (c.client_type, c.model, c.provider)
        client_groups[str(key)].append(c)

    for key in sorted(client_groups):
        calls = client_groups[key]
        # Re-extract fields from first call
        first = calls[0]
        input_total = sum(c.input_tokens for c in calls)
        output_total = sum(c.output_tokens for c in calls)
        lats = [c.latency_ms for c in calls]
        p95 = percentile(lats, 95)
        L(
            f"| {first.client_type} | {first.model} | {first.provider} | {len(calls)} | "
            f"{input_total:,} | {output_total:,} | {statistics.mean(lats):.0f} | {p95:.0f} |"
        )
    L()

    # Per-Methodology Breakdown
    meth_turns: dict[str, list[TurnRecord]] = defaultdict(list)
    for t in all_turns:
        meth = t.methodology or "unknown"
        meth_turns[meth].append(t)

    if len(meth_turns) > 1 or "unknown" not in meth_turns:
        L("## Per-Methodology Breakdown")
        L()
        L("| Methodology | Turns | Cold | p50 Total (ms) | p95 Total (ms) |")
        L("|-------------|-------|------|----------------|----------------|")
        for meth in sorted(meth_turns):
            mturns = meth_turns[meth]
            cold = sum(1 for t in mturns if t.is_cold_start)
            totals = [t.total_latency_ms for t in mturns]
            L(
                f"| {meth} | {len(mturns)} | {cold} | "
                f"{percentile(totals, 50):.0f} | {percentile(totals, 95):.0f} |"
            )
        L()

        # Per-stage per-methodology (steady-state only)
        L("### Per-Stage by Methodology (Steady State)")
        L()
        for meth in sorted(meth_turns):
            msteady = [t for t in meth_turns[meth] if not t.is_cold_start]
            if not msteady:
                continue
            L(f"**{meth}**")
            L()
            L("| Stage | Mean (ms) | p95 (ms) | N |")
            L("|-------|-----------|----------|---|")
            for stage in STAGE_ORDER:
                durs = [
                    t.stage_timings.get(stage, 0)
                    for t in msteady
                    if stage in t.stage_timings
                ]
                if not durs:
                    continue
                s = compute_stats(durs)
                L(f"| {stage} | {s['mean']:.0f} | {s['p95']:.0f} | {s['count']} |")
            L()

    # Optimization Candidates
    L("## Optimization Candidates")
    L()
    if candidates:
        for c in candidates:
            L(f"### {c['rank']}. {c['name']} ({c['type']})")
            L(f"- **Metric**: {c['metric']}")
            L(f"- **Sample size**: {c['count']} observations")
            L()
    else:
        L("No optimization candidates flagged by current thresholds.")
        L()

    # Threshold Reference
    L("## Threshold Reference")
    L(f"- Stage steady-state p95 flag: >{STAGE_P95_THRESHOLD_MS}ms")
    L(f"- LLM output tokens per call flag: >{OUTPUT_TOKENS_THRESHOLD}")
    L()

    return "\n".join(lines)


def write_csv(all_turns: list[TurnRecord], csv_path: Path) -> None:
    """Write per-turn per-stage timings as a CSV for pivot analysis."""
    fields = [
        "session_id",
        "log_file",
        "turn_number",
        "is_cold_start",
        "total_latency_ms",
        "concept_id",
        "persona_id",
        "methodology",
    ] + STAGE_ORDER

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for t in all_turns:
            row: dict[str, str | float | int] = {
                "session_id": t.session_id,
                "log_file": t.log_file,
                "turn_number": t.turn_number,
                "is_cold_start": t.is_cold_start,
                "total_latency_ms": round(t.total_latency_ms, 1),
                "concept_id": t.concept_id,
                "persona_id": t.persona_id,
                "methodology": t.methodology or "",
            }
            for stage in STAGE_ORDER:
                row[stage] = round(t.stage_timings.get(stage, 0), 2)
            writer.writerow(row)


def write_llm_csv(all_llm_calls: list[LLMCallRecord], csv_path: Path) -> None:
    """Write per-LLM-call details as a CSV."""
    fields = [
        "session_id",
        "log_file",
        "turn_number",
        "is_cold_start",
        "client_type",
        "model",
        "provider",
        "input_tokens",
        "output_tokens",
        "latency_ms",
    ]

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for c in all_llm_calls:
            writer.writerow(
                {
                    "session_id": c.session_id,
                    "log_file": c.log_file,
                    "turn_number": c.turn_number,
                    "is_cold_start": c.is_cold_start,
                    "client_type": c.client_type,
                    "model": c.model,
                    "provider": c.provider,
                    "input_tokens": c.input_tokens,
                    "output_tokens": c.output_tokens,
                    "latency_ms": round(c.latency_ms, 2),
                }
            )


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    all_turns: list[TurnRecord] = []
    all_llm_calls: list[LLMCallRecord] = []
    all_sessions: dict[str, SessionMeta] = {}
    log_files_used: list[str] = []

    log_files = sorted(LOGS_DIR.glob("interview_*.log"))
    if not log_files:
        print("No log files found in logs/")
        return

    for log_path in log_files:
        if log_path.stat().st_size == 0:
            continue
        turns, llm_calls, sessions = parse_log_file(log_path)
        if turns or llm_calls:
            all_turns.extend(turns)
            all_llm_calls.extend(llm_calls)
            all_sessions.update(sessions)
            log_files_used.append(log_path.name)

    print(
        f"Parsed {len(log_files_used)} log files: "
        f"{len(all_turns)} turns, {len(all_llm_calls)} LLM calls, "
        f"{len(all_sessions)} sessions"
    )

    join_methodology(all_sessions, all_turns)

    candidates = identify_optimization_candidates(all_turns, all_llm_calls)

    report = generate_report(
        all_turns, all_llm_calls, all_sessions, candidates, log_files_used
    )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"{ts}.md"
    report_path.write_text(report)
    print(f"Report: {report_path}")

    stage_csv_path = REPORTS_DIR / f"{ts}_stages.csv"
    write_csv(all_turns, stage_csv_path)
    print(f"Stage CSV: {stage_csv_path}")

    llm_csv_path = REPORTS_DIR / f"{ts}_llm_calls.csv"
    write_llm_csv(all_llm_calls, llm_csv_path)
    print(f"LLM CSV: {llm_csv_path}")

    print("\nTop candidates:")
    for c in candidates[:3]:
        print(f"  {c['rank']}. {c['name']}: {c['metric']}")


if __name__ == "__main__":
    main()
