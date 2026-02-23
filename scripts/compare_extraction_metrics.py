#!/usr/bin/env python3
"""
Compare extraction metrics across multiple interview sessions.

Queries the SQLite database directly for surface and canonical graph metrics.
Outputs a markdown table comparing sessions side-by-side.

Usage:
    uv run python scripts/compare_extraction_metrics.py <session_id_1> [session_id_2] ...

Example:
    uv run python scripts/compare_extraction_metrics.py \
        abc123 def456 ghi789 jkl012

Bead: pong (Phase 4: Signal Pool Extensions)
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import settings


async def get_surface_metrics(db_path: Path, session_id: str) -> Dict[str, Any]:
    """Query surface graph metrics for a session.

    Args:
        db_path: Path to SQLite database
        session_id: Session ID to query

    Returns:
        Dict with node_count, edge_count, edge_node_ratio, orphan_count, orphan_pct
    """
    async with aiosqlite.connect(db_path) as db:
        # Node count
        cursor = await db.execute(
            "SELECT COUNT(*) FROM kg_nodes WHERE session_id = ? AND superseded_by IS NULL",
            (session_id,),
        )
        row = await cursor.fetchone()
        node_count = row[0] if row else 0

        # Edge count
        cursor = await db.execute(
            "SELECT COUNT(*) FROM kg_edges WHERE session_id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        edge_count = row[0] if row else 0

        # Orphan count (nodes with no edges)
        cursor = await db.execute(
            """
            SELECT COUNT(*) FROM kg_nodes n
            WHERE n.session_id = ? AND n.superseded_by IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM kg_edges e
                  WHERE e.session_id = ?
                    AND (e.source_node_id = n.id OR e.target_node_id = n.id)
              )
            """,
            (session_id, session_id),
        )
        row = await cursor.fetchone()
        orphan_count = row[0] if row else 0

    # Edge/node ratio
    edge_node_ratio = edge_count / node_count if node_count > 0 else 0.0

    # Orphan percentage
    orphan_pct = (orphan_count / node_count * 100) if node_count > 0 else 0.0

    return {
        "node_count": node_count,
        "edge_count": edge_count,
        "edge_node_ratio": round(edge_node_ratio, 2),
        "orphan_count": orphan_count,
        "orphan_pct": round(orphan_pct, 1),
    }


async def get_canonical_metrics(db_path: Path, session_id: str) -> Optional[Dict[str, Any]]:
    """Query canonical graph metrics for a session.

    Args:
        db_path: Path to SQLite database
        session_id: Session ID to query

    Returns:
        Dict with concept_count, canonical_edge_count, edge_concept_ratio,
        orphan_count, orphan_pct, or None if no canonical data exists
    """
    async with aiosqlite.connect(db_path) as db:
        # Canonical slot count (active only)
        cursor = await db.execute(
            "SELECT COUNT(*) FROM canonical_slots WHERE session_id = ? AND status = 'active'",
            (session_id,),
        )
        row = await cursor.fetchone()
        concept_count = row[0] if row else 0

        # If no active slots, canonical graphs not populated for this session
        if concept_count == 0:
            return None

        # Canonical edge count
        cursor = await db.execute(
            "SELECT COUNT(*) FROM canonical_edges WHERE session_id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        canonical_edge_count = row[0] if row else 0

        # Canonical orphan count (slots with no edges)
        cursor = await db.execute(
            """
            SELECT COUNT(*) FROM canonical_slots s
            WHERE s.session_id = ? AND s.status = 'active'
              AND NOT EXISTS (
                  SELECT 1 FROM canonical_edges e
                  WHERE e.session_id = ?
                    AND (e.source_slot_id = s.id OR e.target_slot_id = s.id)
              )
            """,
            (session_id, session_id),
        )
        row = await cursor.fetchone()
        orphan_count = row[0] if row else 0

    # Edge/concept ratio
    edge_concept_ratio = canonical_edge_count / concept_count if concept_count > 0 else 0.0

    # Orphan percentage
    orphan_pct = (orphan_count / concept_count * 100) if concept_count > 0 else 0.0

    return {
        "concept_count": concept_count,
        "canonical_edge_count": canonical_edge_count,
        "edge_concept_ratio": round(edge_concept_ratio, 2),
        "orphan_count": orphan_count,
        "orphan_pct": round(orphan_pct, 1),
    }


async def compare_sessions(session_ids: List[str]) -> None:
    """Compare metrics across multiple sessions.

    Args:
        session_ids: List of session IDs to compare

    Raises:
        RuntimeError: If any session_id is not found in database
    """
    db_path = settings.database_path

    if not db_path.exists():
        raise RuntimeError(f"Database not found at {db_path}")

    # Collect all metrics
    results = []
    for session_id in session_ids:
        surface = await get_surface_metrics(db_path, session_id)

        # Verify session exists (has at least some nodes)
        if surface["node_count"] == 0:
            raise RuntimeError(f"Session {session_id} not found in database")

        canonical = await get_canonical_metrics(db_path, session_id)

        results.append(
            {
                "session_id": session_id,
                "surface": surface,
                "canonical": canonical,
            }
        )

    # Print comparison table
    print_comparison_table(results)


def print_comparison_table(results: List[Dict[str, Any]]) -> None:
    """Print a markdown comparison table.

    Args:
        results: List of session result dicts with surface and canonical metrics
    """
    print("\n# Interview Metrics Comparison\n")

    # Header row
    print("| Metric |", end="")
    for r in results:
        sid = r["session_id"][:8]  # Short ID
        print(f" {sid} |", end="")
    print("\n" + "|" + "---------|" * (len(results) + 1))

    # Surface metrics
    surface_metrics = [
        ("Surface Nodes", "node_count"),
        ("Surface Edges", "edge_count"),
        ("Edge/Node Ratio", "edge_node_ratio"),
        ("Surface Orphans", "orphan_count"),
        ("Orphan %", "orphan_pct"),
    ]

    for label, key in surface_metrics:
        print(f"| {label} |", end="")
        for r in results:
            val = r["surface"][key]
            print(f" {val} |", end="")
        print()

    print("|  |" + " |" * len(results))  # Separator

    # Canonical metrics (may be None for some sessions)
    canonical_metrics = [
        ("Canonical Concepts", "concept_count"),
        ("Canonical Edges", "canonical_edge_count"),
        ("Edge/Concept Ratio", "edge_concept_ratio"),
        ("Canonical Orphans", "orphan_count"),
        ("Orphan %", "orphan_pct"),
    ]

    for label, key in canonical_metrics:
        print(f"| {label} |", end="")
        for r in results:
            canonical = r["canonical"]
            if canonical is None:
                val = "—"
            else:
                val = canonical[key]
            print(f" {val} |", end="")
        print()

    # Comparison metrics (if we have canonical data for all sessions)
    if all(r["canonical"] is not None for r in results):
        print("|  |" + " |" * len(results))  # Separator

        print("| Node Reduction % |", end="")
        for r in results:
            surface_nodes = r["surface"]["node_count"]
            canonical_nodes = r["canonical"]["concept_count"]
            reduction = (1 - canonical_nodes / surface_nodes) * 100 if surface_nodes > 0 else 0
            print(f" {reduction:.1f}% |", end="")
        print()

        print("| Edge Improvement % |", end="")
        for r in results:
            surface_edges = r["surface"]["edge_count"]
            canonical_edges = r["canonical"]["canonical_edge_count"]
            improvement = (1 - canonical_edges / surface_edges) * 100 if surface_edges > 0 else 0
            print(f" {improvement:.1f}% |", end="")
        print()

        print("| Orphan Improvement % |", end="")
        for r in results:
            surface_orphan_pct = r["surface"]["orphan_pct"]
            canonical_orphan_pct = r["canonical"]["orphan_pct"]
            improvement = surface_orphan_pct - canonical_orphan_pct
            print(f" {improvement:.1f}% |", end="")
        print()

    print()


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python compare_extraction_metrics.py <session_id_1> [session_id_2] ...")
        sys.exit(1)

    session_ids = sys.argv[1:]
    await compare_sessions(session_ids)


if __name__ == "__main__":
    asyncio.run(main())
