"""
Test GraphService._add_edge_from_relationship with ConfirmedEdge input.

Since B11 removed ExtractedRelationship, only the ConfirmedEdge path remains.
"""

import pytest
from datetime import datetime, timezone

from src.services.graph_service import GraphService
from src.domain.models.edge_extraction import ConfirmedEdge
from src.domain.models.extraction import (
    ExtractionResult,
    ExtractedConcept,
)
from src.domain.models.session import Session, SessionState
from src.domain.models.interview_state import InterviewMode

_EDGE_KWARGS = {"supporting_span": (0, 10), "reasoning_summary": "Test edge"}


@pytest.mark.asyncio
async def test_confirmed_edge_valid_types_creates_edge(graph_repo, session_repo):
    """ConfirmedEdge with valid type pair creates an edge."""
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
        concepts=[node_attr, node_func], is_extractable=True, latency_ms=100
    )
    nodes, _ = await graph_service.add_extraction_to_graph(
        session_id=session_id, extraction=extraction, utterance_id="utt-0"
    )
    assert len(nodes) == 2
    attr_node = next(n for n in nodes if n.node_type == "attribute")
    func_node = next(n for n in nodes if n.node_type == "functional_consequence")

    confirmed = ConfirmedEdge(
        source_node_id=attr_node.id,
        target_node_id=func_node.id,
        edge_type="leads_to",
        confidence="high",
        utterance_id="utt-3",
        **_EDGE_KWARGS,
    )
    edge = await graph_service._add_edge_from_relationship(
        session_id=session_id,
        relationship=confirmed,
        methodology="means_end_chain_v2_strict",
    )
    assert edge is not None
    assert edge.edge_type == "leads_to"
    assert edge.source_node_id == attr_node.id
    assert edge.target_node_id == func_node.id
    assert "utt-3" in edge.source_utterance_ids


@pytest.mark.asyncio
async def test_confirmed_edge_invalid_types_returns_none(graph_repo, session_repo):
    """ConfirmedEdge with invalid type pair must return None."""
    session_id = "test-ce-invalid"
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
        concepts=[node_attr, node_term], is_extractable=True, latency_ms=100
    )
    nodes, _ = await graph_service.add_extraction_to_graph(
        session_id=session_id, extraction=extraction, utterance_id="utt-0"
    )
    assert len(nodes) == 2
    attr_node = next(n for n in nodes if n.node_type == "attribute")
    term_node = next(n for n in nodes if n.node_type == "terminal_value")

    confirmed = ConfirmedEdge(
        source_node_id=attr_node.id,
        target_node_id=term_node.id,
        edge_type="leads_to",
        confidence="high",
        utterance_id="utt-4",
        **_EDGE_KWARGS,
    )
    result = await graph_service._add_edge_from_relationship(
        session_id=session_id,
        relationship=confirmed,
        methodology="means_end_chain_v2_strict",
    )
    assert result is None, "ConfirmedEdge with invalid type pair should return None"


@pytest.mark.asyncio
async def test_confirmed_edge_dedup_calls_add_edge_source_utterance(
    graph_repo, session_repo
):
    """Second edge with same (source, target, type) deduplicates."""
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
        concepts=[node_attr, node_func], is_extractable=True, latency_ms=100
    )
    nodes, _ = await graph_service.add_extraction_to_graph(
        session_id=session_id, extraction=extraction, utterance_id="utt-0"
    )
    attr_node = next(n for n in nodes if n.node_type == "attribute")
    func_node = next(n for n in nodes if n.node_type == "functional_consequence")

    e1 = ConfirmedEdge(
        source_node_id=attr_node.id,
        target_node_id=func_node.id,
        edge_type="leads_to",
        confidence="high",
        utterance_id="utt-3",
        **_EDGE_KWARGS,
    )
    edge1 = await graph_service._add_edge_from_relationship(
        session_id=session_id,
        relationship=e1,
        methodology="means_end_chain_v2_strict",
    )
    assert edge1 is not None

    e2 = ConfirmedEdge(
        source_node_id=attr_node.id,
        target_node_id=func_node.id,
        edge_type="leads_to",
        confidence="high",
        utterance_id="utt-4",
        **_EDGE_KWARGS,
    )
    edge2 = await graph_service._add_edge_from_relationship(
        session_id=session_id,
        relationship=e2,
        methodology="means_end_chain_v2_strict",
    )
    assert edge2 is not None
    assert "utt-3" in edge2.source_utterance_ids
    assert "utt-4" in edge2.source_utterance_ids


@pytest.mark.asyncio
async def test_confirmed_edge_uses_own_utterance_id(graph_repo, session_repo):
    """ConfirmedEdge provenance uses edge.utterance_id."""
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
        concepts=[node_attr, node_func], is_extractable=True, latency_ms=100
    )
    nodes, _ = await graph_service.add_extraction_to_graph(
        session_id=session_id, extraction=extraction, utterance_id="utt-0"
    )
    attr_node = next(n for n in nodes if n.node_type == "attribute")
    func_node = next(n for n in nodes if n.node_type == "functional_consequence")

    confirmed = ConfirmedEdge(
        source_node_id=attr_node.id,
        target_node_id=func_node.id,
        edge_type="leads_to",
        confidence="high",
        utterance_id="edge-specific-utt",
        **_EDGE_KWARGS,
    )
    edge = await graph_service._add_edge_from_relationship(
        session_id=session_id,
        relationship=confirmed,
        methodology="means_end_chain_v2_strict",
    )
    assert edge is not None
    assert "edge-specific-utt" in edge.source_utterance_ids


@pytest.mark.asyncio
async def test_confirmed_edge_missing_node_returns_none(graph_repo, session_repo):
    """Missing source or target node returns None."""
    session_id = "test-ce-missing"
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

    confirmed = ConfirmedEdge(
        source_node_id="nonexistent-1",
        target_node_id="nonexistent-2",
        edge_type="leads_to",
        confidence="high",
        utterance_id="utt-1",
        **_EDGE_KWARGS,
    )
    result = await graph_service._add_edge_from_relationship(
        session_id=session_id,
        relationship=confirmed,
        methodology="means_end_chain_v2_strict",
    )
    assert result is None


@pytest.mark.asyncio
async def test_confirmed_edge_without_methodology_skips_validation(
    graph_repo, session_repo
):
    """Edge accepted when methodology not provided (no validation)."""
    session_id = "test-ce-no-method"
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
        concepts=[node_attr, node_term], is_extractable=True, latency_ms=100
    )
    nodes, _ = await graph_service.add_extraction_to_graph(
        session_id=session_id, extraction=extraction, utterance_id="utt-0"
    )
    attr_node = next(n for n in nodes if n.node_type == "attribute")
    term_node = next(n for n in nodes if n.node_type == "terminal_value")

    confirmed = ConfirmedEdge(
        source_node_id=attr_node.id,
        target_node_id=term_node.id,
        edge_type="leads_to",
        confidence="high",
        utterance_id="utt-3",
        **_EDGE_KWARGS,
    )
    result = await graph_service._add_edge_from_relationship(
        session_id=session_id,
        relationship=confirmed,
    )
    assert result is not None
