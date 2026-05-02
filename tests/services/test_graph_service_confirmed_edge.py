"""
Test GraphService._add_edge_from_relationship with ConfirmedEdge input.

Validates B6 (D5): the method accepts ConfirmedEdge (Stage 4.5B) in addition
to ExtractedRelationship (legacy Stage 3). Both paths share the same
post-dedup is_valid_connection enforcement point.

Acceptance criteria:
- ConfirmedEdge with valid types creates edge
- ConfirmedEdge with invalid type pair behaves identically to ExtractedRelationship
- Dedup against existing edge calls add_edge_source_utterance
"""

import pytest
from datetime import datetime, timezone

from src.services.graph_service import GraphService
from src.domain.models.edge_extraction import ConfirmedEdge
from src.domain.models.extraction import (
    ExtractionResult,
    ExtractedConcept,
    ExtractedRelationship,
)
from src.domain.models.session import Session, SessionState
from src.domain.models.interview_state import InterviewMode


@pytest.mark.asyncio
async def test_confirmed_edge_valid_types_creates_edge(graph_repo, session_repo):
    """
    ConfirmedEdge with valid type pair creates an edge.

    Setup: attribute node (t1) + functional_consequence node (t2).
    MEC strict permits attribute -> functional_consequence via leads_to.
    """
    session_id = "test-ce-valid"
    now = datetime.now(timezone.utc)

    session = Session(
        id=session_id,
        methodology="means_end_chain_v2_strict",
        concept_id="test_concept",
        concept_name="Test Concept",
        created_at=now,
        updated_at=now,
        state=SessionState(
            methodology="means_end_chain_v2_strict",
            concept_id="test_concept",
            concept_name="Test Concept",
            turn_count=0,
            mode=InterviewMode.EXPLORATORY,
        ),
        mode=InterviewMode.EXPLORATORY,
        status="active",
    )
    await session_repo.create(session=session)

    graph_service = GraphService(graph_repo)

    # Create two nodes
    node_attr = ExtractedConcept(
        text="creamy texture",
        node_type="attribute",
        confidence=0.9,
        source_utterance_id="utt-1",
    )
    node_func = ExtractedConcept(
        text="easier to digest",
        node_type="functional_consequence",
        confidence=0.9,
        source_utterance_id="utt-2",
    )

    extraction = ExtractionResult(
        concepts=[node_attr, node_func],
        relationships=[],
        is_extractable=True,
        latency_ms=100,
    )

    nodes, _edges = await graph_service.add_extraction_to_graph(
        session_id=session_id,
        extraction=extraction,
        utterance_id="utt-0",
    )

    assert len(nodes) == 2
    attr_node = next(n for n in nodes if n.node_type == "attribute")
    func_node = next(n for n in nodes if n.node_type == "functional_consequence")

    # Create ConfirmedEdge between them
    confirmed = ConfirmedEdge(
        source_node_id=attr_node.id,
        target_node_id=func_node.id,
        edge_type="leads_to",
        confidence="high",
        supporting_span=(0, 10),
        utterance_id="utt-3",
        reasoning_summary="Direct connection",
    )

    edge = await graph_service._add_edge_from_relationship(
        session_id=session_id,
        relationship=confirmed,
        methodology="means_end_chain_v2_strict",
    )

    # Assert edge was created
    assert edge is not None, "Valid ConfirmedEdge should create an edge"
    assert edge.edge_type == "leads_to"
    assert edge.source_node_id == attr_node.id
    assert edge.target_node_id == func_node.id
    # Verify provenance uses the ConfirmedEdge's utterance_id, not a parameter default
    assert "utt-3" in edge.source_utterance_ids


