#!/usr/bin/env python3
"""SessionEnd hook: capture new fix: commits to bug_patterns.jsonl.

Appends one JSONL entry per new fix commit since the last capture.
Idempotent — skips commits already recorded by commit hash.
"""

import json, subprocess
from pathlib import Path

BUG_LOG = Path(__file__).resolve().parent.parent.parent / "bug_patterns.jsonl"

# Domain routing matching the project CLAUDE.md agent routing table.
DOMAIN_ROUTES = [
    ("signals", [
        "src/signals/", "src/services/node_signal_detection",
        "src/services/methodology_strategy_service", "src/methodologies/scoring.py",
        "src/methodologies/registry.py", "src/services/global_signal_detection",
        "src/services/node_state_tracker.py", "config/methodologies/",
    ]),
    ("pipeline", [
        "src/services/turn_pipeline/", "src/services/session_service.py",
        "src/domain/models/pipeline_contracts.py",
    ]),
    ("extraction", [
        "src/services/extraction_service.py", "src/llm/prompts/",
        "src/domain/models/extraction.py",
    ]),
    ("methodology", ["src/methodologies/", "config/methodologies/"]),
    ("api", ["src/api/", "src/main.py"]),
    ("core", ["src/core/"]),
    ("persistence", ["src/persistence/"]),
    ("llm", ["src/llm/", "config/interview_config.yaml"]),
    ("testing", ["tests/"]),
    ("docs", [".claude/", "docs/"]),
    ("domain-models", ["src/domain/models/"]),
]


def domain_for_file(fp: str) -> str:
    for name, prefixes in DOMAIN_ROUTES:
        for p in prefixes:
            if fp.startswith(p):
                return name
    return "other"


def get_domain(files: list[str]) -> str:
    """Return the most specific domain across changed files."""
    counts = {}
    for f in files:
        d = domain_for_file(f)
        counts[d] = counts.get(d, 0) + 1
    # Pick the domain with the most files, excluding "other" and "docs" if possible
    for skip in ("docs",):
        if skip in counts and len(counts) > 1:
            del counts[skip]
    if "other" in counts and len(counts) > 1:
        del counts["other"]
    # Sort by count descending, pick first
    ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return ranked[0][0] if ranked else "other"


def known_hashes() -> set[str]:
    if not BUG_LOG.exists():
        return set()
    hashes = set()
    with open(BUG_LOG) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if "commit" in entry:
                    hashes.add(entry["commit"])
            except json.JSONDecodeError:
                continue
    return hashes


def main():
    known = known_hashes()

    # Get all fix commits
    result = subprocess.run(
        ["git", "log", "--grep=^fix:", "--all", "--format=%H", "-100"],
        capture_output=True, text=True, cwd=Path(__file__).resolve().parent.parent.parent,
    )
    commits = [c for c in result.stdout.strip().split("\n") if c]

    new_entries = []
    for chash in commits:
        short = chash[:8]
        if short in known:
            continue  # already captured

        # Get commit details
        subj = subprocess.run(
            ["git", "log", "--format=%s", "-1", chash],
            capture_output=True, text=True,
            cwd=Path(__file__).resolve().parent.parent.parent,
        ).stdout.strip()
        date_str = subprocess.run(
            ["git", "log", "--format=%ai", "-1", chash],
            capture_output=True, text=True,
            cwd=Path(__file__).resolve().parent.parent.parent,
        ).stdout.strip()
        body = subprocess.run(
            ["git", "log", "--format=%b", "-1", chash],
            capture_output=True, text=True,
            cwd=Path(__file__).resolve().parent.parent.parent,
        ).stdout.strip()
        changed = subprocess.run(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", chash],
            capture_output=True, text=True,
            cwd=Path(__file__).resolve().parent.parent.parent,
        ).stdout.strip().split("\n")
        changed = [f for f in changed if f]

        # Skip non-bug commits
        skip_words = ["merge", "revert", "automated", "bot", "ruff format", "ruff check",
                      "formatting", "formatting fixes", "docs:", "test:"]
        if any(w in subj.lower() for w in skip_words):
            # Check if it might still be a real fix despite the prefix
            if subj.lower().startswith(("docs:", "test:")):
                if "fix" not in subj.lower().split(":", 1)[1] if ":" in subj else True:
                    continue

        # Extract clean symptom from subject
        symptom = subj.replace("fix: ", "").replace("fix:", "").strip()

        # Extract root cause from body if available
        root_cause = symptom  # fallback
        if body:
            lines = [l.strip("- ").strip() for l in body.split("\n") if l.strip()
                     and not l.startswith("Co-Authored") and not l.startswith("EOF")]
            if lines:
                root_cause = "; ".join(lines[:3])

        domain = get_domain(changed)

        entry = {
            "timestamp": date_str[:10],
            "source": "session_end_hook",
            "commit": short,
            "symptom": symptom[:200],
            "root_cause": root_cause[:300],
            "files": changed[:5],
            "domain": domain,
        }
        new_entries.append(entry)

    if not new_entries:
        return 0

    with open(BUG_LOG, "a") as f:
        for entry in new_entries:
            f.write(json.dumps(entry) + "\n")

    print(f"[capture_fix_commits] Appended {len(new_entries)} new entries to {BUG_LOG}")


if __name__ == "__main__":
    main()
