"""
Graph service for knowledge graph business logic.

Responsibilities:
- Convert extraction results to graph nodes/edges
- Deduplicate nodes by label match
- Link nodes to source utterances (provenance)
- Compute graph state for scoring

Uses GraphRepository for persistence.
"""

from typing import List, Optional, Tuple

import structlog

from src.domain.models.extraction import (
    ExtractedConcept,
    ExtractedRelationship,
    ExtractionResult,
)
from src.domain.models.knowledge_graph import KGNode, KGEdge, GraphState
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

    def __init__(self, repo: GraphRepository):
        """
        Initialize graph service.

        Args:
            repo: GraphRepository instance
        """
        self.repo = repo

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
        label_to_node = {}  # Map concept text to node for edge creation
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

        Deduplication strategy (v2 simplified):
        1. Exact label match (case-insensitive)
        2. If match found, add utterance to provenance
        3. If no match, create new node

        Args:
            session_id: Session ID
            concept: Extracted concept
            utterance_id: Source utterance ID

        Returns:
            KGNode (existing or newly created)
        """
        # Try to find existing node
        existing = await self.repo.find_node_by_label(session_id, concept.text)

        if existing:
            log.debug(
                "node_deduplicated",
                label=concept.text,
                existing_id=existing.id,
            )
            # Add this utterance to provenance
            return await self.repo.add_source_utterance(existing.id, utterance_id)

        # Prepare node properties with linked_elements
        node_properties = dict(concept.properties)
        if concept.linked_elements:
            node_properties["linked_elements"] = concept.linked_elements

        # Create new node
        return await self.repo.create_node(
            session_id=session_id,
            label=concept.text,
            node_type=concept.node_type,
            confidence=concept.confidence,
            properties=node_properties,
            source_utterance_ids=[utterance_id],
            stance=concept.stance if concept.stance is not None else 0,
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

    async def get_session_graph(
        self, session_id: str
    ) -> Tuple[List[KGNode], List[KGEdge]]:
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
