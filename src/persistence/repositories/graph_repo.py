"""
Repository for knowledge graph persistence.

Handles CRUD operations on kg_nodes and kg_edges tables.
Uses aiosqlite for async SQLite access.

No business logic - that belongs in GraphService.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import aiosqlite
import numpy as np
import structlog

from src.domain.models.knowledge_graph import (
    KGNode,
    KGEdge,
    GraphState,
    DepthMetrics,
)

log = structlog.get_logger(__name__)


class GraphRepository:
    """
    Repository for knowledge graph nodes and edges.

    Provides CRUD operations on SQLite tables:
    - kg_nodes: Knowledge graph nodes
    - kg_edges: Knowledge graph edges
    """

    def __init__(self, db: aiosqlite.Connection):
        """
        Initialize graph repository.

        Args:
            db: aiosqlite connection (from FastAPI dependency)
        """
        self.db = db

    # ==================== NODE OPERATIONS ====================

    async def create_node(
        self,
        session_id: str,
        label: str,
        node_type: str,
        confidence: float = 0.8,
        properties: Optional[dict] = None,
        source_utterance_ids: Optional[List[str]] = None,
        stance: int = 0,  # Deprecated: no longer extracted. Kept for backward compat.
        embedding: Optional[bytes] = None,
    ) -> KGNode:
        """
        Create a new knowledge graph node.

        Args:
            session_id: Session ID
            label: Node label (respondent's language)
            node_type: Node type (attribute, consequence, value)
            confidence: Extraction confidence (0.0-1.0)
            properties: Additional properties
            source_utterance_ids: IDs of source utterances
            stance: Deprecated — no longer extracted. Kept for backward compat.
            embedding: Optional embedding bytes for surface semantic dedup

        Returns:
            Created KGNode
        """
        node_id = str(uuid4())
        now = datetime.now().isoformat()
        properties = properties or {}
        source_ids = source_utterance_ids or []

        await self.db.execute(
            """
            INSERT INTO kg_nodes (
                id, session_id, label, node_type, confidence,
                properties, source_utterance_ids, recorded_at, superseded_by, stance, embedding
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                node_id,
                session_id,
                label,
                node_type,
                confidence,
                json.dumps(properties),
                json.dumps(source_ids),
                now,
                None,
                stance,
                embedding,
            ),
        )
        await self.db.commit()

        log.info(
            "node_created",
            node_id=node_id,
            label=label,
            node_type=node_type,
            stance=stance,
        )

        node = await self.get_node(node_id)
        if node is None:
            raise RuntimeError(
                f"Node creation failed: node {node_id} not found after INSERT"
            )
        return node

    async def get_node(self, node_id: str) -> Optional[KGNode]:
        """
        Get a node by ID.

        Args:
            node_id: Node ID

        Returns:
            KGNode or None if not found
        """
        self.db.row_factory = aiosqlite.Row
        cursor = await self.db.execute(
            "SELECT * FROM kg_nodes WHERE id = ?",
            (node_id,),
        )
        row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_node(row)

    async def get_nodes_by_session(self, session_id: str) -> List[KGNode]:
        """
        Get all nodes for a session.

        Args:
            session_id: Session ID

        Returns:
            List of KGNode objects
        """
        self.db.row_factory = aiosqlite.Row
        cursor = await self.db.execute(
            "SELECT * FROM kg_nodes WHERE session_id = ? AND superseded_by IS NULL",
            (session_id,),
        )
        rows = await cursor.fetchall()

        return [self._row_to_node(row) for row in rows]

    async def find_node_by_label_and_type(
        self, session_id: str, label: str, node_type: str
    ) -> Optional[KGNode]:
        """
        Find a node by exact label and node_type match (case-insensitive label).

        This is the recommended method for node deduplication as it ensures
        nodes of different types (e.g., attribute vs terminal_value) are not
        merged incorrectly.

        Args:
            session_id: Session ID
            label: Node label to find
            node_type: Node type to match

        Returns:
            KGNode or None if not found
        """
        self.db.row_factory = aiosqlite.Row
        cursor = await self.db.execute(
            """
            SELECT * FROM kg_nodes
            WHERE session_id = ? AND LOWER(label) = LOWER(?)
              AND node_type = ? AND superseded_by IS NULL
            """,
            (session_id, label, node_type),
        )
        row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_node(row)

    async def update_node(
        self,
        node_id: str,
        **updates,
    ) -> Optional[KGNode]:
        """
        Update a node's fields.

        Args:
            node_id: Node ID
            **updates: Fields to update (confidence, properties, etc.)

        Returns:
            Updated KGNode or None if not found
        """
        # Build update query
        set_clauses = []
        values = []

        for field, value in updates.items():
            if field in ("confidence", "superseded_by"):
                set_clauses.append(f"{field} = ?")
                values.append(value)
            elif field == "properties":
                set_clauses.append("properties = ?")
                values.append(json.dumps(value))
            elif field == "source_utterance_ids":
                set_clauses.append("source_utterance_ids = ?")
                values.append(json.dumps(value))

        if not set_clauses:
            return await self.get_node(node_id)

        values.append(node_id)
        query = f"UPDATE kg_nodes SET {', '.join(set_clauses)} WHERE id = ?"

        await self.db.execute(query, values)
        await self.db.commit()

        log.info("node_updated", node_id=node_id, updates=list(updates.keys()))

        return await self.get_node(node_id)

    async def add_source_utterance(
        self, node_id: str, utterance_id: str
    ) -> Optional[KGNode]:
        """
        Add a source utterance to a node's provenance.

        Args:
            node_id: Node ID
            utterance_id: Utterance ID to add

        Returns:
            Updated KGNode or None if not found
        """
        node = await self.get_node(node_id)
        if not node:
            return None

        source_ids = list(node.source_utterance_ids)
        if utterance_id not in source_ids:
            source_ids.append(utterance_id)
            return await self.update_node(node_id, source_utterance_ids=source_ids)

        return node

    async def supersede_node(
        self, old_node_id: str, new_node_id: str
    ) -> Optional[KGNode]:
        """
        Mark a node as superseded by another (for contradictions).

        Args:
            old_node_id: Node being superseded
            new_node_id: Node that supersedes it

        Returns:
            Updated old node or None
        """
        return await self.update_node(old_node_id, superseded_by=new_node_id)

    # ==================== EDGE OPERATIONS ====================

    async def create_edge(
        self,
        session_id: str,
        source_node_id: str,
        target_node_id: str,
        edge_type: str,
        confidence: float = 0.8,
        properties: Optional[dict] = None,
        source_utterance_ids: Optional[List[str]] = None,
    ) -> KGEdge:
        """
        Create a new knowledge graph edge.

        Args:
            session_id: Session ID
            source_node_id: Source node ID
            target_node_id: Target node ID
            edge_type: Edge type (leads_to, revises)
            confidence: Extraction confidence
            properties: Additional properties
            source_utterance_ids: IDs of source utterances

        Returns:
            Created KGEdge
        """
        edge_id = str(uuid4())
        now = datetime.now().isoformat()
        properties = properties or {}
        source_ids = source_utterance_ids or []

        await self.db.execute(
            """
            INSERT INTO kg_edges (
                id, session_id, source_node_id, target_node_id, edge_type,
                confidence, properties, source_utterance_ids, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                edge_id,
                session_id,
                source_node_id,
                target_node_id,
                edge_type,
                confidence,
                json.dumps(properties),
                json.dumps(source_ids),
                now,
            ),
        )
        await self.db.commit()

        log.info(
            "edge_created",
            edge_id=edge_id,
            source=source_node_id,
            target=target_node_id,
            type=edge_type,
        )

        edge = await self.get_edge(edge_id)
        if edge is None:
            raise RuntimeError(
                f"Edge creation failed: edge {edge_id} not found after INSERT"
            )
        return edge

    async def get_edge(self, edge_id: str) -> Optional[KGEdge]:
        """
        Get an edge by ID.

        Args:
            edge_id: Edge ID

        Returns:
            KGEdge or None if not found
        """
        self.db.row_factory = aiosqlite.Row
        cursor = await self.db.execute(
            "SELECT * FROM kg_edges WHERE id = ?",
            (edge_id,),
        )
        row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_edge(row)

    async def get_edges_by_session(self, session_id: str) -> List[KGEdge]:
        """
        Get all edges for a session.

        Args:
            session_id: Session ID

        Returns:
            List of KGEdge objects
        """
        self.db.row_factory = aiosqlite.Row
        cursor = await self.db.execute(
            "SELECT * FROM kg_edges WHERE session_id = ?",
            (session_id,),
        )
        rows = await cursor.fetchall()

        return [self._row_to_edge(row) for row in rows]

    async def find_edge(
        self,
        session_id: str,
        source_node_id: str,
        target_node_id: str,
        edge_type: str,
    ) -> Optional[KGEdge]:
        """
        Find an edge by source, target, and type.

        Args:
            session_id: Session ID
            source_node_id: Source node ID
            target_node_id: Target node ID
            edge_type: Edge type

        Returns:
            KGEdge or None if not found
        """
        self.db.row_factory = aiosqlite.Row
        cursor = await self.db.execute(
            """
            SELECT * FROM kg_edges
            WHERE session_id = ? AND source_node_id = ?
              AND target_node_id = ? AND edge_type = ?
            """,
            (session_id, source_node_id, target_node_id, edge_type),
        )
        row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_edge(row)

    async def add_edge_source_utterance(
        self, edge_id: str, utterance_id: str
    ) -> Optional[KGEdge]:
        """
        Add a source utterance to an edge's provenance.

        Args:
            edge_id: Edge ID
            utterance_id: Utterance ID to add

        Returns:
            Updated KGEdge or None
        """
        edge = await self.get_edge(edge_id)
        if not edge:
            return None

        source_ids = list(edge.source_utterance_ids)
        if utterance_id not in source_ids:
            source_ids.append(utterance_id)

            await self.db.execute(
                "UPDATE kg_edges SET source_utterance_ids = ? WHERE id = ?",
                (json.dumps(source_ids), edge_id),
            )
            await self.db.commit()

        return await self.get_edge(edge_id)

    # ==================== GRAPH STATE ====================

    async def get_graph_state(self, session_id: str) -> GraphState:
        """
        Get aggregate graph statistics for a session.

        Args:
            session_id: Session ID

        Returns:
            GraphState with counts and metrics
        """
        # Node count
        cursor = await self.db.execute(
            "SELECT COUNT(*) FROM kg_nodes WHERE session_id = ? AND superseded_by IS NULL",
            (session_id,),
        )
        row = await cursor.fetchone()
        node_count = row[0] if row else 0

        # Edge count
        cursor = await self.db.execute(
            "SELECT COUNT(*) FROM kg_edges WHERE session_id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        edge_count = row[0] if row else 0

        # Nodes by type
        cursor = await self.db.execute(
            """
            SELECT node_type, COUNT(*) FROM kg_nodes
            WHERE session_id = ? AND superseded_by IS NULL
            GROUP BY node_type
            """,
            (session_id,),
        )
        nodes_by_type = {row[0]: row[1] for row in await cursor.fetchall()}

        # Edges by type
        cursor = await self.db.execute(
            """
            SELECT edge_type, COUNT(*) FROM kg_edges
            WHERE session_id = ?
            GROUP BY edge_type
            """,
            (session_id,),
        )
        edges_by_type = {row[0]: row[1] for row in await cursor.fetchall()}

        # Orphan nodes (no edges)
        cursor = await self.db.execute(
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

        # Max depth via graph traversal (chain validation)
        # Build directed adjacency and find longest chain via BFS from roots.
        all_nodes = await self.get_nodes_by_session(session_id)
        all_edges = await self.get_edges_by_session(session_id)

        all_node_ids = {node.id for node in all_nodes}
        adjacency, has_incoming = self._build_directed_adjacency(all_node_ids, all_edges)
        max_depth = self._find_longest_path_bfs(adjacency, all_node_ids, has_incoming)

        # Create DepthMetrics (ADR-010)
        depth_metrics = DepthMetrics(
            max_depth=max_depth,
            avg_depth=0.0,
            depth_by_element={},
            longest_chain_path=[],
        )

        return GraphState(
            node_count=node_count,
            edge_count=edge_count,
            nodes_by_type=nodes_by_type,
            edges_by_type=edges_by_type,
            orphan_count=orphan_count,
            depth_metrics=depth_metrics,
        )

    # ==================== GRAPH TRAVERSAL HELPERS ====================

    def _build_directed_adjacency(
        self,
        node_ids: set,
        edges: List[KGEdge],
    ) -> tuple[Dict[str, List[str]], set]:
        """Build directed adjacency list and incoming-edge tracker from edges.

        Preserves edge directionality (source → target) for meaningful depth
        computation. Only includes edges connecting nodes within node_ids.

        Returns:
            (adjacency, has_incoming) where:
            - adjacency: dict mapping node_id → list of neighbor node_ids
            - has_incoming: set of node_ids that have at least one incoming edge
        """
        adjacency: Dict[str, List[str]] = {node_id: [] for node_id in node_ids}
        has_incoming: set = set()
        for edge in edges:
            source = edge.source_node_id
            target = edge.target_node_id
            if source in node_ids and target in node_ids:
                adjacency[source].append(target)
                has_incoming.add(target)
        return adjacency, has_incoming

    def _find_longest_path_bfs(
        self,
        adjacency: Dict[str, List[str]],
        node_ids: set,
        has_incoming: set,
    ) -> int:
        """Find longest reasoning chain using BFS from root nodes.

        Roots are nodes with no incoming edges (chain entry points). BFS
        tracks visited nodes per traversal to handle cycles without
        backtracking. Complexity: O(V × (V+E)) — polynomial.

        Args:
            adjacency: Directed adjacency list
            node_ids: Full set of node IDs (for root detection)
            has_incoming: Nodes that have at least one incoming edge

        Returns:
            Length of longest chain, or 0 if no edges exist
        """
        from collections import deque

        if not any(adjacency.values()):
            return 0

        roots = node_ids - has_incoming
        if not roots:
            # All nodes in cycles — use every node as a potential start
            roots = node_ids

        max_depth = 0

        for root in roots:
            visited: set = set()
            queue: deque = deque([(root, 0)])

            while queue:
                node, depth = queue.popleft()
                if node in visited:
                    continue
                visited.add(node)
                max_depth = max(max_depth, depth)

                for neighbor in adjacency.get(node, []):
                    if neighbor not in visited:
                        queue.append((neighbor, depth + 1))

        return max_depth

    # ==================== DUAL-GRAPH REPORTING METHODS ====================

    async def get_nodes_with_canonical_mapping(
        self, session_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get surface nodes with optional canonical slot mapping.

        LEFT JOIN kg_nodes with surface_to_slot_mapping and canonical_slots
        to include canonical_slot field in results.

        Args:
            session_id: Session ID

        Returns:
            List of node dicts with optional canonical_slot field:
            {id, label, node_type, confidence, canonical_slot: {slot_id, slot_name, similarity_score}}

        Note:
            canonical_slot is None if no mapping exists.
            Uses LEFT JOIN to include all nodes even if unmapped.
        """
        self.db.row_factory = aiosqlite.Row
        cursor = await self.db.execute(
            """
            SELECT
                n.id,
                n.label,
                n.node_type,
                n.confidence,
                m.canonical_slot_id,
                s.slot_name,
                m.similarity_score
            FROM kg_nodes n
            LEFT JOIN surface_to_slot_mapping m ON n.id = m.surface_node_id
            LEFT JOIN canonical_slots s ON m.canonical_slot_id = s.id
            WHERE n.session_id = ?
            ORDER BY n.recorded_at DESC
            """,
            (session_id,),
        )
        rows = await cursor.fetchall()

        result = []
        for row in rows:
            node_dict = {
                "id": row["id"],
                "label": row["label"],
                "node_type": row["node_type"],
                "confidence": row["confidence"],
            }
            if row["canonical_slot_id"]:
                node_dict["canonical_slot"] = {
                    "slot_id": row["canonical_slot_id"],
                    "slot_name": row["slot_name"],
                    "similarity_score": row["similarity_score"],
                }
            result.append(node_dict)

        return result

    # ==================== SURFACE SEMANTIC DEDUP ====================

    async def find_similar_nodes(
        self,
        session_id: str,
        node_type: str,
        embedding: np.ndarray,
        threshold: float = 0.80,
    ) -> List[Tuple[KGNode, float]]:
        """
        Find nodes similar to the given embedding via cosine similarity.

        O(N) brute-force search: loads all nodes of matching session+type
        with non-null embeddings and computes cosine similarity in Python.
        N~100 max per session, so this is acceptable.

        Args:
            session_id: Session ID
            node_type: Node type filter (only compare nodes of same type)
            embedding: Query embedding (numpy float32 array)
            threshold: Similarity threshold (default: 0.80)

        Returns:
            List of (KGNode, similarity_score) tuples above threshold,
            sorted descending by similarity
        """
        self.db.row_factory = aiosqlite.Row
        cursor = await self.db.execute(
            """
            SELECT * FROM kg_nodes
            WHERE session_id = ? AND node_type = ? AND superseded_by IS NULL
              AND embedding IS NOT NULL
            """,
            (session_id, node_type),
        )
        rows = await cursor.fetchall()

        similar_nodes = []
        for row in rows:
            node_embedding = np.frombuffer(row["embedding"], dtype=np.float32)
            similarity = self._cosine_similarity(embedding, node_embedding)

            if similarity >= threshold:
                similar_nodes.append((self._row_to_node(row), similarity))

        similar_nodes.sort(key=lambda x: x[1], reverse=True)
        return similar_nodes

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two numpy arrays."""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

    # ==================== HELPERS ====================

    def _row_to_node(self, row: aiosqlite.Row) -> KGNode:
        """Convert database row to KGNode."""
        return KGNode(
            id=row["id"],
            session_id=row["session_id"],
            label=row["label"],
            node_type=row["node_type"],
            confidence=row["confidence"],
            properties=json.loads(row["properties"]) if row["properties"] else {},
            source_utterance_ids=json.loads(row["source_utterance_ids"])
            if row["source_utterance_ids"]
            else [],
            recorded_at=datetime.fromisoformat(row["recorded_at"]),
            superseded_by=row["superseded_by"],
            stance=row["stance"]
            if "stance" in row.keys()
            else 0,  # Default to 0 for existing nodes
        )

    def _row_to_edge(self, row: aiosqlite.Row) -> KGEdge:
        """Convert database row to KGEdge."""
        return KGEdge(
            id=row["id"],
            session_id=row["session_id"],
            source_node_id=row["source_node_id"],
            target_node_id=row["target_node_id"],
            edge_type=row["edge_type"],
            confidence=row["confidence"],
            properties=json.loads(row["properties"]) if row["properties"] else {},
            source_utterance_ids=json.loads(row["source_utterance_ids"])
            if row["source_utterance_ids"]
            else [],
            recorded_at=datetime.fromisoformat(row["recorded_at"]),
        )
