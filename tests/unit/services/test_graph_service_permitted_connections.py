"""
Test permitted_connections validation for edges via ConfirmedEdge path.

Since B11 removed ExtractedRelationship, add_extraction_to_graph no longer
processes relationships. Validation is tested directly via _add_edge_from_relationship
with ConfirmedEdge objects.
"""

import pytest
from datetime import datetime, timezone

from src.services.graph_service import GraphService
from src.domain.models.extraction import (
    ExtractionResult,
    ExtractedConcept,
)
from src.domain.models.edge_extraction import ConfirmedEdge
from src.domain.models.session import Session, SessionState
from src.domain.models.interview_state import InterviewMode

_EDGE_KWARGS = {"supporting_span": (0, 10), "reasoning_summary": "Test edge"}


@pytest.mark.asyncio
async def test_cross_turn_edge_validation_rejects_invalid_connection(
    graph_repo, session_repo
):
    """Invalid type pair (attribute→terminal_value) should be rejected."""
    session_id = "test-cross-turn-validation"
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

    turn1_concept = ExtractedConcept(
        text="creamy texture",
        node_type="attribute",
        confidence=0.9,
        source_utterance_id="turn1-utt",
    )
    turn1_extraction = ExtractionResult(
        concepts=[turn1_concept], is_extractable=True, latency_ms=100
    )
    nodes_t1, _ = await graph_service.add_extraction_to_graph(
        session_id=session_id, extraction=turn1_extraction, utterance_id="turn1-utt"
    )
    assert len(nodes_t1) == 1
    assert nodes_t1[0].node_type == "attribute"

    turn2_concept = ExtractedConcept(
        text="self-respect",
        node_type="terminal_value",
        confidence=0.9,
        source_utterance_id="turn2-utt",
    )
    turn2_extraction = ExtractionResult(
        concepts=[turn2_concept], is_extractable=True, latency_ms=100
    )
    nodes_t2, _ = await graph_service.add_extraction_to_graph(
        session_id=session_id, extraction=turn2_extraction, utterance_id="turn2-utt"
    )
    assert len(nodes_t2) == 1

    invalid_edge = ConfirmedEdge(
        source_node_id=nodes_t1[0].id,
        target_node_id=nodes_t2[0].id,
        edge_type="leads_to",
        confidence="medium",
        utterance_id="turn2-utt",
        **_EDGE_KWARGS,
    )
    result = await graph_service._add_edge_from_relationship(
        session_id=session_id,
        relationship=invalid_edge,
        methodology="means_end_chain_v2_strict",
    )
    assert result is None, "Invalid cross-turn edge should be rejected"


@pytest.mark.asyncio
async def test_cross_turn_edge_validation_accepts_valid_connection(
    graph_repo, session_repo
):
    """Valid type pair (attribute→functional_consequence) should be accepted."""
    session_id = "test-valid-cross-turn"
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

    turn1_concept = ExtractedConcept(
        text="creamy texture",
        node_type="attribute",
        confidence=0.9,
        source_utterance_id="turn1-utt",
    )
    turn1_extraction = ExtractionResult(
        concepts=[turn1_concept], is_extractable=True, latency_ms=100
    )
    nodes_t1, _ = await graph_service.add_extraction_to_graph(
        session_id=session_id, extraction=turn1_extraction, utterance_id="turn1-utt"
    )

    turn2_concept = ExtractedConcept(
        text="easier to digest",
        node_type="functional_consequence",
        confidence=0.9,
        source_utterance_id="turn2-utt",
    )
    turn2_extraction = ExtractionResult(
        concepts=[turn2_concept], is_extractable=True, latency_ms=100
    )
    nodes_t2, _ = await graph_service.add_extraction_to_graph(
        session_id=session_id, extraction=turn2_extraction, utterance_id="turn2-utt"
    )

    valid_edge = ConfirmedEdge(
        source_node_id=nodes_t1[0].id,
        target_node_id=nodes_t2[0].id,
        edge_type="leads_to",
        confidence="medium",
        utterance_id="turn2-utt",
        **_EDGE_KWARGS,
    )
    result = await graph_service._add_edge_from_relationship(
        session_id=session_id,
        relationship=valid_edge,
        methodology="means_end_chain_v2_strict",
    )
    assert result is not None, "Valid cross-turn edge should be accepted"
    assert result.edge_type == "leads_to"


@pytest.mark.asyncio
async def test_validation_skipped_when_methodology_not_provided(
    graph_repo, session_repo
):
    """Edge should be accepted when methodology is not provided (no validation)."""
    session_id = "test-no-methodology"
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

    turn1_concept = ExtractedConcept(
        text="creamy texture",
        node_type="attribute",
        confidence=0.9,
        source_utterance_id="turn1-utt",
    )
    turn1_extraction = ExtractionResult(
        concepts=[turn1_concept], is_extractable=True, latency_ms=100
    )
    nodes_t1, _ = await graph_service.add_extraction_to_graph(
        session_id=session_id, extraction=turn1_extraction, utterance_id="turn1-utt"
    )

    turn2_concept = ExtractedConcept(
        text="self-respect",
        node_type="terminal_value",
        confidence=0.9,
        source_utterance_id="turn2-utt",
    )
    turn2_extraction = ExtractionResult(
        concepts=[turn2_concept], is_extractable=True, latency_ms=100
    )
    nodes_t2, _ = await graph_service.add_extraction_to_graph(
        session_id=session_id, extraction=turn2_extraction, utterance_id="turn2-utt"
    )

    edge = ConfirmedEdge(
        source_node_id=nodes_t1[0].id,
        target_node_id=nodes_t2[0].id,
        edge_type="leads_to",
        confidence="medium",
        utterance_id="turn2-utt",
        **_EDGE_KWARGS,
    )
    result = await graph_service._add_edge_from_relationship(
        session_id=session_id,
        relationship=edge,
    )
    assert result is not None, "Edge should be accepted when methodology not provided"


@pytest.mark.asyncio
async def test_revises_edge_always_permitted(graph_repo, session_repo):
    """Revises edges should always be permitted (wildcard in schema)."""
    session_id = "test-revises-permitted"
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

    c1 = ExtractedConcept(
        text="creamy texture",
        node_type="attribute",
        confidence=0.9,
        source_utterance_id="turn1-utt",
    )
    c2 = ExtractedConcept(
        text="self-respect",
        node_type="terminal_value",
        confidence=0.9,
        source_utterance_id="turn2-utt",
    )

    nodes1, _ = await graph_service.add_extraction_to_graph(
        session_id=session_id,
        extraction=ExtractionResult(concepts=[c1], is_extractable=True, latency_ms=100),
        utterance_id="turn1-utt",
    )
    nodes2, _ = await graph_service.add_extraction_to_graph(
        session_id=session_id,
        extraction=ExtractionResult(concepts=[c2], is_extractable=True, latency_ms=100),
        utterance_id="turn2-utt",
    )

    revises_edge = ConfirmedEdge(
        source_node_id=nodes1[0].id,
        target_node_id=nodes2[0].id,
        edge_type="revises",
        confidence="medium",
        utterance_id="turn2-utt",
        **_EDGE_KWARGS,
    )
    result = await graph_service._add_edge_from_relationship(
        session_id=session_id,
        relationship=revises_edge,
        methodology="means_end_chain_v2_strict",
    )
    assert result is not None, "Revises edge should be permitted (wildcard)"
    assert result.edge_type == "revises"
