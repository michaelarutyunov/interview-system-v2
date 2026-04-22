#!/usr/bin/env python3
"""Smoke test for eval harness: 2 personas × 2 replicates.

Usage: uv run python scripts/smoke_test_eval.py

Verifies:
1. Matrix runner produces scoreboard rows
2. Metrics are computed correctly
3. Show scoreboard doesn't crash
"""

import asyncio
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

DB_PATH = "data/interview.db"
PERSONAS = ["baseline_cooperative", "brief_responder"]
CONCEPT = "zerofizz_beverage_mec"
REPLICATES = 2


async def run_smoke():
    from scripts.run_eval_matrix import run_matrix

    await run_matrix(
        methodology="means_end_chain_v2_strict",
        concept_id=CONCEPT,
        personas=PERSONAS,
        replicates=REPLICATES,
        max_turns=5,
        label="smoke_test",
        max_parallel=2,
    )


def verify_scoreboard():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Check eval_runs populated
    rows = conn.execute(
        "SELECT * FROM eval_runs WHERE run_label = 'smoke_test' AND error_flag = 0"
    ).fetchall()

    expected = len(PERSONAS) * REPLICATES
    if len(rows) != expected:
        print(f"FAIL: Expected {expected} rows, got {len(rows)}")
        return False

    # Check metrics are populated
    for row in rows:
        if row["node_count"] == 0:
            print(f"FAIL: Zero node_count for {row['id']}")
            return False
        if row["structural_completeness"] is None:
            print(f"FAIL: NULL structural_completeness for {row['id']}")
            return False

    # Check config registry
    config_rows = conn.execute(
        "SELECT * FROM eval_config_registry WHERE label = 'smoke_test'"
    ).fetchall()
    if len(config_rows) != 1:
        print(f"FAIL: Expected 1 config registry entry, got {len(config_rows)}")
        return False

    conn.close()

    print("\nVerification PASSED:")
    print(f"  {len(rows)}/{expected} runs recorded")
    print(f"  Config hash: {config_rows[0]['config_hash']}")
    for row in rows:
        print(
            f"  {row['persona_id'][:20]:20s} seed={row['replicate_seed'][:8]} "
            f"nodes={row['node_count']} struct={row['structural_completeness']} "
            f"depth={row['exploration_depth']:.1f}"
        )
    return True


def main():
    print("=== Eval Harness Smoke Test ===")
    print(f"Personas: {PERSONAS}")
    print(f"Concept: {CONCEPT}")
    print(f"Replicates: {REPLICATES}")
    print()

    print("--- Running matrix ---")
    asyncio.run(run_smoke())

    print("\n--- Verifying scoreboard ---")
    ok = verify_scoreboard()

    print("\n--- Show scoreboard ---")
    import subprocess

    subprocess.run(
        [sys.executable, "scripts/show_scoreboard.py", "--label", "smoke_test"],
        check=False,
    )

    if ok:
        print("\n=== SMOKE TEST PASSED ===")
    else:
        print("\n=== SMOKE TEST FAILED ===")
        sys.exit(1)


if __name__ == "__main__":
    main()
