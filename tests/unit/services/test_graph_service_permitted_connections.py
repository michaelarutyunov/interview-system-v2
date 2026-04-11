"""
Test permitted_connections validation for cross-turn edges.

This test validates the fix for bead ui0f: cross-turn edges that bypass
extraction-time validation should be rejected in GraphService after
dedup resolution when source and target node types violate the
methodology's permitted_connections schema.
"""

import pytest
from datetime import datetime, timezone

from src.services.graph_service import GraphService
from src.domain.models.extraction import (
    ExtractionResult,
    ExtractedConcept,
    ExtractedRelationship,
)
from src.domain.models.session import Session, SessionState
from src.domain.models.interview_state import InterviewMode


@pytest.mark.asyncio
async def test_cross_turn_edge_validation_rejects_invalid_connection(
    graph_repo, session_repo
):
    """
    Test that cross-turn edges violating permitted_connections are rejected.

    Scenario:
    1. Turn 1: Create an 'attribute' node
    2. Turn 2: Extract edge from prior 'attribute' to new 'terminal_value'
    3. Expected: Edge is rejected because attribute→terminal_value is not
       permitted in means_end_chain (must go through intermediate levels)

    This tests the fix for bead ui0f where extraction_service validation
    only checks current-turn concepts, allowing cross-turn edges to bypass
    validation.
    """
    session_id = "test-cross-turn-validation"
    now = datetime.now(timezone.utc)

    # Create session with means_end_chain methodology
    session = Session(
        id=session_id,
        methodology="means_end_chain",
        concept_id="test_concept",
        concept_name="Test Concept",
        created_at=now,
        updated_at=now,
        state=SessionState(
            methodology="means_end_chain",
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

    # Turn 1: Create an attribute node
    turn1_concept = ExtractedConcept(
        text="creamy texture",
        node_type="attribute",
        confidence=0.9,
        source_utterance_id="turn1-utt",
    )

    turn1_extraction = ExtractionResult(
        concepts=[turn1_concept],
        relationships=[],
        is_extractable=True,
        latency_ms=100,
    )

    nodes_t1, edges_t1 = await graph_service.add_extraction_to_graph(
        session_id=session_id,
        extraction=turn1_extraction,
        utterance_id="turn1-utt",
    )

    assert len(nodes_t1) == 1
    assert nodes_t1[0].node_type == "attribute"
    assert len(edges_t1) == 0

    # Turn 2: Try to create edge from attribute to terminal_value
    # This is INVALID in means_end_chain (must go: attribute → functional → psychosocial → instrumental → terminal)
    turn2_relationship = ExtractedRelationship(
        source_text="creamy texture",  # References turn1 node
        target_text="self-respect",  # New node this turn
        relationship_type="leads_to",
        confidence=0.8,
        reasoning="Direct connection test",
        source_utterance_id="turn2-utt",
    )

    turn2_target_concept = ExtractedConcept(
        text="self-respect",
        node_type="terminal_value",
        confidence=0.9,
        source_utterance_id="turn2-utt",
    )

    turn2_extraction = ExtractionResult(
        concepts=[turn2_target_concept],
        relationships=[turn2_relationship],
        is_extractable=True,
        latency_ms=100,
    )

    # This should reject the invalid cross-turn edge
    nodes_t2, edges_t2 = await graph_service.add_extraction_to_graph(
        session_id=session_id,
        extraction=turn2_extraction,
        utterance_id="turn2-utt",
        methodology="means_end_chain",  # Pass methodology to enable validation
    )

    # The target node should be created, but the edge should be rejected
    assert len(nodes_t2) == 1
    assert nodes_t2[0].node_type == "terminal_value"
    assert len(edges_t2) == 0, "Invalid cross-turn edge should be rejected"


@pytest.mark.asyncio
async def test_cross_turn_edge_validation_accepts_valid_connection(
    graph_repo, session_repo
):
    """
    Test that valid cross-turn edges are accepted.

    Scenario:
    1. Turn 1: Create an 'attribute' node
    2. Turn 2: Extract edge from prior 'attribute' to new 'functional_consequence'
    3. Expected: Edge is accepted because attribute→functional_consequence
       is permitted in means_end_chain

    This validates that the fix doesn't over-reject valid edges.
    """
    session_id = "test-valid-cross-turn"
    now = datetime.now(timezone.utc)

    session = Session(
        id=session_id,
        methodology="means_end_chain",
        concept_id="test_concept",
        concept_name="Test Concept",
        created_at=now,
        updated_at=now,
        state=SessionState(
            methodology="means_end_chain",
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

    # Turn 1: Create an attribute node
    turn1_concept = ExtractedConcept(
        text="creamy texture",
        node_type="attribute",
        confidence=0.9,
        source_utterance_id="turn1-utt",
    )

    turn1_extraction = ExtractionResult(
        concepts=[turn1_concept],
        relationships=[],
        is_extractable=True,
        latency_ms=100,
    )

    nodes_t1, edges_t1 = await graph_service.add_extraction_to_graph(
        session_id=session_id,
        extraction=turn1_extraction,
        utterance_id="turn1-utt",
    )

    assert len(nodes_t1) == 1
    assert nodes_t1[0].node_type == "attribute"

    # Turn 2: Create VALID edge from attribute to functional_consequence
    turn2_relationship = ExtractedRelationship(
        source_text="creamy texture",  # References turn1 node
        target_text="easier to digest",  # New node this turn
        relationship_type="leads_to",
        confidence=0.8,
        reasoning="Valid MEC connection",
        source_utterance_id="turn2-utt",
    )

    turn2_target_concept = ExtractedConcept(
        text="easier to digest",
        node_type="functional_consequence",
        confidence=0.9,
        source_utterance_id="turn2-utt",
    )

    turn2_extraction = ExtractionResult(
        concepts=[turn2_target_concept],
        relationships=[turn2_relationship],
        is_extractable=True,
        latency_ms=100,
    )

    nodes_t2, edges_t2 = await graph_service.add_extraction_to_graph(
        session_id=session_id,
        extraction=turn2_extraction,
        utterance_id="turn2-utt",
        methodology="means_end_chain",
    )

    # Both node and edge should be created
    assert len(nodes_t2) == 1
    assert nodes_t2[0].node_type == "functional_consequence"
    assert len(edges_t2) == 1, "Valid cross-turn edge should be accepted"
    assert edges_t2[0].edge_type == "leads_to"


@pytest.mark.asyncio
async def test_validation_skipped_when_methodology_not_provided(
    graph_repo, session_repo
):
    """
    Test that validation is skipped when methodology is not provided.

    This ensures backward compatibility: existing code that calls
    add_extraction_to_graph without methodology parameter continues
    to work (no validation).
    """
    session_id = "test-no-methodology"
    now = datetime.now(timezone.utc)

    session = Session(
        id=session_id,
        methodology="means_end_chain",
        concept_id="test_concept",
        concept_name="Test Concept",
        created_at=now,
        updated_at=now,
        state=SessionState(
            methodology="means_end_chain",
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

    # Turn 1: Create an attribute node
    turn1_concept = ExtractedConcept(
        text="creamy texture",
        node_type="attribute",
        confidence=0.9,
        source_utterance_id="turn1-utt",
    )

    turn1_extraction = ExtractionResult(
        concepts=[turn1_concept],
        relationships=[],
        is_extractable=True,
        latency_ms=100,
    )

    await graph_service.add_extraction_to_graph(
        session_id=session_id,
        extraction=turn1_extraction,
        utterance_id="turn1-utt",
    )

    # Turn 2: Create INVALID edge without methodology parameter
    # Should be accepted (no validation)
    turn2_relationship = ExtractedRelationship(
        source_text="creamy texture",
        target_text="self-respect",
        relationship_type="leads_to",
        confidence=0.8,
        reasoning="Direct connection",
        source_utterance_id="turn2-utt",
    )

    turn2_target_concept = ExtractedConcept(
        text="self-respect",
        node_type="terminal_value",
        confidence=0.9,
        source_utterance_id="turn2-utt",
    )

    turn2_extraction = ExtractionResult(
        concepts=[turn2_target_concept],
        relationships=[turn2_relationship],
        is_extractable=True,
        latency_ms=100,
    )

    # NO methodology parameter - validation skipped
    nodes_t2, edges_t2 = await graph_service.add_extraction_to_graph(
        session_id=session_id,
        extraction=turn2_extraction,
        utterance_id="turn2-utt",
        # methodology NOT provided - backward compatible
    )

    # Both node and edge should be created (no validation)
    assert len(nodes_t2) == 1
    assert len(edges_t2) == 1, "Edge should be accepted when methodology not provided"


@pytest.mark.asyncio
async def test_revises_edge_always_permitted(graph_repo, session_repo):
    """
    Test that revises edges are always permitted (wildcard in schema).

    The means_end_chain schema defines permitted_connections for
    revises as ["*", "*"], so any node type pair should be allowed.
    """
    session_id = "test-revises-permitted"
    now = datetime.now(timezone.utc)

    session = Session(
        id=session_id,
        methodology="means_end_chain",
        concept_id="test_concept",
        concept_name="Test Concept",
        created_at=now,
        updated_at=now,
        state=SessionState(
            methodology="means_end_chain",
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

    # Turn 1: Create a terminal_value node
    turn1_concept = ExtractedConcept(
        text="self-respect",
        node_type="terminal_value",
        confidence=0.9,
        source_utterance_id="turn1-utt",
    )

    turn1_extraction = ExtractionResult(
        concepts=[turn1_concept],
        relationships=[],
        is_extractable=True,
        latency_ms=100,
    )

    await graph_service.add_extraction_to_graph(
        session_id=session_id,
        extraction=turn1_extraction,
        utterance_id="turn1-utt",
    )

    # Turn 2: Create revises edge from attribute to terminal_value
    # This would be invalid for leads_to, but valid for revises (wildcard)
    turn2_relationship = ExtractedRelationship(
        source_text="creamy texture",  # New node (attribute)
        target_text="self-respect",  # Prior node (terminal_value)
        relationship_type="revises",
        confidence=0.8,
        reasoning="Correction",
        source_utterance_id="turn2-utt",
    )

    turn2_source_concept = ExtractedConcept(
        text="creamy texture",
        node_type="attribute",
        confidence=0.9,
        source_utterance_id="turn2-utt",
    )

    turn2_extraction = ExtractionResult(
        concepts=[turn2_source_concept],
        relationships=[turn2_relationship],
        is_extractable=True,
        latency_ms=100,
    )

    nodes_t2, edges_t2 = await graph_service.add_extraction_to_graph(
        session_id=session_id,
        extraction=turn2_extraction,
        utterance_id="turn2-utt",
        methodology="means_end_chain",
    )

    # Revises edge should be created (wildcard permits all)
    assert len(nodes_t2) == 1
    assert len(edges_t2) == 1, "Revises edge should be permitted (wildcard)"
    assert edges_t2[0].edge_type == "revises"
