#!/usr/bin/env python3
"""Doc drift detector.

Warns when source files have been modified more than once since their
corresponding doc was last updated. One deferred update is acceptable;
two or more signals drift.

Usage:
    uv run python scripts/check_doc_drift.py [--repo-root PATH] [--config PATH]

Exit code: always 0 (warns but never blocks).
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class DriftWarning:
    doc: str
    changes: list[str]  # list of "hash message" strings


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def run_git(cmd: list[str], cwd: Path) -> str:
    """Run a git command and return stdout. Returns empty string on error."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return ""


def get_last_doc_commit(doc: str, repo_root: Path) -> str | None:
    """Return the hash of the last commit that touched `doc`, or None."""
    output = run_git(["git", "log", "-1", "--format=%H", "--", doc], cwd=repo_root)
    result = output.strip()
    return result if result else None


def get_source_changes_since(
    since_commit: str | None,
    source_globs: list[str],
    repo_root: Path,
) -> list[str]:
    """Return commits that touched any source glob since `since_commit`.

    Returns empty list if since_commit is None (doc never committed).
    Each entry is "hash short-message".
    """
    if since_commit is None:
        return []

    cmd = [
        "git", "log",
        "--oneline",
        f"{since_commit}..HEAD",
        "--",
        *source_globs,
    ]
    output = run_git(cmd, cwd=repo_root)
    lines = [line for line in output.splitlines() if line.strip()]
    return lines


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def load_mapping(config_path: Path) -> list[dict]:
    """Load and return the mappings list from doc_mapping.yaml."""
    if not config_path.exists():
        raise FileNotFoundError(f"Mapping config not found: {config_path}")
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return data.get("mappings", [])


def check_drift(
    mapping: list[dict],
    repo_root: Path,
) -> list[DriftWarning]:
    """Check all mappings for drift. Returns list of DriftWarning."""
    warnings: list[DriftWarning] = []

    for entry in mapping:
        doc = entry["doc"]
        sources = entry["sources"]

        last_doc_commit = get_last_doc_commit(doc, repo_root)
        if last_doc_commit is None:
            # Doc not yet committed — skip
            continue

        changes = get_source_changes_since(last_doc_commit, sources, repo_root)

        # Allow one deferred update; two or more is drift
        if len(changes) > 1:
            warnings.append(DriftWarning(doc=doc, changes=changes))

    return warnings


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def format_warnings(warnings: list[DriftWarning]) -> str:
    if not warnings:
        return ""
    lines = ["⚠  Doc drift detected:"]
    for w in warnings:
        lines.append(f"  {w.doc} — {len(w.changes)} source changes since last update")
        for change in w.changes:
            lines.append(f"    → {change}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Check for doc drift.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="Path to repository root (default: current directory)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to doc_mapping.yaml (default: <repo-root>/.claude/doc_mapping.yaml)",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    config_path = args.config or repo_root / ".claude" / "doc_mapping.yaml"

    try:
        mapping = load_mapping(config_path)
    except FileNotFoundError as e:
        print(f"check_doc_drift: {e}", file=sys.stderr)
        sys.exit(0)

    warnings = check_drift(mapping, repo_root)
    output = format_warnings(warnings)
    if output:
        print(output)

    sys.exit(0)  # Always exit 0 — warn, never block


if __name__ == "__main__":
    main()
