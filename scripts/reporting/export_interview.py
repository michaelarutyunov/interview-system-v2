#!/usr/bin/env python3
"""Export all interview artifacts into a single timestamped folder.

Orchestrates the individual generators to produce a complete interview export:
    reports/interviews/<timestamp>/
    ├── 00_meta.yaml
    ├── 00_methodology.yaml    (copy of config/methodologies/<name>.yaml)
    ├── 01_transcript.md
    ├── 02_causal_chains.md
    ├── 03_graph.mmd
    ├── 03_graph.png
    ├── 04_scoring.csv
    ├── 04_scoring_summary.md
    ├── 05_latency/
│   ├── summary.md
│   ├── llm_calls.csv
│   └── stages.csv
    ├── 05_turn_diagnostics.md
    ├── 06_insights.md          (placeholder — filled by reviewer skill)
    └── 99_session.log          (copied from logs/)

Usage:
    # Export most recent simulation
    uv run python scripts/reporting/export_interview.py

    # Export specific simulation
    uv run python scripts/reporting/export_interview.py synthetic_interviews/20260424_*.json

    # Custom output directory
    uv run python scripts/reporting/export_interview.py <json> --output-dir /tmp/my_exports
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.reporting.generate_latency_report import analyze_log, write_report
from scripts.chains.generate_causal_chains import generate_causal_chains
from scripts.chains.generate_chain_groups import generate_chain_groups
from scripts.reporting.generate_transcript import generate_transcript
from scripts.reporting.generate_scoring_csv import generate_scoring_csv
from scripts.reporting.generate_scoring_summary import generate_summary

REPORTS_DIR = Path("reports/interviews")
LOGS_DIR = Path("logs")
SYNTHETIC_DIR = Path("synthetic_interviews")
METHODOLOGY_DIR = Path("config/methodologies")


def _find_most_recent_json() -> Path:
    candidates = sorted(
        SYNTHETIC_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if not candidates:
        raise FileNotFoundError("No JSON files found in synthetic_interviews/")
    return candidates[0]


def _extract_timestamp(json_path: Path) -> str:
    """Extract YYYYMMDD_HHMMSS from filename."""
    match = re.match(r"(\d{8}_\d{6})", json_path.stem)
    if match:
        return match.group(1)
    # Fallback: use file modification time
    mtime = datetime.fromtimestamp(json_path.stat().st_mtime)
    return mtime.strftime("%Y%m%d_%H%M%S")


def _write_meta_yaml(json_path: Path, export_dir: Path) -> None:
    """Write 00_meta.yaml with interview metadata."""
    data = json.loads(json_path.read_text())
    meta = data.get("metadata", {})

    yaml_lines = [
        "# Interview Export Metadata",
        f'timestamp: "{_extract_timestamp(json_path)}"',
        f'session_id: "{meta.get("session_id", "N/A")}"',
        "concept:",
        f'  id: "{meta.get("concept_id", "")}"',
        f'  name: "{meta.get("concept_name", "")}"',
        f'methodology: "{meta.get("methodology", "")}"',
        "persona:",
        f'  id: "{meta.get("persona_id", "")}"',
        f'  name: "{meta.get("persona_name", "")}"',
        "interview:",
        f"  total_turns: {meta.get('total_turns', 0)}",
        f'  status: "{meta.get("status", "")}"',
        f'  saved_at: "{meta.get("saved_at", "")}"',
        "source:",
        f'  json_file: "{json_path}"',
        f'  log_file: "{meta.get("log_file", "")}"',
    ]

    meta_path = export_dir / "00_meta.yaml"
    meta_path.write_text("\n".join(yaml_lines) + "\n")


def _copy_methodology_yaml(json_path: Path, export_dir: Path) -> Path | None:
    """Copy the methodology YAML used for this simulation into the export folder.

    Reads the methodology name from the simulation JSON metadata, locates the
    corresponding YAML in config/methodologies/, and copies it as
    00_methodology.yaml alongside 00_meta.yaml. This preserves the exact
    configuration that produced the results — essential for retrospective
    calibration analysis.
    """
    data = json.loads(json_path.read_text())
    methodology_name = data.get("metadata", {}).get("methodology", "")
    if not methodology_name:
        print("  ⚠ No methodology name in metadata — skipping YAML copy")
        return None

    yaml_path = METHODOLOGY_DIR / f"{methodology_name}.yaml"
    if not yaml_path.exists():
        print(f"  ⚠ Methodology YAML not found: {yaml_path} — skipping")
        return None

    dest = export_dir / "00_methodology.yaml"
    shutil.copy2(yaml_path, dest)
    return dest


def _generate_causal_chains(json_path: Path, output_path: Path) -> None:
    """Run causal chain extraction (flat + grouped) and write to output path."""
    md_flat = generate_causal_chains(json_path)
    output_path.write_text(md_flat)
    # Append grouped view
    try:
        md_groups = generate_chain_groups(json_path, include_mermaid=True)
        with open(output_path, "a") as f:
            f.write("\n---\n\n")
            f.write(md_groups)
    except Exception as e:
        print(f"  ⚠ Chain groups skipped: {e}", file=sys.stderr)


def _generate_mermaid(json_path: Path, mmd_path: Path, png_path: Path) -> None:
    """Generate Mermaid diagram and render PNG."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.chains.generate_mermaid_graph",
            str(json_path),
            "-o",
            str(mmd_path),
            "--scale",
            "1",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Mermaid generation warning: {result.stderr}", file=sys.stderr)

    # PNG should be rendered alongside the .mmd by the script
    # If it didn't render, try manually
    if not png_path.exists() and mmd_path.exists():
        render_result = subprocess.run(
            [
                "npx",
                "@mermaid-js/mermaid-cli",
                "-i",
                str(mmd_path),
                "-o",
                str(png_path),
                "-w",
                "3200",
                "-H",
                "2400",
                "-q",
            ],
            capture_output=True,
            text=True,
        )
        if render_result.returncode != 0:
            print(f"PNG rendering failed: {render_result.stderr}", file=sys.stderr)


