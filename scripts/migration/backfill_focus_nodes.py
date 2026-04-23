#!/usr/bin/env python3
"""Backfill focus_node_id and focus_node_label into existing simulation JSON files.

Reads the selected node-level entry from score_decomposition (the entry with
selected=True and a non-empty node_id) and writes it back to each turn as
focus_node_id / focus_node_label.

This is a one-time migration for JSON files produced before focus_node_id was
added to SimulationTurn. Safe to re-run — already-patched turns are skipped.

Usage:
    python scripts/migration/backfill_focus_nodes.py                    # all files
    python scripts/migration/backfill_focus_nodes.py --dry-run          # preview only
    python scripts/migration/backfill_focus_nodes.py synthetic_interviews/20260411_*.json
"""

import json
import sys
from pathlib import Path


def backfill_file(path: Path, dry_run: bool = False) -> tuple[int, int]:
    """Backfill focus node fields in a single JSON file.

    Returns:
        (turns_patched, turns_already_set)
    """
    data = json.loads(path.read_text())
    nodes_by_id = {n["id"]: n for n in data["graph"]["nodes"]}

    patched = 0
    already_set = 0

    for turn in data["turns"]:
        if turn.get("focus_node_id"):
            already_set += 1
            continue

        decomp = turn.get("score_decomposition") or []
        node_id = None
        for entry in decomp:
            if entry.get("selected") and entry.get("node_id"):
                node_id = entry["node_id"]
                break

        if node_id:
            node_data = nodes_by_id.get(node_id, {})
            label = node_data.get("label")
            if not dry_run:
                turn["focus_node_id"] = node_id
                turn["focus_node_label"] = label
            patched += 1

    if patched > 0 and not dry_run:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    return patched, already_set


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv

    if args:
        files = [Path(a) for a in args]
    else:
        files = sorted(Path("synthetic_interviews").glob("*.json"))

    if not files:
        print("No JSON files found.")
        return

    if dry_run:
        print("DRY RUN — no files will be modified\n")

    total_patched = 0
    total_already = 0

    for f in files:
        patched, already = backfill_file(f, dry_run=dry_run)
        status = "DRY" if dry_run else "patched"
        print(f"{f.name}: {patched} turns {status}, {already} already set")
        total_patched += patched
        total_already += already

    print(
        f"\nTotal: {total_patched} turns patched, {total_already} already had focus node"
    )


if __name__ == "__main__":
    main()
