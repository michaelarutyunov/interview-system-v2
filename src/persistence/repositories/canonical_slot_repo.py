"""
Repository for canonical graph persistence (dual-graph architecture).

Handles CRUD operations on canonical_slots, surface_to_slot_mapping,
and canonical_edges tables. Uses aiosqlite for async SQLite access.

IMPLEMENTATION NOTES:
- Follows SessionRepository pattern: accepts db_path and manages its own connections
- Each method creates its own connection via async context manager
- Fail-fast error handling: no try/except around DB operations
"""

import json
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import aiosqlite
import numpy as np
import structlog

from src.core.config import settings
from src.domain.models.canonical_graph import (
    CanonicalSlot,
    SlotMapping,
    CanonicalEdge,
)

log = structlog.get_logger(__name__)


class CanonicalSlotRepository:
    """
    Repository for canonical slots and mappings.

    Provides CRUD operations on SQLite tables:
    - canonical_slots: Abstract concept slots (candidate → active lifecycle)
    - surface_to_slot_mapping: Maps surface kg_nodes to canonical slots
    - canonical_edges: Aggregated edges between canonical slots

    Follows SessionRepository pattern: accepts db_path and manages its own
    connections internally using async context managers.
    """

    def __init__(self, db_path: str):
        """
        Initialize canonical slot repository.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

    # ==================== CANONICAL SLOT OPERATIONS ====================

    async def create_slot(
        self,
        session_id: str,
        slot_name: str,
        description: str,
        node_type: str,
        first_seen_turn: int,
        embedding: Optional[np.ndarray] = None,
        status: str = "candidate",
    ) -> CanonicalSlot:
        """
        Create a new canonical slot.

        Args:
            session_id: Session ID
            slot_name: LLM-generated canonical name (e.g., 'energy_stability')
            description: LLM-generated description
            node_type: Node type (attribute, consequence, value) - preserves methodology hierarchy
            first_seen_turn: Turn when slot was first discovered
            embedding: Optional numpy embedding (float32 array). Serialized via tobytes() if provided.
            status: 'candidate' or 'active' (default: 'candidate')

        Returns:
            Created CanonicalSlot
        """
        slot_id = f"slot_{uuid4().hex[:12]}"

        # Serialize embedding if provided
        embedding_blob = embedding.tobytes() if embedding is not None else None

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO canonical_slots (
                    id, session_id, slot_name, description, node_type,
                    status, support_count, first_seen_turn, promoted_turn, embedding
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    slot_id,
                    session_id,
                    slot_name,
                    description,
                    node_type,
                    status,
                    0,  # support_count starts at 0
                    first_seen_turn,
                    None,  # promoted_turn initially None
                    embedding_blob,
                ),
            )
            await db.commit()

        log.info(
            "canonical_slot_created",
            slot_id=slot_id,
            slot_name=slot_name,
            node_type=node_type,
            status=status,
        )

        slot = await self.get_slot(slot_id)
        if slot is None:
            raise RuntimeError(f"Slot creation failed: slot {slot_id} not found after INSERT")
        return slot

    async def get_slot(self, slot_id: str) -> Optional[CanonicalSlot]:
        """
        Get a canonical slot by ID.

        Args:
            slot_id: Slot ID

        Returns:
            CanonicalSlot or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM canonical_slots WHERE id = ?",
                (slot_id,),
            )
            row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_slot(row)

    async def get_active_slots(
        self, session_id: str, node_type: Optional[str] = None
    ) -> List[CanonicalSlot]:
        """
        Get all active slots for a session, optionally filtered by node_type.

        Args:
            session_id: Session ID
            node_type: Optional node type filter (attribute, consequence, value)

        Returns:
            List of active CanonicalSlot objects
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if node_type:
                cursor = await db.execute(
                    """
                    SELECT * FROM canonical_slots
                    WHERE session_id = ? AND status = 'active' AND node_type = ?
                    ORDER BY created_at DESC
                    """,
                    (session_id, node_type),
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT * FROM canonical_slots
                    WHERE session_id = ? AND status = 'active'
                    ORDER BY created_at DESC
                    """,
                    (session_id,),
                )

            rows = await cursor.fetchall()

        return [self._row_to_slot(row) for row in rows]

    async def find_slot_by_name_and_type(
        self, session_id: str, slot_name: str, node_type: str
    ) -> Optional[CanonicalSlot]:
        """
        Find a canonical slot by exact slot_name and node_type match.

        This is the recommended method for slot deduplication as it ensures
        slots of different types (e.g., attribute vs instrumental_value) are not
        merged incorrectly. Prevents UNIQUE constraint violations by checking
        existence before attempting to create.

        Args:
            session_id: Session ID
            slot_name: Slot name to find (exact match)
            node_type: Node type to match

        Returns:
            CanonicalSlot or None if not found

        Note:
            Deduplication check prevents UNIQUE constraint violations.
            Pattern follows GraphRepository.find_node_by_label_and_type().
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM canonical_slots
                WHERE session_id = ? AND slot_name = ? AND node_type = ?
                """,
                (session_id, slot_name, node_type),
            )
            row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_slot(row)

    async def find_similar_slots(
        self,
        session_id: str,
        node_type: str,
        embedding: np.ndarray,
        threshold: Optional[float] = None,
        status: str = "active",
    ) -> List[Tuple[CanonicalSlot, float]]:
        """
        Find slots similar to the given embedding via cosine similarity.

        O(N) brute-force search: loads all embeddings of matching node_type
        and computes cosine similarity in Python. Accepted for MVP - see
        AMBIGUITY RESOLUTION 2026-02-07.

        Args:
            session_id: Session ID
            node_type: Node type filter (only compare slots of same type)
            embedding: Query embedding (numpy float32 array)
            threshold: Optional similarity threshold (default: settings.canonical_similarity_threshold)
            status: Slot status filter (default: 'active')

        Returns:
            List of (CanonicalSlot, similarity_score) tuples above threshold,
            sorted descending by similarity
        """
        if threshold is None:
            # Read from config, NOT hardcoded (AMBIGUITY RESOLUTION 2026-02-07)
            threshold = settings.canonical_similarity_threshold

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM canonical_slots
                WHERE session_id = ? AND node_type = ? AND status = ? AND embedding IS NOT NULL
                """,
                (session_id, node_type, status),
            )
            rows = await cursor.fetchall()

        # Compute cosine similarity for each slot
        similar_slots = []
        for row in rows:
            slot = self._row_to_slot(row)
            if slot.embedding is None:
                continue

            # Deserialize embedding: all-MiniLM-L6-v2 (384-dim float32)
            slot_embedding = np.frombuffer(slot.embedding, dtype=np.float32)
            similarity = self._cosine_similarity(embedding, slot_embedding)

            if similarity >= threshold:
                similar_slots.append((slot, similarity))

        # Sort descending by similarity
        similar_slots.sort(key=lambda x: x[1], reverse=True)

        return similar_slots

    async def map_surface_to_slot(
        self,
        surface_node_id: str,
        slot_id: str,
        similarity_score: float,
        assigned_turn: int,
    ) -> None:
        """
        Map a surface node to a canonical slot, incrementing support_count.

        Args:
            surface_node_id: ID of the surface node (from kg_nodes table)
            slot_id: ID of the canonical slot (from canonical_slots table)
            similarity_score: Cosine similarity score (0.0-1.0)
            assigned_turn: Turn when this mapping was created
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Insert mapping (INSERT OR REPLACE handles re-mapping if needed)
            await db.execute(
                """
                INSERT OR REPLACE INTO surface_to_slot_mapping
                (surface_node_id, canonical_slot_id, similarity_score, assigned_turn)
                VALUES (?, ?, ?, ?)
                """,
                (surface_node_id, slot_id, similarity_score, assigned_turn),
            )

            # Increment support_count
            await db.execute(
                "UPDATE canonical_slots SET support_count = support_count + 1 WHERE id = ?",
                (slot_id,),
            )
            await db.commit()

        log.info(
            "surface_node_mapped",
            surface_node_id=surface_node_id,
            slot_id=slot_id,
            similarity=round(similarity_score, 3),
        )

    async def promote_slot(self, slot_id: str, turn_number: int) -> None:
        """
        Promote a candidate slot to active status.

        Args:
            slot_id: Slot ID to promote
            turn_number: Current turn number (recorded as promoted_turn)
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE canonical_slots
                SET status = 'active', promoted_turn = ?, promoted_at = datetime('now')
                WHERE id = ?
                """,
                (turn_number, slot_id),
            )
            await db.commit()

        log.info("slot_promoted", slot_id=slot_id, turn=turn_number)

    # ==================== MAPPING OPERATIONS ====================

    async def get_mapping_for_node(self, surface_node_id: str) -> Optional[SlotMapping]:
        """
        Get the canonical slot mapping for a surface node.

        Args:
            surface_node_id: Surface node ID (from kg_nodes table)

        Returns:
            SlotMapping or None if not mapped
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM surface_to_slot_mapping WHERE surface_node_id = ?
                """,
                (surface_node_id,),
            )
            row = await cursor.fetchone()

        if not row:
            return None

        return SlotMapping(
            surface_node_id=row["surface_node_id"],
            canonical_slot_id=row["canonical_slot_id"],
            similarity_score=row["similarity_score"],
            assigned_turn=row["assigned_turn"],
        )

    async def get_slot_saturation_map(self, session_id: str) -> Dict[str, int]:
        """
        Get support_count for each surface node's canonical slot.

        Returns a mapping of surface_node_id to the support_count of the
        canonical slot it maps to. This is used for node differentiation
        signals to break scoring ties among same-turn new nodes.

        Args:
            session_id: Session ID

        Returns:
            Dict mapping surface_node_id to support_count of its canonical slot.
            Empty dict if session has no mappings.
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT m.surface_node_id, s.support_count
                FROM surface_to_slot_mapping m
                JOIN canonical_slots s ON m.canonical_slot_id = s.id
                WHERE s.session_id = ?
                """,
                (session_id,),
            )
            rows = await cursor.fetchall()

        return {row["surface_node_id"]: row["support_count"] for row in rows}

    # ==================== CANONICAL EDGE OPERATIONS ====================

    async def add_or_update_canonical_edge(
        self,
        session_id: str,
        source_slot_id: str,
        target_slot_id: str,
        edge_type: str,
        surface_edge_id: str,
    ) -> CanonicalEdge:
        """
        Add or update a canonical edge, aggregating surface edges.

        SELECT WHERE session_id, source_slot_id, target_slot_id, edge_type.
        - If exists: support_count += 1, append surface_edge_id to JSON array, UPDATE updated_at
        - If not exists: INSERT with support_count=1, surface_edge_ids=[surface_edge_id]

        The UNIQUE constraint on (session_id, source_slot_id, target_slot_id, edge_type)
        prevents duplicates and enables this UPSERT pattern.

        Args:
            session_id: Session ID
            source_slot_id: Source canonical slot ID
            target_slot_id: Target canonical slot ID
            edge_type: Edge type (leads_to, revises, etc.)
            surface_edge_id: Surface edge ID to add to provenance

        Returns:
            CanonicalEdge (created or updated)

        REFERENCE: AMBIGUITY RESOLUTION 2026-02-07 for full semantics
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # Check if edge exists
            cursor = await db.execute(
                """
                SELECT * FROM canonical_edges
                WHERE session_id = ? AND source_slot_id = ? AND target_slot_id = ? AND edge_type = ?
                """,
                (session_id, source_slot_id, target_slot_id, edge_type),
            )
            row = await cursor.fetchone()

            if row:
                # Edge exists: update
                edge_id = row["id"]
                current_count = row["support_count"]
                current_edges = json.loads(row["surface_edge_ids"])

                # Append new surface edge ID (avoid duplicates)
                if surface_edge_id not in current_edges:
                    current_edges.append(surface_edge_id)

                await db.execute(
                    """
                    UPDATE canonical_edges
                    SET support_count = ?, surface_edge_ids = ?, updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (current_count + 1, json.dumps(current_edges), edge_id),
                )
                await db.commit()

                log.debug(
                    "canonical_edge_updated",
                    edge_id=edge_id,
                    support_count=current_count + 1,
                )

            else:
                # Create new edge
                edge_id = f"cedge_{uuid4().hex[:12]}"

                await db.execute(
                    """
                    INSERT INTO canonical_edges
                    (id, session_id, source_slot_id, target_slot_id, edge_type,
                     support_count, surface_edge_ids)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        edge_id,
                        session_id,
                        source_slot_id,
                        target_slot_id,
                        edge_type,
                        1,
                        json.dumps([surface_edge_id]),
                    ),
                )
                await db.commit()

                log.info(
                    "canonical_edge_created",
                    edge_id=edge_id,
                    source=source_slot_id,
                    target=target_slot_id,
                    type=edge_type,
                )

        edge = await self.get_canonical_edge(edge_id)
        if edge is None:
            raise RuntimeError(f"Canonical edge {edge_id} not found after operation")
        return edge

    async def get_canonical_edge(self, edge_id: str) -> Optional[CanonicalEdge]:
        """Get a canonical edge by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM canonical_edges WHERE id = ?",
                (edge_id,),
            )
            row = await cursor.fetchone()

        if not row:
            return None

        return CanonicalEdge(
            id=row["id"],
            session_id=row["session_id"],
            source_slot_id=row["source_slot_id"],
            target_slot_id=row["target_slot_id"],
            edge_type=row["edge_type"],
            support_count=row["support_count"],
            surface_edge_ids=json.loads(row["surface_edge_ids"]) if row["surface_edge_ids"] else [],
        )

    async def get_canonical_edges(self, session_id: str) -> List[CanonicalEdge]:
        """
        Get all canonical edges for a session.

        Args:
            session_id: Session ID

        Returns:
            List of CanonicalEdge objects
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM canonical_edges WHERE session_id = ?",
                (session_id,),
            )
            rows = await cursor.fetchall()

        return [
            CanonicalEdge(
                id=row["id"],
                session_id=row["session_id"],
                source_slot_id=row["source_slot_id"],
                target_slot_id=row["target_slot_id"],
                edge_type=row["edge_type"],
                support_count=row["support_count"],
                surface_edge_ids=json.loads(row["surface_edge_ids"])
                if row["surface_edge_ids"]
                else [],
            )
            for row in rows
        ]

    # ==================== DUAL-GRAPH REPORTING METHODS ====================

    async def get_slots_with_provenance(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get active canonical slots with their surface node provenance.

        Returns active slots with list of surface_node_ids that map to each slot.

        Args:
            session_id: Session ID

        Returns:
            List of slot dicts with surface_node_ids:
            {slot_id, slot_name, node_type, support_count, surface_node_ids: [...]}
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT
                    s.id as slot_id,
                    s.slot_name,
                    s.node_type,
                    s.support_count,
                    s.status,
                    GROUP_CONCAT(m.surface_node_id) as surface_node_ids
                FROM canonical_slots s
                LEFT JOIN surface_to_slot_mapping m ON s.id = m.canonical_slot_id
                WHERE s.session_id = ? AND s.status = 'active'
                GROUP BY s.id
                ORDER BY s.support_count DESC
                """,
                (session_id,),
            )
            rows = await cursor.fetchall()

        result = []
        for row in rows:
            surface_ids = row["surface_node_ids"].split(",") if row["surface_node_ids"] else []
            result.append(
                {
                    "slot_id": row["slot_id"],
                    "slot_name": row["slot_name"],
                    "node_type": row["node_type"],
                    "support_count": row["support_count"],
                    "status": row["status"],
                    "surface_node_ids": surface_ids,
                }
            )

        return result

    async def get_edges_with_metadata(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get canonical edges with surface edge metadata.

        Returns canonical edges with surface_edge_ids and computed
        average confidence from the underlying surface edges.

        Args:
            session_id: Session ID

        Returns:
            List of edge dicts with metadata:
            {edge_id, source_slot_id, target_slot_id, edge_type, support_count,
             surface_edge_ids: [...], avg_confidence}

        Note:
            avg_confidence is computed from surface edges in kg_edges table.
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT
                    e.id as edge_id,
                    e.source_slot_id,
                    e.target_slot_id,
                    e.edge_type,
                    e.support_count,
                    e.surface_edge_ids
                FROM canonical_edges e
                WHERE e.session_id = ?
                ORDER BY e.support_count DESC
                """,
                (session_id,),
            )
            rows = await cursor.fetchall()

            result = []
            for row in rows:
                surface_edge_ids = json.loads(row["surface_edge_ids"])
                avg_confidence = 0.0

                # Compute avg confidence from surface edges
                if surface_edge_ids:
                    placeholders = ",".join("?" * len(surface_edge_ids))
                    cursor2 = await db.execute(
                        f"""
                        SELECT AVG(confidence) as avg_conf
                        FROM kg_edges
                        WHERE id IN ({placeholders})
                        """,
                        surface_edge_ids,
                    )
                    conf_row = await cursor2.fetchone()
                    if conf_row and conf_row["avg_conf"]:
                        avg_confidence = round(conf_row["avg_conf"], 3)

                result.append(
                    {
                        "edge_id": row["edge_id"],
                        "source_slot_id": row["source_slot_id"],
                        "target_slot_id": row["target_slot_id"],
                        "edge_type": row["edge_type"],
                        "support_count": row["support_count"],
                        "surface_edge_ids": surface_edge_ids,
                        "avg_confidence": avg_confidence,
                    }
                )

        return result

    # ==================== HELPER METHODS ====================

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """
        Compute cosine similarity between two numpy arrays.

        Args:
            a: First embedding vector
            b: Second embedding vector

        Returns:
            Float similarity score (0.0-1.0, higher = more similar)
        """
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

    def _row_to_slot(self, row: aiosqlite.Row) -> CanonicalSlot:
        """Convert database row to CanonicalSlot."""
        return CanonicalSlot(
            id=row["id"],
            session_id=row["session_id"],
            slot_name=row["slot_name"],
            description=row["description"] or "",
            node_type=row["node_type"],
            status=row["status"],
            support_count=row["support_count"],
            first_seen_turn=row["first_seen_turn"],
            promoted_turn=row["promoted_turn"],
            embedding=row["embedding"],  # Keep as bytes (BLOB) for storage
        )