def _generate_latency_audit(log_path: Path | None, latency_dir: Path) -> None:
    """Generate latency audit from log file."""
    if log_path is None or not log_path.exists():
        latency_dir.mkdir(parents=True, exist_ok=True)
        (latency_dir / "summary.md").write_text(
            "# Latency Audit\n\n_No log file available for this simulation._\n"
        )
        return

    data = analyze_log(log_path)
    write_report(data, latency_dir)


def _truncate(text: str, max_len: int = 80) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "…"


def _generate_turn_diagnostics(json_path: Path, output_path: Path) -> None:
    """Generate per-turn diagnostics showing nodes, confirmed edges, and rejected candidates."""
    data = json.loads(json_path.read_text())
    meta = data.get("metadata", {})
    turns = data.get("turns", [])

    # Build node_id -> (label, turn_number) map across all turns
    node_map: dict[str, tuple[str, int]] = {}
    for t in turns:
        for n in t.get("nodes_added") or []:
            node_map[n["id"]] = (n["label"], t["turn_number"])

    def node_label(node_id: str) -> str:
        entry = node_map.get(node_id)
        return _truncate(entry[0], 80) if entry else node_id[:12]

    def node_turn(node_id: str) -> str:
        entry = node_map.get(node_id)
        return f"t={entry[1]}" if entry else "?"

    lines: list[str] = [
        f"# Turn Diagnostics — {_extract_timestamp(json_path)}",
        "",
        f"- **Session**: `{meta.get('session_id', 'N/A')}`",
        f"- **Methodology**: `{meta.get('methodology', '')}`",
        f"- **Concept**: {meta.get('concept_name', '')}",
        f"- **Total turns**: {meta.get('total_turns', 0)}",
    ]

    for t in turns:
        tn = t.get("turn_number", "?")
        strategy = t.get("strategy_selected") or "—"
        question = t.get("question", "")
        response = t.get("response", "")

        lines.append("")
        lines.append(f"## Turn {tn} — {strategy}")
        lines.append("")
        lines.append(f"> **system**: {_truncate(question)}")
        lines.append(f"> **user**: {_truncate(response)}")

        nodes = t.get("nodes_added") or []
        ee = t.get("edge_extraction")

        # Nodes extracted
        if nodes:
            lines.append("")
            lines.append(f"### Nodes extracted ({len(nodes)})")
            lines.append("")
            lines.append("| ID | Label | Type |")
            lines.append("|----|-------|------|")
            for n in nodes:
                nid = n["id"][:8]
                label = _truncate(n["label"], 60)
                ntype = n["node_type"]
                lines.append(f"| `{nid}` | {label} | `{ntype}` |")

        if not ee:
            continue

        # Edges confirmed
        confirmed = ee.get("confirmed_edges") or []
        if confirmed:
            lines.append("")
            lines.append(f"### Edges confirmed ({len(confirmed)})")
            lines.append("")
            lines.append(
                "| Source | T | → | Target | T | Type | Conf | Assertion | Direction | Frame |"
            )
            lines.append(
                "|--------|---|---|--------|---|------|------|-----------|-----------|-------|"
            )
            for e in confirmed:
                src = node_label(e["source_node_id"])
                src_t = node_turn(e["source_node_id"])
                tgt = node_label(e["target_node_id"])
                tgt_t = node_turn(e["target_node_id"])
                etype = e["edge_type"]
                conf = e.get("confidence", "—")
                assertion = e.get("assertion") or "—"
                direction = e.get("direction") or "—"
                frame = e.get("frame") or "—"
                lines.append(
                    f"| {src} | {src_t} | → | {tgt} | {tgt_t} | `{etype}` | {conf} | {assertion} | {direction} | {frame} |"
                )

        # Rejected candidates
        rejected = ee.get("rejected_candidates") or []
        if rejected:
            # Summary table by reason
            reason_counts: dict[str, int] = {}
            for r in rejected:
                reason = r.get("rejection_reason", "unknown")
                reason_counts[reason] = reason_counts.get(reason, 0) + 1

            lines.append("")
            lines.append(f"### Rejected candidates ({len(rejected)})")
            lines.append("")
            lines.append("| Reason | Count |")
            lines.append("|--------|-------|")
            for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
                lines.append(f"| `{reason}` | {count} |")

            # Per-pair details in collapsible section
            lines.append("")
            lines.append("<details>")
            lines.append("<summary>Per-pair details</summary>")
            lines.append("")
            lines.append("| Source | → | Target | Reason |")
            lines.append("|--------|---|--------|--------|")
            for r in rejected:
                src = node_label(r["source_node_id"])
                tgt = node_label(r["target_node_id"])
                reason = r.get("rejection_reason", "unknown")
                lines.append(f"| {src} | → | {tgt} | `{reason}` |")
            lines.append("")
            lines.append("</details>")

    output_path.write_text("\n".join(lines) + "\n")


