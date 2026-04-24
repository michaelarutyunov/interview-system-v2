#!/usr/bin/env python3
"""Export all interview artifacts into a single timestamped folder.

Orchestrates the individual generators to produce a complete interview export:
    reports/interviews/<timestamp>/
    ├── 00_meta.yaml
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

from scripts.reporting.generate_transcript import generate_transcript
from scripts.reporting.generate_scoring_csv import generate_scoring_csv
from scripts.reporting.generate_scoring_summary import generate_summary

REPORTS_DIR = Path("reports/interviews")
LOGS_DIR = Path("logs")
SYNTHETIC_DIR = Path("synthetic_interviews")


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


def _generate_causal_chains(json_path: Path, output_path: Path) -> None:
    """Run causal chain extraction and write to output path."""
    # Import and run the inline extraction logic from the skill
    # For now, delegate to a subprocess call to the skill's script
    # TODO: Refactor causal chain extraction into an importable module
    # For the initial implementation, we write a placeholder
    output_path.write_text(
        "# Causal Chain Extraction\n\n"
        f"Source: {json_path.name}\n\n"
        "_Run extract-causal-chains skill to populate this file._\n"
    )


def _generate_mermaid(json_path: Path, mmd_path: Path, png_path: Path) -> None:
    """Generate Mermaid diagram and render PNG."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.reporting.generate_mermaid_graph",
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

    # Run the latency audit on this specific log file
    # The existing latency_audit.py processes ALL logs; we need a single-log version
    # For now, we copy the log and note that full audit requires running latency_audit.py
    latency_dir.mkdir(parents=True, exist_ok=True)
    (latency_dir / "summary.md").write_text(
        f"# Latency Audit\n\n"
        f"Log file: {log_path.name}\n\n"
        f"_Run `uv run python scripts/eval/latency_audit.py` for full audit._\n"
        f"_Per-session latency parsing to be implemented._\n"
    )


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

    # 01_transcript.md
    transcript_path = export_dir / "01_transcript.md"
    generate_transcript(json_path, output_path=transcript_path)
    print("  ✓ 01_transcript.md")

    # 02_causal_chains.md
    chains_path = export_dir / "02_causal_chains.md"
    _generate_causal_chains(json_path, chains_path)
    print("  ✓ 02_causal_chains.md (placeholder)")

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
    print("  ✓ 05_latency/")

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
