"""
Graph service for knowledge graph business logic.

Responsibilities:
- Convert extraction results to graph nodes/edges
- Deduplicate nodes by label match
- Link nodes to source utterances (provenance)
- Compute graph state for scoring

Uses GraphRepository for persistence.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING, cast

import structlog

if TYPE_CHECKING:
    from src.services.embedding_service import EmbeddingService

from src.domain.models.canonical_graph import CanonicalEdge
from src.domain.models.extraction import (
    ExtractedConcept,
    ExtractedRelationship,
    ExtractionResult,
)
from src.domain.models.knowledge_graph import KGNode, KGEdge, GraphState
from src.persistence.repositories.canonical_slot_repo import CanonicalSlotRepository
from src.persistence.repositories.graph_repo import GraphRepository

log = structlog.get_logger(__name__)


class GraphService:
    """
    Service for knowledge graph operations.

    Provides business logic layer over GraphRepository:
    - Deduplication when adding nodes
    - Extraction result integration
    - Graph state computation
    """

    def __init__(
        self,
        repo: GraphRepository,
        canonical_slot_repo: Optional[CanonicalSlotRepository] = None,
        embedding_service: Optional["EmbeddingService"] = None,
    ):
        """
        Initialize graph service.

        Args:
            repo: GraphRepository instance
            canonical_slot_repo: Optional CanonicalSlotRepository for dual-graph edge aggregation.
                Required when enable_canonical_slots=True, None when disabled.
            embedding_service: Optional EmbeddingService for surface semantic dedup.
                When provided, enables 3-step dedup: exact match → semantic → create new.

        IMPLEMENTATION NOTES:
            - canonical_slot_repo is optional based on enable_canonical_slots feature flag
            - If None and aggregate_surface_edges_to_canonical() is called, raises AttributeError
            - embedding_service enables surface semantic dedup independently of canonical slots
        """
        self.repo = repo
        self.canonical_slot_repo = canonical_slot_repo
        self.embedding_service = embedding_service

    async def add_extraction_to_graph(
        self,
        session_id: str,
        extraction: ExtractionResult,
        utterance_id: str,
    ) -> Tuple[List[KGNode], List[KGEdge]]:
        """
        Add extraction results to the knowledge graph.

        Pipeline:
        1. For each concept: deduplicate or create node
        2. Link nodes to source utterance
        3. For each relationship: create edge between nodes

        Args:
            session_id: Session ID
            extraction: Extraction result from ExtractionService
            utterance_id: Source utterance ID for provenance

        Returns:
            (added_nodes, added_edges) tuple
        """
        if not extraction.is_extractable:
            log.debug("extraction_not_extractable", session_id=session_id)
            return [], []

        log.info(
            "adding_extraction_to_graph",
            session_id=session_id,
            concept_count=len(extraction.concepts),
            relationship_count=len(extraction.relationships),
        )

        # Step 1: Process concepts into nodes
        label_to_node: dict[str, KGNode] = {}
        added_nodes = []

        for concept in extraction.concepts:
            node = await self._add_or_get_node(
                session_id=session_id,
                concept=concept,
                utterance_id=utterance_id,
            )
            if node:
                label_to_node[concept.text.lower()] = node
                added_nodes.append(node)

        # Step 1.5: Expand label_to_node with all session nodes for cross-turn edge resolution
        # Current-turn concepts take precedence (already in dict)
        all_session_nodes = await self.repo.get_nodes_by_session(session_id)
        cross_turn_count = 0
        for node in all_session_nodes:
            key = node.label.lower()
            if key not in label_to_node:
                label_to_node[key] = node
                cross_turn_count += 1

        if cross_turn_count > 0:
            log.debug(
                "cross_turn_nodes_loaded",
                session_id=session_id,
                cross_turn_count=cross_turn_count,
                total_label_map=len(label_to_node),
            )

        # Step 2: Process relationships into edges
        added_edges = []

        for relationship in extraction.relationships:
            edge = await self._add_edge_from_relationship(
                session_id=session_id,
                relationship=relationship,
                label_to_node=label_to_node,
                utterance_id=utterance_id,
            )
            if edge:
                added_edges.append(edge)

        log.info(
            "extraction_added_to_graph",
            session_id=session_id,
            nodes_added=len(added_nodes),
            edges_added=len(added_edges),
        )

        return added_nodes, added_edges

    async def _add_or_get_node(
        self,
        session_id: str,
        concept: ExtractedConcept,
        utterance_id: str,
    ) -> Optional[KGNode]:
        """
        Add a concept as node, or get existing node if duplicate.

        Three-step deduplication:
        1. Exact label + node_type match (case-insensitive, fast path)
        2. Semantic similarity match (same node_type, threshold 0.80)
        3. Create new node (with embedding if computed)

        Args:
            session_id: Session ID
            concept: Extracted concept
            utterance_id: Source utterance ID

        Returns:
            KGNode (existing or newly created)
        """
        from src.core.config import settings

        # Step 1: Exact label match (fast path)
        existing = await self.repo.find_node_by_label_and_type(
            session_id, concept.text, concept.node_type
        )

        if existing:
            log.debug(
                "node_deduplicated",
                label=concept.text,
                node_type=concept.node_type,
                existing_id=existing.id,
                method="exact",
            )
            log.debug(
                "node_dedup_result",
                new_label=concept.text,
                matched_label=existing.label,
                similarity_score=None,
                threshold=None,
                outcome="exact_match",
            )
            return await self.repo.add_source_utterance(existing.id, utterance_id)

        # Step 2: Semantic similarity match (if embedding_service available)
        embedding_bytes = None
        if self.embedding_service is not None:
            embedding = await self.embedding_service.encode(concept.text)
            embedding_bytes = embedding.tobytes()

            similar = await self.repo.find_similar_nodes(
                session_id=session_id,
                node_type=concept.node_type,
                embedding=embedding,
                threshold=settings.surface_similarity_threshold,
            )

            if similar:
                best_node, similarity = similar[0]
                log.info(
                    "node_deduplicated",
                    label=concept.text,
                    node_type=concept.node_type,
                    existing_id=best_node.id,
                    existing_label=best_node.label,
                    similarity=round(similarity, 3),
                    method="semantic",
                )
                log.debug(
                    "node_dedup_result",
                    new_label=concept.text,
                    matched_label=best_node.label,
                    similarity_score=round(similarity, 4),
                    threshold=settings.surface_similarity_threshold,
                    outcome="semantic_merge",
                )
                return await self.repo.add_source_utterance(best_node.id, utterance_id)

        # Step 3: Create new node (with embedding if computed)
        node_properties = dict(concept.properties)
        if concept.linked_elements:
            node_properties["linked_elements"] = concept.linked_elements

        log.debug(
            "node_dedup_result",
            new_label=concept.text,
            matched_label=None,
            similarity_score=None,
            threshold=settings.surface_similarity_threshold
            if self.embedding_service is not None
            else None,
            outcome="new_node",
        )
        return await self.repo.create_node(
            session_id=session_id,
            label=concept.text,
            node_type=concept.node_type,
            confidence=concept.confidence,
            properties=node_properties,
            source_utterance_ids=[utterance_id],
            stance=concept.stance if concept.stance is not None else 0,
            embedding=embedding_bytes,
        )

    async def _add_edge_from_relationship(
        self,
        session_id: str,
        relationship: ExtractedRelationship,
        label_to_node: dict,
        utterance_id: str,
    ) -> Optional[KGEdge]:
        """
        Create edge from extracted relationship.

        Args:
            session_id: Session ID
            relationship: Extracted relationship
            label_to_node: Map of concept text to node
            utterance_id: Source utterance ID

        Returns:
            KGEdge or None if nodes not found
        """
        # Find source and target nodes
        source_node = label_to_node.get(relationship.source_text.lower())
        target_node = label_to_node.get(relationship.target_text.lower())

        # Detect cross-turn resolution: node is cross-turn if current utterance_id
        # is not in its source_utterance_ids (i.e. it was created in a prior turn)
        source_is_cross_turn = (
            source_node is not None and utterance_id not in source_node.source_utterance_ids
        )
        target_is_cross_turn = (
            target_node is not None and utterance_id not in target_node.source_utterance_ids
        )
        is_cross_turn = source_is_cross_turn or target_is_cross_turn

        log.debug(
            "edge_resolution",
            source_label=relationship.source_text,
            target_label=relationship.target_text,
            source_found=source_node is not None,
            target_found=target_node is not None,
            is_cross_turn=is_cross_turn,
            outcome="created" if (source_node and target_node) else "failed",
        )

        if not source_node or not target_node:
            log.warning(
                "edge_skipped_missing_node",
                source=relationship.source_text,
                target=relationship.target_text,
                source_found=source_node is not None,
                target_found=target_node is not None,
            )
            return None

        # Check for existing edge (deduplication)
        existing = await self.repo.find_edge(
            session_id=session_id,
            source_node_id=source_node.id,
            target_node_id=target_node.id,
            edge_type=relationship.relationship_type,
        )

        if existing:
            log.debug(
                "edge_deduplicated",
                source=source_node.label,
                target=target_node.label,
            )
            # Add this utterance to provenance
            return await self.repo.add_edge_source_utterance(existing.id, utterance_id)

        # Create new edge
        return await self.repo.create_edge(
            session_id=session_id,
            source_node_id=source_node.id,
            target_node_id=target_node.id,
            edge_type=relationship.relationship_type,
            confidence=relationship.confidence,
            source_utterance_ids=[utterance_id],
        )

    async def get_session_graph(self, session_id: str) -> Tuple[List[KGNode], List[KGEdge]]:
        """
        Get complete graph for a session.

        Args:
            session_id: Session ID

        Returns:
            (nodes, edges) tuple
        """
        nodes = await self.repo.get_nodes_by_session(session_id)
        edges = await self.repo.get_edges_by_session(session_id)

        return nodes, edges

    async def get_graph_state(self, session_id: str) -> GraphState:
        """
        Get graph state for scoring.

        Args:
            session_id: Session ID

        Returns:
            GraphState with counts and metrics
        """
        return await self.repo.get_graph_state(session_id)

    async def get_node(self, node_id: str) -> Optional[KGNode]:
        """
        Get a single node by ID.

        Args:
            node_id: Node ID

        Returns:
            KGNode or None
        """
        return await self.repo.get_node(node_id)

    async def get_nodes_of_type(self, session_id: str, node_type: str) -> List[KGNode]:
        """
        Get all nodes of a specific type.

        Args:
            session_id: Session ID
            node_type: Node type to filter

        Returns:
            List of nodes matching type
        """
        all_nodes = await self.repo.get_nodes_by_session(session_id)
        return [n for n in all_nodes if n.node_type == node_type]

    async def get_recent_nodes(self, session_id: str, limit: int = 5) -> List[KGNode]:
        """
        Get most recently added nodes.

        Args:
            session_id: Session ID
            limit: Maximum nodes to return

        Returns:
            List of nodes sorted by recorded_at descending
        """
        nodes = await self.repo.get_nodes_by_session(session_id)
        sorted_nodes = sorted(nodes, key=lambda n: n.recorded_at, reverse=True)
        return sorted_nodes[:limit]

    async def handle_contradiction(
        self,
        session_id: str,
        old_node_id: str,
        new_concept: ExtractedConcept,
        utterance_id: str,
    ) -> Tuple[KGNode, KGEdge]:
        """
        Handle a contradiction between old and new beliefs.

        Creates new node and REVISES edge, marks old node as superseded.

        Args:
            session_id: Session ID
            old_node_id: ID of node being contradicted
            new_concept: New contradicting concept
            utterance_id: Source utterance ID

        Returns:
            (new_node, revises_edge) tuple
        """
        # Create new node for the new belief
        new_node = await self.repo.create_node(
            session_id=session_id,
            label=new_concept.text,
            node_type=new_concept.node_type,
            confidence=new_concept.confidence,
            source_utterance_ids=[utterance_id],
            stance=new_concept.stance if new_concept.stance is not None else 0,
        )

        # Mark old node as superseded
        await self.repo.supersede_node(old_node_id, new_node.id)

        # Create REVISES edge
        edge = await self.repo.create_edge(
            session_id=session_id,
            source_node_id=new_node.id,
            target_node_id=old_node_id,
            edge_type="revises",
            confidence=new_concept.confidence,
            source_utterance_ids=[utterance_id],
        )

        log.info(
            "contradiction_handled",
            old_node_id=old_node_id,
            new_node_id=new_node.id,
        )

        return new_node, edge

    async def aggregate_surface_edges_to_canonical(
        self,
        session_id: str,
        surface_edges: List[Dict[str, Any]],
        turn_number: int,
    ) -> List[CanonicalEdge]:
        """
        Aggregate surface edges to canonical edges for dual-graph architecture.

        Maps each surface edge to its canonical equivalent by looking up the
        canonical slot mappings for source and target nodes. Skips edges where
        either endpoint is unmapped or forms a self-loop in the canonical graph.

        Args:
            session_id: Session ID
            surface_edges: List of surface edges from GraphUpdateOutput.edges_added
                         Each edge dict has keys: id, source_node_id, target_node_id, edge_type
            turn_number: Current turn number (for logging)

        Returns:
            List of created/updated CanonicalEdge objects

        Raises:
            AttributeError: If canonical_slot_repo is None (not initialized for dual-graph mode)

        IMPLEMENTATION NOTES:
            - surface_edges are List[Dict[str, Any]] from GraphUpdateOutput
            - Skips unmapped nodes (logs debug: surface_edge_not_mapped)
            - Skips self-loops where source_slot == target_slot (logs: canonical_self_loop_prevented)
            - Uses edge_type unchanged from surface edge (different types create separate canonical edges)
        """
        if self.canonical_slot_repo is None:
            raise AttributeError(
                "canonical_slot_repo is required for edge aggregation but was None. "
                "Dual-graph mode requires enable_canonical_slots=True setting."
            )

        log.info(
            "canonical_edge_aggregation_started",
            session_id=session_id,
            turn=turn_number,
            surface_edge_count=len(surface_edges),
        )

        canonical_edges: List[CanonicalEdge] = []
        skipped_unmapped = 0
        skipped_self_loops = 0

        for edge in surface_edges:
            source_id = edge.get("source_node_id")
            target_id = edge.get("target_node_id")
            edge_type = edge.get("edge_type")
            surface_edge_id = edge.get("id")

            if not all([source_id, target_id, edge_type, surface_edge_id]):
                log.warning(
                    "surface_edge_skipped_missing_fields",
                    edge_id=edge.get("id"),
                    source_id=source_id,
                    target_id=target_id,
                    edge_type=edge_type,
                )
                continue

            # Type narrowing: after the truthy check, these are guaranteed to be strings
            source_id = cast(str, source_id)
            target_id = cast(str, target_id)
            edge_type = cast(str, edge_type)
            surface_edge_id = cast(str, surface_edge_id)

            # Get canonical slot mappings for source and target
            source_mapping = await self.canonical_slot_repo.get_mapping_for_node(source_id)
            target_mapping = await self.canonical_slot_repo.get_mapping_for_node(target_id)

            # Skip if either endpoint is unmapped
            if source_mapping is None or target_mapping is None:
                skipped_unmapped += 1
                log.debug(
                    "surface_edge_not_mapped",
                    surface_edge_id=surface_edge_id,
                    source_mapped=source_mapping is not None,
                    target_mapped=target_mapping is not None,
                )
                continue

            source_slot_id = source_mapping.canonical_slot_id
            target_slot_id = target_mapping.canonical_slot_id

            # Skip self-loops in canonical graph (source_slot == target_slot)
            if source_slot_id == target_slot_id:
                skipped_self_loops += 1
                log.debug(
                    "canonical_self_loop_prevented",
                    surface_edge_id=surface_edge_id,
                    slot_id=source_slot_id,
                )
                continue

            # Add or update canonical edge
            canonical_edge = await self.canonical_slot_repo.add_or_update_canonical_edge(
                session_id=session_id,
                source_slot_id=source_slot_id,
                target_slot_id=target_slot_id,
                edge_type=edge_type,
                surface_edge_id=surface_edge_id,
            )
            canonical_edges.append(canonical_edge)

        log.info(
            "canonical_edges_aggregated",
            session_id=session_id,
            turn=turn_number,
            canonical_edge_count=len(canonical_edges),
            skipped_unmapped=skipped_unmapped,
            skipped_self_loops=skipped_self_loops,
        )

        return canonical_edges
