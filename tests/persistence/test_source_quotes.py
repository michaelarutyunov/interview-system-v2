"""
Tests for source_quotes traceability on KGNode (bead u0d6).

TDD: tests written before implementation — all should fail initially.
"""

import pytest
import pytest_asyncio


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def session_and_utterance(session_repo, utterance_repo):
    """Create a session and utterance to satisfy FK constraints."""
    from datetime import datetime, timezone
    from src.domain.models.session import Session, SessionState, InterviewMode

    now = datetime.now(timezone.utc)
    session_obj = Session(
        id="test-session-quotes",
        methodology="means_end_chain",
        concept_id="test-concept",
        concept_name="Test Product",
        mode=InterviewMode.EXPLORATORY,
        created_at=now,
        updated_at=now,
        state=SessionState(
            methodology="means_end_chain",
            concept_id="test-concept",
            concept_name="Test Product",
        ),
    )
    session = await session_repo.create(session_obj)

    from uuid import uuid4
    from src.domain.models.utterance import Utterance

    utterance_obj = Utterance(
        id=str(uuid4()),
        session_id=session.id,
        turn_number=1,
        speaker="user",
        text="I like the convenience of the product",
    )
    utterance = await utterance_repo.save(utterance_obj)
    return session, utterance


@pytest_asyncio.fixture
async def second_utterance(session_and_utterance, utterance_repo):
    """Create a second utterance for multi-quote merge tests."""
    from uuid import uuid4
    from src.domain.models.utterance import Utterance

    session, _ = session_and_utterance
    utterance_obj = Utterance(
        id=str(uuid4()),
        session_id=session.id,
        turn_number=2,
        speaker="user",
        text="It also saves me time in the morning",
    )
    return await utterance_repo.save(utterance_obj)


# ── Domain model ──────────────────────────────────────────────────────────────

def test_kgnode_has_source_quotes_field():
    """KGNode must have a source_quotes field (List[str]) defaulting to []."""
    from src.domain.models.knowledge_graph import KGNode

    node = KGNode(
        id="n1",
        session_id="s1",
        label="convenience",
        node_type="attribute",
        confidence=0.9,
    )
    assert hasattr(node, "source_quotes")
    assert node.source_quotes == []


def test_kgnode_source_quotes_accepts_list():
    """KGNode accepts source_quotes as a list of strings."""
    from src.domain.models.knowledge_graph import KGNode

    node = KGNode(
        id="n1",
        session_id="s1",
        label="convenience",
        node_type="attribute",
        confidence=0.9,
        source_quotes=["verbatim quote one", "verbatim quote two"],
    )
    assert node.source_quotes == ["verbatim quote one", "verbatim quote two"]


# ── Repository: create_node ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_node_stores_source_quotes(graph_repo, session_and_utterance):
    """create_node persists source_quotes to the database."""
    session, utterance = session_and_utterance

    node = await graph_repo.create_node(
        session_id=session.id,
        label="convenience",
        node_type="attribute",
        source_utterance_ids=[utterance.id],
        source_quotes=["I like the convenience of the product"],
    )

    assert node.source_quotes == ["I like the convenience of the product"]


@pytest.mark.asyncio
async def test_create_node_defaults_source_quotes_to_empty(graph_repo, session_and_utterance):
    """create_node without source_quotes stores an empty list."""
    session, utterance = session_and_utterance

    node = await graph_repo.create_node(
        session_id=session.id,
        label="convenience",
        node_type="attribute",
        source_utterance_ids=[utterance.id],
    )

    assert node.source_quotes == []


@pytest.mark.asyncio
async def test_get_node_returns_source_quotes(graph_repo, session_and_utterance):
    """get_node round-trips source_quotes from the DB correctly."""
    session, utterance = session_and_utterance

    created = await graph_repo.create_node(
        session_id=session.id,
        label="convenience",
        node_type="attribute",
        source_utterance_ids=[utterance.id],
        source_quotes=["the convenience of the product"],
    )

    fetched = await graph_repo.get_node(created.id)
    assert fetched is not None
    assert fetched.source_quotes == ["the convenience of the product"]


