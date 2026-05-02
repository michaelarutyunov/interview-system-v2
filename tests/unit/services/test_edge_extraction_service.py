"""Tests for UtteranceRepository.get_by_ids and edge_extraction_service.

Covers B3 acceptance criteria:
- get_by_ids returns utterances in stable order, deduped by ID
- Helper excludes nodes with source_utterance_ids == ["unknown"]
- Helper handles focus node introduced many turns ago (cross-turn focus jump)
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from src.persistence.repositories.utterance_repo import UtteranceRepository
from src.persistence.repositories.graph_repo import GraphRepository
from src.domain.models.utterance import Utterance
from src.services.edge_extraction_service import assemble_focus_derived_utterances


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime.now(timezone.utc)


def _make_utterance(
    uid: str,
    session_id: str = "test-session",
    turn_number: int = 1,
    speaker: str = "user",
    text: str = "",
) -> Utterance:
    return Utterance(
        id=uid,
        session_id=session_id,
        turn_number=turn_number,
        speaker=speaker,
        text=text or f"utterance {uid}",
        created_at=NOW,
    )


async def _save_node(
    graph_repo: GraphRepository,
    session_id: str,
    node_id: str,
    label: str,
    node_type: str,
    source_utterance_ids: list,
) -> None:
    """Create a node with a specific ID via direct DB insert.

    GraphRepository.create_node always generates a new UUID, so we insert
    directly to control the node ID for testing.
    """
    import json

    await graph_repo.db.execute(
        """
        INSERT INTO kg_nodes (
            id, session_id, label, node_type, confidence,
            properties, source_utterance_ids, source_quotes,
            recorded_at, superseded_by, stance
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            node_id,
            session_id,
            label,
            node_type,
            0.9,
            json.dumps({}),
            json.dumps(source_utterance_ids),
            json.dumps([]),
            NOW.isoformat(),
            None,
            0,
        ),
    )
    await graph_repo.db.commit()


async def _save_edge(
    graph_repo: GraphRepository,
    session_id: str,
    source_node_id: str,
    target_node_id: str,
    edge_type: str = "leads_to",
) -> str:
    """Create an edge and return its ID."""
    import json

    edge_id = str(uuid4())
    await graph_repo.db.execute(
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
            0.9,
            json.dumps({}),
            json.dumps([]),
            NOW.isoformat(),
        ),
    )
    await graph_repo.db.commit()
    return edge_id


# ---------------------------------------------------------------------------
# Tests: UtteranceRepository.get_by_ids
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_by_ids_empty(utterance_repo: UtteranceRepository):
    """Empty input list returns empty list."""
    result = await utterance_repo.get_by_ids([])
    assert result == []


@pytest.mark.asyncio
async def test_get_by_ids_returns_in_input_order(utterance_repo: UtteranceRepository):
    """Utterances are returned in the order of first occurrence in the input list."""
    utt_a = _make_utterance("utt-a", turn_number=1, text="first")
    utt_b = _make_utterance("utt-b", turn_number=2, text="second")
    utt_c = _make_utterance("utt-c", turn_number=3, text="third")

    await utterance_repo.save(utt_a)
    await utterance_repo.save(utt_b)
    await utterance_repo.save(utt_c)

    # Request in reverse order
    result = await utterance_repo.get_by_ids(["utt-c", "utt-b", "utt-a"])
    assert [u.id for u in result] == ["utt-c", "utt-b", "utt-a"]


@pytest.mark.asyncio
async def test_get_by_ids_deduplicates_by_id(utterance_repo: UtteranceRepository):
    """Duplicate IDs in input are collapsed to first occurrence."""
    utt_a = _make_utterance("utt-a")
    await utterance_repo.save(utt_a)

    result = await utterance_repo.get_by_ids(["utt-a", "utt-a", "utt-a"])
    assert len(result) == 1
    assert result[0].id == "utt-a"


@pytest.mark.asyncio
async def test_get_by_ids_missing_ids_dropped_silently(
    utterance_repo: UtteranceRepository,
):
    """IDs that don't exist in the DB are silently dropped."""
    utt_a = _make_utterance("utt-a")
    await utterance_repo.save(utt_a)

    result = await utterance_repo.get_by_ids(
        ["utt-missing", "utt-a", "utt-also-missing"]
    )
    assert len(result) == 1
    assert result[0].id == "utt-a"


@pytest.mark.asyncio
async def test_get_by_ids_all_missing_returns_empty(
    utterance_repo: UtteranceRepository,
):
    """When all IDs are missing, returns empty list."""
    utt_a = _make_utterance("utt-a")
    await utterance_repo.save(utt_a)

    result = await utterance_repo.get_by_ids(["utt-x", "utt-y"])
    assert result == []