def export_interview(json_path: Path, output_dir: Path | None = None) -> Path:
    """Export all interview artifacts into a single folder.

    Args:
        json_path: Path to the simulation JSON file.
        output_dir: Optional output directory. If not provided, uses
            reports/interviews/<timestamp>/.

    Returns:
        Path to the export directory.
    """
    timestamp = _extract_timestamp(json_path)

    if output_dir:
        export_dir = output_dir
    else:
        export_dir = REPORTS_DIR / timestamp

    export_dir.mkdir(parents=True, exist_ok=True)

    print(f"Exporting {json_path.name} → {export_dir}")

    # 00_meta.yaml
    _write_meta_yaml(json_path, export_dir)
    print("  ✓ 00_meta.yaml")

    # 00_methodology.yaml — copy the YAML that produced this simulation
    yaml_dest = _copy_methodology_yaml(json_path, export_dir)
    if yaml_dest:
        print(f"  ✓ 00_methodology.yaml ({yaml_dest.name})")

    # 01_transcript.md
    transcript_path = export_dir / "01_transcript.md"
    generate_transcript(json_path, output_path=transcript_path)
    print("  ✓ 01_transcript.md")

    # 02_causal_chains.md
    chains_path = export_dir / "02_causal_chains.md"
    _generate_causal_chains(json_path, chains_path)
    print("  ✓ 02_causal_chains.md")

    # 03_graph.mmd + .png
    mmd_path = export_dir / "03_graph.mmd"
    png_path = export_dir / "03_graph.png"
    _generate_mermaid(json_path, mmd_path, png_path)
    if mmd_path.exists():
        print("  ✓ 03_graph.mmd")
    if png_path.exists():
        print("  ✓ 03_graph.png")

    # 04_scoring.csv
    scoring_csv_path = export_dir / "04_scoring.csv"
    generate_scoring_csv(json_path, output_path=scoring_csv_path)
    print("  ✓ 04_scoring.csv")

    # 04_scoring_summary.md
    if scoring_csv_path.exists():
        summary_md = generate_summary(scoring_csv_path)
        summary_path = export_dir / "04_scoring_summary.md"
        summary_path.write_text(summary_md)
        print("  ✓ 04_scoring_summary.md")

    # 05_latency/
    data = json.loads(json_path.read_text())
    meta = data.get("metadata", {})
    log_file_name = meta.get("log_file", "")
    log_path = LOGS_DIR / log_file_name if log_file_name else None
    latency_dir = export_dir / "05_latency"
    _generate_latency_audit(log_path, latency_dir)
    print("  ✓ 05_latency/ (summary.md, llm_calls.csv, stages.csv)")

    # 05_turn_diagnostics.md
    diagnostics_path = export_dir / "05_turn_diagnostics.md"
    _generate_turn_diagnostics(json_path, diagnostics_path)
    print("  ✓ 05_turn_diagnostics.md")

    # 06_insights.md — placeholder for reviewer skill
    insights_path = export_dir / "06_insights.md"
    insights_path.write_text(
        "# Interview Insights\n\n"
        "_Generated by /interview-review skill._\n\n"
        "Run the reviewer skill on this export folder to populate this file.\n"
    )
    print("  ✓ 06_insights.md (placeholder)")

    # 99_session.log
    if log_path is not None and log_path.exists():
        shutil.copy2(log_path, export_dir / "99_session.log")
        print("  ✓ 99_session.log")

    print(f"\nExport complete: {export_dir}")
    return export_dir


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export all interview artifacts into a single folder."
    )
    parser.add_argument(
        "json_file",
        nargs="?",
        type=Path,
        help="Path to simulation JSON file (default: most recent)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        help="Output directory (default: reports/interviews/<timestamp>)",
    )
    args = parser.parse_args()

    if args.json_file:
        json_path = args.json_file
    else:
        json_path = _find_most_recent_json()
        print(f"No file specified — using most recent: {json_path}")

    if not json_path.exists():
        print(f"Error: file not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    export_dir = export_interview(json_path, args.output_dir)
    print(f"\nExport folder: {export_dir}")


if __name__ == "__main__":
    main()
