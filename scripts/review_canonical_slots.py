#!/usr/bin/env python3
"""
Manual quality review script for canonical slots.

Extracts data from the dual-graph database for quality assessment.
Outputs JSON to stdout for documentation and analysis.

Usage:
    uv run python scripts/review_canonical_slots.py <session_id>

Bead: 817x (Phase 4: Signal Pool Extensions)
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict

import aiosqlite

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import settings


async def review_canonical_slots(session_id: str) -> Dict[str, Any]:
    """
    Extract all data needed for canonical slot quality review.

    Args:
        session_id: Session ID to review

    Returns:
        Dict with canonical_slots, mappings, edges, and sample_assignments
    """
    db_path = settings.database_path

    if not db_path.exists():
        raise RuntimeError(f"Database not found at {db_path}")

    results = {"session_id": session_id}

    # Query 1: Canonical slots
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT
                s.id as slot_id,
                s.slot_name,
                s.node_type,
                s.description,
                s.support_count,
                s.first_seen_turn,
                s.status
            FROM canonical_slots s
            WHERE s.session_id = ?
            ORDER BY s.status DESC, s.node_type, s.slot_name
            """,
            (session_id,),
        )
        rows = await cursor.fetchall()

    canonical_slots = []
    for row in rows:
        canonical_slots.append(
            {
                "slot_id": row["slot_id"],
                "slot_name": row["slot_name"],
                "node_type": row["node_type"],
                "description": row["description"] or "",
                "support_count": row["support_count"],
                "first_seen_turn": row["first_seen_turn"],
                "status": row["status"],
            }
        )

    results["canonical_slots"] = canonical_slots

    # Query 2: Surface-to-canonical mappings
    # Note: surface_to_slot_mapping has no session_id column, filter through kg_nodes
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT
                m.surface_node_id,
                n.label as surface_label,
                n.node_type as surface_type,
                m.canonical_slot_id,
                s.slot_name as canonical_name,
                s.node_type as canonical_type,
                m.similarity_score,
                m.assigned_turn
            FROM surface_to_slot_mapping m
            JOIN kg_nodes n ON m.surface_node_id = n.id
            JOIN canonical_slots s ON m.canonical_slot_id = s.id
            WHERE n.session_id = ?
            ORDER BY m.canonical_slot_id, m.similarity_score DESC
            """,
            (session_id,),
        )
        rows = await cursor.fetchall()

    mappings = []
    for row in rows:
        mappings.append(
            {
                "surface_node_id": row["surface_node_id"],
                "surface_label": row["surface_label"],
                "surface_type": row["surface_type"],
                "canonical_slot_id": row["canonical_slot_id"],
                "canonical_name": row["canonical_name"],
                "canonical_type": row["canonical_type"],
                "similarity_score": row["similarity_score"],
                "assigned_turn": row["assigned_turn"],
            }
        )

    results["mappings"] = mappings

    # Query 3: Canonical edges
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT
                e.id as edge_id,
                e.source_slot_id,
                s1.slot_name as source_name,
                e.target_slot_id,
                s2.slot_name as target_name,
                e.edge_type,
                e.support_count
            FROM canonical_edges e
            JOIN canonical_slots s1 ON e.source_slot_id = s1.id
            JOIN canonical_slots s2 ON e.target_slot_id = s2.id
            WHERE e.session_id = ?
            ORDER BY e.support_count DESC
            """,
            (session_id,),
        )
        rows = await cursor.fetchall()

    canonical_edges = []
    for row in rows:
        canonical_edges.append(
            {
                "edge_id": row["edge_id"],
                "source_slot_id": row["source_slot_id"],
                "source_name": row["source_name"],
                "target_slot_id": row["target_slot_id"],
                "target_name": row["target_name"],
                "edge_type": row["edge_type"],
                "support_count": row["support_count"],
            }
        )

    results["canonical_edges"] = canonical_edges

    # Query 4: Random sampling for false merge analysis
    # Note: surface_to_slot_mapping has no session_id column, filter through kg_nodes
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT
                m.surface_node_id,
                n.label as surface_label,
                s.slot_name as canonical_name,
                m.similarity_score
            FROM surface_to_slot_mapping m
            JOIN kg_nodes n ON m.surface_node_id = n.id
            JOIN canonical_slots s ON m.canonical_slot_id = s.id
            WHERE n.session_id = ?
            ORDER BY RANDOM()
            LIMIT 50
            """,
            (session_id,),
        )
        rows = await cursor.fetchall()

    sample_assignments = []
    for row in rows:
        sample_assignments.append(
            {
                "surface_node_id": row["surface_node_id"],
                "surface_label": row["surface_label"],
                "canonical_name": row["canonical_name"],
                "similarity_score": row["similarity_score"],
            }
        )

    results["sample_assignments"] = sample_assignments

    # Add summary stats
    results["summary"] = {
        "total_canonical_slots": len(canonical_slots),
        "total_mappings": len(mappings),
        "total_canonical_edges": len(canonical_edges),
        "total_samples": len(sample_assignments),
    }

    return results


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python review_canonical_slots.py <session_id>")
        print(
            "Example: uv run python scripts/review_canonical_slots.py ddc755ec-b286-4448-b7eb-6988a7bcbd52"
        )
        sys.exit(1)

    session_id = sys.argv[1]
    results = await review_canonical_slots(session_id)

    # Output JSON to stdout
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