@pytest.mark.asyncio
async def test_get_by_ids_stable_order_with_duplicates_and_missing(
    utterance_repo: UtteranceRepository,
):
    """Combined: dedup preserves first-occurrence order, missing dropped."""
    utt_a = _make_utterance("utt-a", turn_number=1)
    utt_b = _make_utterance("utt-b", turn_number=2)
    await utterance_repo.save(utt_a)
    await utterance_repo.save(utt_b)

    # b appears first in input, so it should come first in output
    result = await utterance_repo.get_by_ids(
        ["utt-b", "utt-missing", "utt-a", "utt-b", "utt-also-missing"]
    )
    assert [u.id for u in result] == ["utt-b", "utt-a"]


# ---------------------------------------------------------------------------
# Tests: assemble_focus_derived_utterances
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assemble_focus_node_not_found(graph_repo, utterance_repo):
    """Returns empty list when focus node doesn't exist."""
    result = await assemble_focus_derived_utterances(
        graph_repo=graph_repo,
        utterance_repo=utterance_repo,
        focus_node_id="nonexistent-node",
        current_turn=1,
        previous_question_utterance_id="",
    )
    assert result == []


@pytest.mark.asyncio
async def test_assemble_all_unknown_source_ids(graph_repo, utterance_repo):
    """Nodes with source_utterance_ids == ["unknown"] are excluded from results."""
    session_id = "test-all-unknown"

    # Save a user utterance for the current turn so the assembler has something
    # to try (but it should find nothing from the nodes)
    utt = _make_utterance("utt-current", session_id=session_id, turn_number=1)
    await utterance_repo.save(utt)

    # Focus node with ["unknown"] source
    await _save_node(
        graph_repo,
        session_id,
        "focus-1",
        "focus label",
        "attribute",
        source_utterance_ids=["unknown"],
    )
    # Neighbor node also ["unknown"]
    await _save_node(
        graph_repo,
        session_id,
        "neighbor-1",
        "neighbor label",
        "attribute",
        source_utterance_ids=["unknown"],
    )
    await _save_edge(graph_repo, session_id, "focus-1", "neighbor-1")

    result = await assemble_focus_derived_utterances(
        graph_repo=graph_repo,
        utterance_repo=utterance_repo,
        focus_node_id="focus-1",
        current_turn=1,
        previous_question_utterance_id="",
    )

    # Only the current turn's user utterance should appear (from get_by_turn)
    # The ["unknown"] source IDs from nodes are excluded
    assert len(result) == 1
    assert result[0].id == "utt-current"


@pytest.mark.asyncio
async def test_assemble_mixed_unknown_and_valid(graph_repo, utterance_repo):
    """Mixed: unknown source IDs are excluded, valid ones plus current turn included."""
    session_id = "test-mixed"

    utt_1 = _make_utterance("utt-1", session_id=session_id, turn_number=1)
    utt_2 = _make_utterance("utt-2", session_id=session_id, turn_number=2)
    utt_3 = _make_utterance(
        "utt-3", session_id=session_id, turn_number=3, speaker="user", text="current"
    )
    await utterance_repo.save(utt_1)
    await utterance_repo.save(utt_2)
    await utterance_repo.save(utt_3)

    # Focus node with mixed valid + unknown
    await _save_node(
        graph_repo,
        session_id,
        "focus-1",
        "focus",
        "attribute",
        source_utterance_ids=["utt-1", "unknown"],
    )
    # Neighbor with valid only
    await _save_node(
        graph_repo,
        session_id,
        "nb-1",
        "neighbor",
        "attribute",
        source_utterance_ids=["utt-2"],
    )
    # Neighbor with unknown only -- should contribute nothing
    await _save_node(
        graph_repo,
        session_id,
        "nb-unknown",
        "ghost",
        "attribute",
        source_utterance_ids=["unknown"],
    )

    await _save_edge(graph_repo, session_id, "focus-1", "nb-1")
    await _save_edge(graph_repo, session_id, "focus-1", "nb-unknown")

    result = await assemble_focus_derived_utterances(
        graph_repo=graph_repo,
        utterance_repo=utterance_repo,
        focus_node_id="focus-1",
        current_turn=3,
        previous_question_utterance_id="",
    )

    ids = {u.id for u in result}
    # utt-1 from focus node, utt-2 from nb-1, utt-3 from current turn
    assert ids == {"utt-1", "utt-2", "utt-3"}


@pytest.mark.asyncio
async def test_assemble_missing_ids(graph_repo, utterance_repo):
    """Valid utterance IDs that don't exist in the DB are silently dropped."""
    session_id = "test-missing"

    utt_real = _make_utterance("utt-real", session_id=session_id, turn_number=1)
    await utterance_repo.save(utt_real)

    # Focus node references an ID that doesn't exist in the utterances table
    await _save_node(
        graph_repo,
        session_id,
        "focus-1",
        "focus",
        "attribute",
        source_utterance_ids=["utt-real", "utt-ghost"],
    )

    result = await assemble_focus_derived_utterances(
        graph_repo=graph_repo,
        utterance_repo=utterance_repo,
        focus_node_id="focus-1",
        current_turn=1,
        previous_question_utterance_id="",
    )

    # Only utt-real should appear; utt-ghost is silently dropped
    ids = {u.id for u in result}
    assert "utt-real" in ids
    assert "utt-ghost" not in ids


