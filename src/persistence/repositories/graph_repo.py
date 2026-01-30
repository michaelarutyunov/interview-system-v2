"""
Repository for knowledge graph persistence.

Handles CRUD operations on kg_nodes and kg_edges tables.
Uses aiosqlite for async SQLite access.

No business logic - that belongs in GraphService.
"""

import json
from datetime import datetime
from typing import List, Optional, Dict
from uuid import uuid4

import aiosqlite
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
        stance: int = 0,
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
            stance: Stance value (-1, 0, or +1)

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
                properties, source_utterance_ids, recorded_at, superseded_by, stance
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            raise RuntimeError(f"Node creation failed: node {node_id} not found after INSERT")
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

    async def find_node_by_label(self, session_id: str, label: str) -> Optional[KGNode]:
        """
        Find a node by exact label match (case-insensitive).

        DEPRECATED: Use find_node_by_label_and_type for type-aware deduplication.
        This method is kept for backward compatibility but should not be used
        for new node deduplication as it can merge nodes of different types.

        Args:
            session_id: Session ID
            label: Node label to find

        Returns:
            KGNode or None if not found
        """
        self.db.row_factory = aiosqlite.Row
        cursor = await self.db.execute(
            """
            SELECT * FROM kg_nodes
            WHERE session_id = ? AND LOWER(label) = LOWER(?) AND superseded_by IS NULL
            """,
            (session_id, label),
        )
        row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_node(row)

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
            raise RuntimeError(f"Edge creation failed: edge {edge_id} not found after INSERT")
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
        # Build undirected adjacency and find longest connected chain via DFS.
        all_nodes = await self.get_nodes_by_session(session_id)
        all_edges = await self.get_edges_by_session(session_id)

        all_node_ids = {node.id for node in all_nodes}
        adjacency = self._build_undirected_adjacency(all_node_ids, all_edges)
        max_depth = self._find_longest_path(adjacency)

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

    def _build_undirected_adjacency(
        self,
        node_ids: set,
        edges: List[KGEdge],
    ) -> Dict[str, set]:
        """Build undirected adjacency graph from edges.

        Only includes edges that connect nodes in the node_ids set.
        """
        adjacency: Dict[str, set] = {node_id: set() for node_id in node_ids}
        for edge in edges:
            source = edge.source_node_id
            target = edge.target_node_id
            if source in node_ids and target in node_ids:
                adjacency[source].add(target)
                adjacency[target].add(source)
        return adjacency

    def _find_longest_path(self, adjacency: Dict[str, set]) -> int:
        """Find longest simple path in undirected graph using DFS."""
        if not adjacency:
            return 0
        longest = 1
        for start_node in adjacency:
            visited: set = set()
            path_length = self._dfs_longest_path(start_node, adjacency, visited)
            longest = max(longest, path_length)
        return longest

    def _dfs_longest_path(
        self, node: str, adjacency: Dict[str, set], visited: set
    ) -> int:
        """DFS to find longest path starting from node."""
        visited.add(node)
        max_length = 1
        for neighbor in adjacency[node]:
            if neighbor not in visited:
                path_length = self._dfs_longest_path(neighbor, adjacency, visited)
                max_length = max(max_length, 1 + path_length)
        visited.remove(node)
        return max_length

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

