#!/usr/bin/env python3
"""Verify paired-label baseline runs work after eval_runs schema migration.

This tests the schema fix directly by inserting rows with the same
(config_hash, persona_id, replicate_seed) but different run_label values.

Usage: uv run python scripts/eval/test_paired_labels.py
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

DB_PATH = "data/interview.db"


def test_paired_labels():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Ensure schema is migrated
    cursor = conn.execute("PRAGMA table_info(eval_runs)")
    columns = {row["name"]: row for row in cursor.fetchall()}
    if "run_label" not in columns or columns["run_label"]["notnull"] == 0:
        print("FAIL: eval_runs schema not migrated (run_label is nullable)")
        conn.close()
        sys.exit(1)

    # Insert two rows with same config_hash/persona/seed but different labels
    test_hash = "test_hash_12345678"
    test_persona = "test_persona"
    test_seed = "seed12345678"

    # Clean up any prior test rows
    conn.execute(
        "DELETE FROM eval_runs WHERE config_hash = ?",
        (test_hash,),
    )
    conn.commit()

    for label in ["baseline_A", "baseline_B"]:
        run_id = f"{test_hash}_{test_persona}_{test_seed}_{label}"
        conn.execute(
            """INSERT INTO eval_runs
               (id, config_hash, methodology, concept_id, persona_id, replicate_seed,
                run_label, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (run_id, test_hash, "mec", "test_concept", test_persona, test_seed, label),
        )
    conn.commit()

    # Verify both rows exist
    rows = conn.execute(
        "SELECT run_label FROM eval_runs WHERE config_hash = ? ORDER BY run_label",
        (test_hash,),
    ).fetchall()

    if len(rows) != 2:
        print(f"FAIL: Expected 2 rows, got {len(rows)}")
        conn.close()
        sys.exit(1)

    labels = [r["run_label"] for r in rows]
    if labels != ["baseline_A", "baseline_B"]:
        print(f"FAIL: Expected labels ['baseline_A', 'baseline_B'], got {labels}")
        conn.close()
        sys.exit(1)

    # Verify duplicate label still fails
    duplicate_id = f"{test_hash}_{test_persona}_{test_seed}_baseline_A"
    try:
        conn.execute(
            """INSERT INTO eval_runs
               (id, config_hash, methodology, concept_id, persona_id, replicate_seed,
                run_label, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (
                duplicate_id,
                test_hash,
                "mec",
                "test_concept",
                test_persona,
                test_seed,
                "baseline_A",
            ),
        )
        conn.commit()
        print("FAIL: Duplicate label insert should have raised IntegrityError")
        conn.close()
        sys.exit(1)
    except sqlite3.IntegrityError:
        print("OK: Duplicate label correctly rejected")

    # Clean up test rows
    conn.execute("DELETE FROM eval_runs WHERE config_hash = ?", (test_hash,))
    conn.commit()
    conn.close()

    print("PASSED: Paired labels coexist; duplicate labels rejected")


if __name__ == "__main__":
    test_paired_labels()
