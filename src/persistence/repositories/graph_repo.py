"""
Repository for knowledge graph persistence.

Handles CRUD operations on kg_nodes and kg_edges tables.
Uses aiosqlite for async SQLite access.

No business logic - that belongs in GraphService.
"""

import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Any, Dict
from uuid import uuid4

import aiosqlite
import structlog

from src.domain.models.knowledge_graph import (
    KGNode,
    KGEdge,
    GraphState,
    CoverageState,
    ElementCoverage,
    DepthMetrics,
)
from src.domain.models.concept import Concept
from src.services.depth_calculator import DepthCalculator

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
        assert node is not None, "Node should exist just after creation"
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
        assert edge is not None, "Edge should exist just after creation"
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
        # Fetch all nodes and edges, then use DepthCalculator's DFS
        # to find the longest connected chain across the entire graph.
        all_nodes = await self.get_nodes_by_session(session_id)
        all_edges = await self.get_edges_by_session(session_id)

        depth_calc = DepthCalculator()
        all_node_ids = {node.id for node in all_nodes}
        adjacency = depth_calc._build_undirected_adjacency(all_node_ids, all_edges)
        max_depth = depth_calc._find_longest_path(adjacency)

        # Build enhanced coverage state with depth tracking
        coverage_state = await self._build_coverage_state(session_id)

        # Create DepthMetrics (ADR-010)
        depth_metrics = DepthMetrics(
            max_depth=max_depth,
            avg_depth=0.0,
            depth_by_element={},
            longest_chain_path=[],
        )

        # Handle case where coverage_state is None (no concept loaded)
        # Per ADR-010, coverage_state should always be present for coverage-driven mode
        # but during migration we handle None gracefully
        if coverage_state is None:
            coverage_state = CoverageState()

        return GraphState(
            node_count=node_count,
            edge_count=edge_count,
            nodes_by_type=nodes_by_type,
            edges_by_type=edges_by_type,
            orphan_count=orphan_count,
            depth_metrics=depth_metrics,
            coverage_state=coverage_state,
        )

    async def _build_coverage_state(self, session_id: str) -> Optional[CoverageState]:
        """
        Build enhanced coverage state with depth tracking via chain validation.

        Phase 4 implementation: Uses DepthCalculator to compute element depth
        based on connected chains of linked nodes.

        Args:
            session_id: Session ID

        Returns:
            CoverageState with element-level depth tracking, or None if concept not found
        """
        # P0 Fix: Add diagnostic logging to trace coverage state building
        log.info(
            "coverage_state_building_started",
            session_id=session_id,
        )

        # Get all nodes for the session
        nodes = await self.get_nodes_by_session(session_id)
        edges = await self.get_edges_by_session(session_id)

        # Load concept elements
        elements_data = await self._load_concept_elements(session_id)
        element_ids = elements_data.get("element_ids", [])
        elements_by_id = elements_data.get("elements_by_id", {})

        # P0 Fix: Log element loading results for diagnostics
        log.info(
            "coverage_state_elements_loaded",
            session_id=session_id,
            element_count=len(element_ids),
            has_elements_by_id=bool(elements_by_id),
        )

        if not element_ids:
            log.warning(
                "coverage_state_failed_no_elements",
                session_id=session_id,
                message="No elements found - coverage_state will be NULL",
            )
            return None

        # Match nodes to elements using fuzzy matching
        element_node_mapping = self._map_nodes_to_elements(nodes, elements_by_id)

        # Initialize depth calculator with MEC ladder
        depth_calculator = DepthCalculator()

        # Calculate depth for all elements
        element_depths = depth_calculator.calculate_all_elements(
            element_node_mapping, edges
        )

        # Build element coverage dict
        elements_dict = {}
        for elem_id in element_ids:
            if elem_id in element_depths:
                elements_dict[elem_id] = ElementCoverage(**element_depths[elem_id])
            else:
                # Element not covered at all
                elements_dict[elem_id] = ElementCoverage(
                    covered=False, linked_node_ids=[], types_found=[], depth_score=0.0
                )

        # Calculate summary metrics
        elements_covered = sum(1 for e in elements_dict.values() if e.covered)
        overall_depth = depth_calculator.get_overall_depth(element_depths)
        max_depth = depth_calculator.get_max_depth(element_depths)  # P0 Fix

        coverage_state = CoverageState(
            elements=elements_dict,
            elements_covered=elements_covered,
            elements_total=len(element_ids),
            overall_depth=overall_depth,
            max_depth=max_depth,  # P0 Fix: Track maximum depth (monotonic metric)
        )

        # P0 Fix: Upgrade to info level for diagnostic visibility
        log.info(
            "coverage_state_built_successfully",
            session_id=session_id,
            elements_covered=elements_covered,
            elements_total=len(element_ids),
            overall_depth=overall_depth,
            max_depth=max_depth,  # P0 Fix: Include max_depth in diagnostics
            coverage_percent=round((elements_covered / len(element_ids)) * 100, 1)
            if element_ids
            else 0,
        )

        return coverage_state

    def _map_nodes_to_elements(
        self, nodes: List[KGNode], elements_by_id: Dict[Any, Dict[str, Any]]
    ) -> Dict[int, List[KGNode]]:
        """
        Map nodes to elements using explicit linked_elements first, then fuzzy matching.

        Priority order:
        1. Use node.properties["linked_elements"] if set (from LLM extraction)
        2. Fall back to fuzzy substring matching on labels and aliases

        A single node can be linked to multiple elements.

        Args:
            nodes: List of KGNode objects
            elements_by_id: Dict mapping element_id -> {label, aliases}

        Returns:
            Dict mapping element_id (int) -> list of linked nodes
        """
        # Normalize all element IDs to integers for the mapping
        int_element_ids = []
        for elem_id in elements_by_id.keys():
            if isinstance(elem_id, int):
                int_element_ids.append(elem_id)
            elif isinstance(elem_id, str) and elem_id.isdigit():
                int_element_ids.append(int(elem_id))
            else:
                # Non-numeric string IDs - skip for v2 format
                continue

        mapping = {elem_id: [] for elem_id in int_element_ids}

        for node in nodes:
            # PRIORITY 1: Use explicit linked_elements from extraction if available
            linked_elements = node.properties.get("linked_elements", [])
            if linked_elements:
                for elem_id in linked_elements:
                    # Normalize to int
                    if isinstance(elem_id, int):
                        key = elem_id
                    elif isinstance(elem_id, str) and elem_id.isdigit():
                        key = int(elem_id)
                    else:
                        continue

                    if key in mapping:
                        mapping[key].append(node)
                        log.debug(
                            "linked_node_to_element_explicit",
                            node_label=node.label,
                            element_id=key,
                            source="linked_elements",
                        )
                # If node has explicit links, skip fuzzy matching for this node
                continue

            # PRIORITY 2: Fall back to fuzzy substring matching
            node_label_lower = node.label.lower()

            for elem_id, elem_data in elements_by_id.items():
                # Normalize to integer key
                if isinstance(elem_id, int):
                    key = elem_id
                elif isinstance(elem_id, str) and elem_id.isdigit():
                    key = int(elem_id)
                else:
                    # Skip non-integer element IDs (v1 format)
                    continue

                # Get search terms: label + aliases
                elem_label = elem_data.get("label", "").lower()
                aliases = [a.lower() for a in elem_data.get("aliases", [])]

                # Label is treated as an implicit alias (substring match)
                search_terms = [elem_label] + aliases

                # Check if any search term appears in the node label
                if any(term in node_label_lower for term in search_terms if term):
                    mapping[key].append(node)

                    log.debug(
                        "matched_node_to_element_fuzzy",
                        node_label=node.label,
                        element_id=key,
                        matched_term=next(
                            (t for t in search_terms if t and t in node_label_lower),
                            None,
                        ),
                    )

        return mapping

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

    async def _load_concept_elements(self, session_id: str) -> dict:
        """
        Load element data (IDs, labels, aliases) from concept config for a session.

        Validates the concept YAML against the Pydantic Concept model for type safety.
        Element IDs are integers in the enhanced concept format.

        Args:
            session_id: Session ID

        Returns:
            Dictionary with:
            - element_ids: List of element IDs (integers in v2 format)
            - elements_by_id: Dict mapping element_id -> {label, aliases}
            Returns empty dict if not found
        """
        # Get concept_id from sessions table
        cursor = await self.db.execute(
            "SELECT concept_id FROM sessions WHERE id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        if not row:
            log.warning("session_not_found_for_concept_elements", session_id=session_id)
            return {"element_ids": [], "elements_by_id": {}}

        concept_id = row[0]
        if not concept_id:
            log.warning("no_concept_id_for_session", session_id=session_id)
            return {"element_ids": [], "elements_by_id": {}}

        # Load concept config from config/concepts/{concept_id}.yaml
        # Path from graph_repo.py: src/persistence/repositories/graph_repo.py
        # We need to go up 4 levels to reach project root, then into config/concepts
        config_dir = Path(__file__).parent.parent.parent.parent / "config" / "concepts"
        concept_path = config_dir / f"{concept_id}.yaml"

        # P0 Fix: Log file path and existence for diagnostic tracing
        log.info(
            "concept_elements_loading",
            concept_id=concept_id,
            file_path=str(concept_path),
            file_exists=concept_path.exists(),
            config_dir_exists=config_dir.exists(),
        )

        if not concept_path.exists():
            log.warning(
                "concept_config_not_found",
                concept_id=concept_id,
                path=str(concept_path),
            )
            return {"element_ids": [], "elements_by_id": {}}

        try:
            with open(concept_path) as f:
                concept_data = yaml.safe_load(f)

            # Validate against Pydantic model for type safety
            try:
                concept = Concept(**concept_data)
            except Exception as validation_error:
                log.error(
                    "concept_config_validation_error",
                    concept_id=concept_id,
                    error=str(validation_error),
                )
                # Fall back to raw parsing for backward compatibility
                elements = concept_data.get("elements", [])
            else:
                # Use validated concept data
                elements = [el.model_dump() for el in concept.elements]

            # Extract element data from the elements list
            element_ids = []
            elements_by_id = {}

            for e in elements:
                elem_id = e.get("id")
                if elem_id is not None:
                    element_ids.append(elem_id)
                    elements_by_id[elem_id] = {
                        "label": e.get("label", ""),
                        "aliases": e.get("aliases", []),
                    }

            log.debug(
                "concept_elements_loaded",
                concept_id=concept_id,
                element_count=len(element_ids),
            )
            return {
                "element_ids": element_ids,
                "elements_by_id": elements_by_id,
            }

        except Exception as e:
            log.error(
                "concept_config_load_error",
                concept_id=concept_id,
                error=str(e),
            )
            return {"element_ids": [], "elements_by_id": {}}

    def _match_labels_to_elements(
        self, node_labels: List[str], elements_data: dict
    ) -> List[Any]:
        """
        Match node labels to element IDs using fuzzy substring matching.

        This is a fallback when LLM-based element linking is not available.
        Matches node labels against element labels and aliases using substring matching.

        Args:
            node_labels: List of node labels (free-form text)
            elements_data: Dict from _load_concept_elements with element_ids and elements_by_id

        Returns:
            List of element IDs (strings or ints) that have at least one matching node label
        """
        elements_matched = set()
        elements_by_id = elements_data.get("elements_by_id", {})

        for label in node_labels:
            label_lower = label.lower()
            for elem_id, elem_data in elements_by_id.items():
                # Check label match (substring)
                elem_label = elem_data.get("label", "").lower()
                aliases = [a.lower() for a in elem_data.get("aliases", [])]

                # Label is treated as an implicit alias (substring match)
                search_terms = [elem_label] + aliases

                # Check if any search term appears in the node label
                if any(term in label_lower for term in search_terms if term):
                    # Keep the original element_id type (string or int) for proper comparison
                    elements_matched.add(elem_id)
                    log.debug(
                        "matched_label_to_element",
                        node_label=label,
                        element_id=elem_id,
                        matched_term=next(
                            (t for t in search_terms if t and t in label_lower), None
                        ),
                    )

        # Convert to list while preserving types
        matched_ids = list(elements_matched)

        log.debug(
            "element_matching_complete",
            node_labels_count=len(node_labels),
            elements_matched=len(matched_ids),
        )
        return matched_ids