# ── Repository: add_source_utterance with quote ───────────────────────────────

@pytest.mark.asyncio
async def test_add_source_utterance_with_quote_appends_quote(
    graph_repo, session_and_utterance, second_utterance
):
    """add_source_utterance(quote=...) appends the quote to source_quotes."""
    session, first_utterance = session_and_utterance

    node = await graph_repo.create_node(
        session_id=session.id,
        label="saves time",
        node_type="consequence",
        source_utterance_ids=[first_utterance.id],
        source_quotes=["I like the convenience"],
    )

    updated = await graph_repo.add_source_utterance(
        node.id, second_utterance.id, quote="It also saves me time"
    )

    assert updated is not None
    assert second_utterance.id in updated.source_utterance_ids
    assert "It also saves me time" in updated.source_quotes
    assert "I like the convenience" in updated.source_quotes


@pytest.mark.asyncio
async def test_add_source_utterance_without_quote_does_not_add_empty(
    graph_repo, session_and_utterance, second_utterance
):
    """add_source_utterance without quote does not append anything to source_quotes."""
    session, first_utterance = session_and_utterance

    node = await graph_repo.create_node(
        session_id=session.id,
        label="saves time",
        node_type="consequence",
        source_utterance_ids=[first_utterance.id],
        source_quotes=["original quote"],
    )

    updated = await graph_repo.add_source_utterance(node.id, second_utterance.id)

    assert updated is not None
    assert updated.source_quotes == ["original quote"]


@pytest.mark.asyncio
async def test_add_source_utterance_deduplicates_quotes(
    graph_repo, session_and_utterance, second_utterance
):
    """Adding the same quote twice does not produce a duplicate entry."""
    session, first_utterance = session_and_utterance

    node = await graph_repo.create_node(
        session_id=session.id,
        label="saves time",
        node_type="consequence",
        source_utterance_ids=[first_utterance.id],
        source_quotes=["saves me time"],
    )

    # Add the same quote a second time
    updated = await graph_repo.add_source_utterance(
        node.id, second_utterance.id, quote="saves me time"
    )

    assert updated is not None
    assert updated.source_quotes.count("saves me time") == 1


# ── Repository: update_node ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_node_source_quotes(graph_repo, session_and_utterance):
    """update_node with source_quotes kwarg persists the new list."""
    session, utterance = session_and_utterance

    node = await graph_repo.create_node(
        session_id=session.id,
        label="quality",
        node_type="attribute",
        source_utterance_ids=[utterance.id],
    )

    updated = await graph_repo.update_node(
        node.id, source_quotes=["high quality beans"]
    )

    assert updated is not None
    assert updated.source_quotes == ["high quality beans"]


# ── Empty string guard ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_node_filters_empty_source_quote(graph_repo, session_and_utterance):
    """create_node with source_quotes=[''] stores empty list (empty strings filtered)."""
    session, utterance = session_and_utterance

    node = await graph_repo.create_node(
        session_id=session.id,
        label="quality",
        node_type="attribute",
        source_utterance_ids=[utterance.id],
        source_quotes=[""],
    )

    assert node.source_quotes == []


@pytest.mark.asyncio
async def test_add_source_utterance_filters_empty_quote(
    graph_repo, session_and_utterance, second_utterance
):
    """add_source_utterance with quote='' does not append to source_quotes."""
    session, first_utterance = session_and_utterance

    node = await graph_repo.create_node(
        session_id=session.id,
        label="quality",
        node_type="attribute",
        source_utterance_ids=[first_utterance.id],
        source_quotes=["original"],
    )

    updated = await graph_repo.add_source_utterance(node.id, second_utterance.id, quote="")

    assert updated is not None
    assert updated.source_quotes == ["original"]