@pytest.mark.asyncio
async def test_confirmed_edge_invalid_types_mirrors_extracted_relationship(
    graph_repo, session_repo
):
    """
    ConfirmedEdge with invalid type pair behaves identically to
    ExtractedRelationship with the same invalid pair.

    MEC strict does NOT permit attribute -> terminal_value via leads_to.
    Both paths must return None (log-and-skip).
    """
    session_id = "test-ce-invalid-mirror"
    now = datetime.now(timezone.utc)

    session = Session(
        id=session_id,
        methodology="means_end_chain_v2_strict",
        concept_id="test_concept",
        concept_name="Test Concept",
        created_at=now,
        updated_at=now,
        state=SessionState(
            methodology="means_end_chain_v2_strict",
            concept_id="test_concept",
            concept_name="Test Concept",
            turn_count=0,
            mode=InterviewMode.EXPLORATORY,
        ),
        mode=InterviewMode.EXPLORATORY,
        status="active",
    )
    await session_repo.create(session=session)

    graph_service = GraphService(graph_repo)

    # Create two nodes: attribute + terminal_value
    node_attr = ExtractedConcept(
        text="creamy texture",
        node_type="attribute",
        confidence=0.9,
        source_utterance_id="utt-1",
    )
    node_term = ExtractedConcept(
        text="self-respect",
        node_type="terminal_value",
        confidence=0.9,
        source_utterance_id="utt-2",
    )

    extraction = ExtractionResult(
        concepts=[node_attr, node_term],
        relationships=[],
        is_extractable=True,
        latency_ms=100,
    )

    nodes, _edges = await graph_service.add_extraction_to_graph(
        session_id=session_id,
        extraction=extraction,
        utterance_id="utt-0",
    )

    assert len(nodes) == 2
    attr_node = next(n for n in nodes if n.node_type == "attribute")
    term_node = next(n for n in nodes if n.node_type == "terminal_value")

    # Path A: ExtractedRelationship with invalid type pair
    extracted_rel = ExtractedRelationship(
        source_text=attr_node.label,
        target_text=term_node.label,
        relationship_type="leads_to",
        confidence=0.8,
        reasoning="Invalid MEC connection",
        source_utterance_id="utt-3",
    )

    label_to_node = {n.label.lower(): n for n in nodes}
    result_extracted = await graph_service._add_edge_from_relationship(
        session_id=session_id,
        relationship=extracted_rel,
        label_to_node=label_to_node,
        utterance_id="utt-3",
        methodology="means_end_chain_v2_strict",
    )

    # Path B: ConfirmedEdge with the same invalid type pair
    confirmed = ConfirmedEdge(
        source_node_id=attr_node.id,
        target_node_id=term_node.id,
        edge_type="leads_to",
        confidence="high",
        supporting_span=(0, 10),
        utterance_id="utt-4",
        reasoning_summary="Invalid MEC connection",
    )

    result_confirmed = await graph_service._add_edge_from_relationship(
        session_id=session_id,
        relationship=confirmed,
        methodology="means_end_chain_v2_strict",
    )

    # Both paths must exhibit identical observable behavior: return None
    assert result_extracted is None, (
        "ExtractedRelationship with invalid type pair should return None"
    )
    assert result_confirmed is None, (
        "ConfirmedEdge with invalid type pair should return None (same as ExtractedRelationship)"
    )


@pytest.mark.asyncio
async def test_confirmed_edge_dedup_calls_add_edge_source_utterance(
    graph_repo, session_repo
):
    """
    ConfirmedEdge dedup: second edge with same (source, target, type) should
    call add_edge_source_utterance on the existing edge.

    This verifies that dedup via repo.find_edge + add_edge_source_utterance
    is retained for the ConfirmedEdge path.
    """
    session_id = "test-ce-dedup"
    now = datetime.now(timezone.utc)

    session = Session(
        id=session_id,
        methodology="means_end_chain_v2_strict",
        concept_id="test_concept",
        concept_name="Test Concept",
        created_at=now,
        updated_at=now,
        state=SessionState(
            methodology="means_end_chain_v2_strict",
            concept_id="test_concept",
            concept_name="Test Concept",
            turn_count=0,
            mode=InterviewMode.EXPLORATORY,
        ),
        mode=InterviewMode.EXPLORATORY,
        status="active",
    )
    await session_repo.create(session=session)

    graph_service = GraphService(graph_repo)

    # Create two nodes
    node_attr = ExtractedConcept(
        text="creamy texture",
        node_type="attribute",
        confidence=0.9,
        source_utterance_id="utt-1",
    )
    node_func = ExtractedConcept(
        text="easier to digest",
        node_type="functional_consequence",
        confidence=0.9,
        source_utterance_id="utt-2",
    )

    extraction = ExtractionResult(
        concepts=[node_attr, node_func],
        relationships=[],
        is_extractable=True,
        latency_ms=100,
    )

    nodes, _edges = await graph_service.add_extraction_to_graph(
        session_id=session_id,
        extraction=extraction,
        utterance_id="utt-0",
    )

    attr_node = next(n for n in nodes if n.node_type == "attribute")
    func_node = next(n for n in nodes if n.node_type == "functional_consequence")

    # First ConfirmedEdge
    confirmed_1 = ConfirmedEdge(
        source_node_id=attr_node.id,
        target_node_id=func_node.id,
        edge_type="leads_to",
        confidence="high",
        supporting_span=(0, 10),
        utterance_id="utt-3",
        reasoning_summary="First edge",
    )

    edge_1 = await graph_service._add_edge_from_relationship(
        session_id=session_id,
        relationship=confirmed_1,
        methodology="means_end_chain_v2_strict",
    )
    assert edge_1 is not None
    assert edge_1.source_utterance_ids == ["utt-3"]

    # Second ConfirmedEdge with same source/target/type -- should dedup
    confirmed_2 = ConfirmedEdge(
        source_node_id=attr_node.id,
        target_node_id=func_node.id,
        edge_type="leads_to",
        confidence="high",
        supporting_span=(0, 10),
        utterance_id="utt-4",
        reasoning_summary="Duplicate edge",
    )

    edge_2 = await graph_service._add_edge_from_relationship(
        session_id=session_id,
        relationship=confirmed_2,
        methodology="means_end_chain_v2_strict",
    )

    # Dedup should return the existing edge, now with both utterance IDs
    assert edge_2 is not None
    assert edge_2.id == edge_1.id, "Dedup should return existing edge, not create new"
    assert "utt-3" in edge_2.source_utterance_ids, (
        "Original utterance should be preserved"
    )
    assert "utt-4" in edge_2.source_utterance_ids, (
        "New utterance should be added via add_edge_source_utterance"
    )