@pytest.mark.asyncio
async def test_assemble_cross_turn_focus_jump(graph_repo, utterance_repo):
    """Focus node introduced many turns ago -- its source utterances are still included.

    Scenario:
    - Turn 2: focus node created with utterance "utt-turn2"
    - Turn 9: strategy jumps back to focus node from turn 2
    - Current turn is 9, so turn 9's user utterance is also included
    - Neighbor from turn 5 with utterance "utt-turn5" is also included
    """
    session_id = "test-cross-turn"

    # Create utterances across multiple turns
    utt_q1 = _make_utterance(
        "utt-q1",
        session_id=session_id,
        turn_number=1,
        speaker="system",
        text="intro question",
    )
    utt_t2 = _make_utterance(
        "utt-turn2",
        session_id=session_id,
        turn_number=2,
        speaker="user",
        text="turn 2 response",
    )
    utt_q2 = _make_utterance(
        "utt-q2",
        session_id=session_id,
        turn_number=2,
        speaker="system",
        text="question 2",
    )
    utt_t5 = _make_utterance(
        "utt-turn5",
        session_id=session_id,
        turn_number=5,
        speaker="user",
        text="turn 5 response",
    )
    utt_t9 = _make_utterance(
        "utt-turn9",
        session_id=session_id,
        turn_number=9,
        speaker="user",
        text="turn 9 response",
    )
    utt_q9 = _make_utterance(
        "utt-q9",
        session_id=session_id,
        turn_number=9,
        speaker="system",
        text="question 9",
    )

    for u in [utt_q1, utt_t2, utt_q2, utt_t5, utt_t9, utt_q9]:
        await utterance_repo.save(u)

    # Focus node from turn 2
    await _save_node(
        graph_repo,
        session_id,
        "focus-turn2",
        "old focus",
        "attribute",
        source_utterance_ids=["utt-turn2"],
    )
    # Neighbor from turn 5
    await _save_node(
        graph_repo,
        session_id,
        "nb-turn5",
        "neighbor from t5",
        "attribute",
        source_utterance_ids=["utt-turn5"],
    )
    await _save_edge(graph_repo, session_id, "focus-turn2", "nb-turn5")

    # Now: strategy jumps to "focus-turn2" at turn 9
    result = await assemble_focus_derived_utterances(
        graph_repo=graph_repo,
        utterance_repo=utterance_repo,
        focus_node_id="focus-turn2",
        current_turn=9,
        previous_question_utterance_id="utt-q9",
    )

    ids = {u.id for u in result}
    # Should include: utt-turn2 (focus node), utt-turn5 (neighbor),
    # utt-turn9 (current turn user), utt-q9 (previous question)
    assert "utt-turn2" in ids, "Turn 2 utterance from focus node should be included"
    assert "utt-turn5" in ids, "Turn 5 utterance from neighbor should be included"
    assert "utt-turn9" in ids, "Turn 9 current user utterance should be included"
    assert "utt-q9" in ids, "Previous interviewer question should be included"
    # Should NOT include random other utterances
    assert "utt-q1" not in ids, "Turn 1 question is unrelated"
    assert "utt-q2" not in ids, "Turn 2 question is unrelated"


@pytest.mark.asyncio
async def test_assemble_previous_question_included(graph_repo, utterance_repo):
    """Previous interviewer question utterance is included in the result set."""
    session_id = "test-prev-q"

    utt_user = _make_utterance(
        "utt-user",
        session_id=session_id,
        turn_number=2,
        speaker="user",
        text="response",
    )
    utt_prev_q = _make_utterance(
        "utt-prev-q",
        session_id=session_id,
        turn_number=2,
        speaker="system",
        text="interviewer question",
    )
    await utterance_repo.save(utt_user)
    await utterance_repo.save(utt_prev_q)

    await _save_node(
        graph_repo,
        session_id,
        "focus-1",
        "focus",
        "attribute",
        source_utterance_ids=["utt-user"],
    )

    result = await assemble_focus_derived_utterances(
        graph_repo=graph_repo,
        utterance_repo=utterance_repo,
        focus_node_id="focus-1",
        current_turn=2,
        previous_question_utterance_id="utt-prev-q",
    )

    ids = {u.id for u in result}
    assert "utt-prev-q" in ids
    assert "utt-user" in ids


@pytest.mark.asyncio
async def test_assemble_empty_previous_question_handled(graph_repo, utterance_repo):
    """Empty string for previous_question_utterance_id is handled gracefully."""
    session_id = "test-empty-prev-q"

    utt = _make_utterance("utt-1", session_id=session_id, turn_number=1)
    await utterance_repo.save(utt)

    await _save_node(
        graph_repo,
        session_id,
        "focus-1",
        "focus",
        "attribute",
        source_utterance_ids=["utt-1"],
    )

    result = await assemble_focus_derived_utterances(
        graph_repo=graph_repo,
        utterance_repo=utterance_repo,
        focus_node_id="focus-1",
        current_turn=1,
        previous_question_utterance_id="",
    )

    assert len(result) == 1
    assert result[0].id == "utt-1"