@pytest.mark.asyncio
async def test_confirmed_edge_uses_own_utterance_id(graph_repo, session_repo):
    """
    ConfirmedEdge uses edge.utterance_id for provenance, NOT the method's
    utterance_id parameter.

    This verifies D5 requirement: "utterance_id arg comes from
    ConfirmedEdge.utterance_id (not the turn-current utterance)"
    """
    session_id = "test-ce-own-utt"
    now = datetime.now(timezone.utc)

    session = Session(
        id=session_id,
        methodology="means_end_chain_v2_strict",
        concept_id="test_concept",
        concept_name="Test Concept",
        created_at=now,
        updated_at=now,
        state=SessionState(
            methodology="means_end_chain_v2_strict",
            concept_id="test_concept",
            concept_name="Test Concept",
            turn_count=0,
            mode=InterviewMode.EXPLORATORY,
        ),
        mode=InterviewMode.EXPLORATORY,
        status="active",
    )
    await session_repo.create(session=session)

    graph_service = GraphService(graph_repo)

    # Create two nodes
    node_attr = ExtractedConcept(
        text="creamy texture",
        node_type="attribute",
        confidence=0.9,
        source_utterance_id="utt-1",
    )
    node_func = ExtractedConcept(
        text="easier to digest",
        node_type="functional_consequence",
        confidence=0.9,
        source_utterance_id="utt-2",
    )

    extraction = ExtractionResult(
        concepts=[node_attr, node_func],
        relationships=[],
        is_extractable=True,
        latency_ms=100,
    )

    nodes, _edges = await graph_service.add_extraction_to_graph(
        session_id=session_id,
        extraction=extraction,
        utterance_id="utt-0",
    )

    attr_node = next(n for n in nodes if n.node_type == "attribute")
    func_node = next(n for n in nodes if n.node_type == "functional_consequence")

    # Create ConfirmedEdge with its own utterance_id
    confirmed = ConfirmedEdge(
        source_node_id=attr_node.id,
        target_node_id=func_node.id,
        edge_type="leads_to",
        confidence="high",
        supporting_span=(0, 10),
        utterance_id="edge-specific-utt",
        reasoning_summary="Test utterance override",
    )

    # Pass a DIFFERENT utterance_id as the method parameter
    edge = await graph_service._add_edge_from_relationship(
        session_id=session_id,
        relationship=confirmed,
        utterance_id="turn-current-utt-should-be-ignored",
        methodology="means_end_chain_v2_strict",
    )

    assert edge is not None
    # Provenance must come from ConfirmedEdge.utterance_id, not the parameter
    assert "edge-specific-utt" in edge.source_utterance_ids, (
        "ConfirmedEdge.utterance_id should be used for provenance"
    )
    assert "turn-current-utt-should-be-ignored" not in edge.source_utterance_ids, (
        "Method's utterance_id parameter should not be used for ConfirmedEdge"
    )


@pytest.mark.asyncio
async def test_confirmed_edge_missing_node_returns_none(graph_repo, session_repo):
    """
    ConfirmedEdge referencing a non-existent node returns None,
    mirroring ExtractedRelationship behavior for missing nodes.
    """
    session_id = "test-ce-missing-node"
    now = datetime.now(timezone.utc)

    session = Session(
        id=session_id,
        methodology="means_end_chain_v2_strict",
        concept_id="test_concept",
        concept_name="Test Concept",
        created_at=now,
        updated_at=now,
        state=SessionState(
            methodology="means_end_chain_v2_strict",
            concept_id="test_concept",
            concept_name="Test Concept",
            turn_count=0,
            mode=InterviewMode.EXPLORATORY,
        ),
        mode=InterviewMode.EXPLORATORY,
        status="active",
    )
    await session_repo.create(session=session)

    graph_service = GraphService(graph_repo)

    # Create one real node
    node_attr = ExtractedConcept(
        text="creamy texture",
        node_type="attribute",
        confidence=0.9,
        source_utterance_id="utt-1",
    )

    extraction = ExtractionResult(
        concepts=[node_attr],
        relationships=[],
        is_extractable=True,
        latency_ms=100,
    )

    nodes, _edges = await graph_service.add_extraction_to_graph(
        session_id=session_id,
        extraction=extraction,
        utterance_id="utt-0",
    )

    attr_node = nodes[0]

    # ConfirmedEdge referencing a non-existent target node
    confirmed = ConfirmedEdge(
        source_node_id=attr_node.id,
        target_node_id="non-existent-node-id",
        edge_type="leads_to",
        confidence="medium",
        supporting_span=(0, 10),
        utterance_id="utt-2",
        reasoning_summary="Missing target",
    )

    result = await graph_service._add_edge_from_relationship(
        session_id=session_id,
        relationship=confirmed,
        methodology="means_end_chain_v2_strict",
    )

    assert result is None, "ConfirmedEdge with missing node should return None"


@pytest.mark.asyncio
async def test_confirmed_edge_without_methodology_skips_validation(
    graph_repo, session_repo
):
    """
    ConfirmedEdge without methodology parameter skips is_valid_connection,
    same as ExtractedRelationship behavior.
    """
    session_id = "test-ce-no-methodology"
    now = datetime.now(timezone.utc)

    session = Session(
        id=session_id,
        methodology="means_end_chain_v2_strict",
        concept_id="test_concept",
        concept_name="Test Concept",
        created_at=now,
        updated_at=now,
        state=SessionState(
            methodology="means_end_chain_v2_strict",
            concept_id="test_concept",
            concept_name="Test Concept",
            turn_count=0,
            mode=InterviewMode.EXPLORATORY,
        ),
        mode=InterviewMode.EXPLORATORY,
        status="active",
    )
    await session_repo.create(session=session)

    graph_service = GraphService(graph_repo)

    # Create two nodes: attribute + terminal_value (INVALID pair in MEC)
    node_attr = ExtractedConcept(
        text="creamy texture",
        node_type="attribute",
        confidence=0.9,
        source_utterance_id="utt-1",
    )
    node_term = ExtractedConcept(
        text="self-respect",
        node_type="terminal_value",
        confidence=0.9,
        source_utterance_id="utt-2",
    )

    extraction = ExtractionResult(
        concepts=[node_attr, node_term],
        relationships=[],
        is_extractable=True,
        latency_ms=100,
    )

    nodes, _edges = await graph_service.add_extraction_to_graph(
        session_id=session_id,
        extraction=extraction,
        utterance_id="utt-0",
    )

    attr_node = next(n for n in nodes if n.node_type == "attribute")
    term_node = next(n for n in nodes if n.node_type == "terminal_value")

    # ConfirmedEdge with invalid type pair but NO methodology
    confirmed = ConfirmedEdge(
        source_node_id=attr_node.id,
        target_node_id=term_node.id,
        edge_type="leads_to",
        confidence="medium",
        supporting_span=(0, 10),
        utterance_id="utt-3",
        reasoning_summary="No methodology = no validation",
    )

    result = await graph_service._add_edge_from_relationship(
        session_id=session_id,
        relationship=confirmed,
        # methodology NOT provided
    )

    # Without methodology, validation is skipped -- edge should be created
    assert result is not None, (
        "ConfirmedEdge without methodology should skip validation and create edge"
    )
    assert result.edge_type == "leads_to"
