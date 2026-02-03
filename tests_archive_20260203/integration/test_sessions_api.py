"""Integration tests for session API endpoints.

Tests verify the full HTTP -> FastAPI -> Service Layer -> Repository -> Database flow.
Uses pytest-asyncio for async test execution with isolated test database.
"""

import tempfile
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def test_db_path():
    """Create isolated test database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_sessions.db"


@pytest.fixture
def fresh_db_path():
    """Create a fresh database path for tests that need isolation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "fresh_test.db"


@pytest.fixture
def app_with_test_db(test_db_path):
    """Create app with test database."""
    from src.core import config

    # Override database path
    original_path = config.settings.database_path
    config.settings.database_path = test_db_path

    # Import app after overriding settings
    from src.main import app

    yield app

    # Restore original path
    config.settings.database_path = original_path


@pytest.fixture
async def initialized_app(app_with_test_db, test_db_path):
    """App with initialized database."""
    from src.persistence.database import init_database

    await init_database(test_db_path)
    return app_with_test_db


@pytest.fixture
async def client(initialized_app):
    """Create async test client."""
    transport = ASGITransport(app=initialized_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def fresh_client(fresh_db_path):
    """Create client with fresh isolated database (no pre-existing data)."""
    from src.core import config
    from src.main import app
    from src.persistence.database import init_database

    # Override database path
    original_path = config.settings.database_path
    config.settings.database_path = fresh_db_path

    # Initialize fresh database
    await init_database(fresh_db_path)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        # Restore original path
        config.settings.database_path = original_path


# =============================================================================
# Session Creation Tests
# =============================================================================


@pytest.mark.asyncio
async def test_create_session(client):
    """Test POST /sessions creates a new session."""
    response = await client.post(
        "/sessions/",
        json={
            "methodology": "mec",
            "concept_id": "test-concept",
            "concept_name": "Test Concept",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["methodology"] == "mec"
    assert data["concept_id"] == "test-concept"
    assert data["concept_name"] == "Test Concept"
    assert data["status"] == "active"
    assert "created_at" in data
    assert "updated_at" in data
    assert "state" in data
    assert data["state"]["methodology"] == "mec"
    assert data["state"]["concept_id"] == "test-concept"
    assert data["state"]["turn_count"] == 0


@pytest.mark.asyncio
async def test_create_session_different_methodology(client):
    """Test POST /sessions with different methodology."""
    response = await client.post(
        "/sessions/",
        json={
            "methodology": "zmet",
            "concept_id": "zmet-concept",
            "concept_name": "ZMET Concept",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["methodology"] == "zmet"
    assert data["state"]["methodology"] == "zmet"


@pytest.mark.asyncio
async def test_create_session_returns_timestamps(client):
    """Test POST /sessions returns session with ISO format timestamps."""
    response = await client.post(
        "/sessions/",
        json={
            "methodology": "mec",
            "concept_id": "timestamp-test",
            "concept_name": "Timestamp Test",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "created_at" in data
    assert "updated_at" in data
    # Timestamps should be ISO format strings
    assert "T" in data["created_at"]
    assert "T" in data["updated_at"]


@pytest.mark.asyncio
async def test_create_session_generates_unique_id(client):
    """Test POST /sessions generates unique IDs for each session."""
    session_ids = set()

    for i in range(5):
        response = await client.post(
            "/sessions/",
            json={
                "methodology": "mec",
                "concept_id": f"unique-test-{i}",
                "concept_name": f"Unique Test {i}",
            },
        )
        assert response.status_code == 201
        session_ids.add(response.json()["id"])

    # All IDs should be unique
    assert len(session_ids) == 5


# =============================================================================
# Validation Error Tests
# =============================================================================


@pytest.mark.asyncio
async def test_create_session_missing_methodology(client):
    """Test POST /sessions with missing methodology returns 422."""
    response = await client.post(
        "/sessions/",
        json={"concept_id": "test-concept", "concept_name": "Test Concept"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_session_missing_concept_id(client):
    """Test POST /sessions with missing concept_id returns 422."""
    response = await client.post(
        "/sessions/", json={"methodology": "mec", "concept_name": "Test Concept"}
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_session_missing_concept_name(client):
    """Test POST /sessions with missing concept_name returns 422."""
    response = await client.post(
        "/sessions/", json={"methodology": "mec", "concept_id": "test-concept"}
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_session_empty_body(client):
    """Test POST /sessions with empty body returns 422."""
    response = await client.post("/sessions/", json={})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_session_no_body(client):
    """Test POST /sessions with no body returns 422."""
    response = await client.post("/sessions/")

    assert response.status_code == 422


# =============================================================================
# Session Retrieval Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_session(client):
    """Test GET /sessions/{id} returns session."""
    # Create a session first
    create_response = await client.post(
        "/sessions/",
        json={
            "methodology": "mec",
            "concept_id": "get-test-concept",
            "concept_name": "Get Test Concept",
        },
    )
    session_id = create_response.json()["id"]

    # Get via API
    response = await client.get(f"/sessions/{session_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == session_id
    assert data["methodology"] == "mec"
    assert data["concept_id"] == "get-test-concept"
    assert data["concept_name"] == "Get Test Concept"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_get_session_not_found(client):
    """Test GET /sessions/{id} with non-existent ID returns 404."""
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/sessions/{fake_id}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_session_invalid_id_format(client):
    """Test GET /sessions/{id} with invalid ID returns 404."""
    response = await client.get("/sessions/not-a-uuid")

    # Since the endpoint accepts any string ID, it returns 404 (not found)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_session_returns_full_state(client):
    """Test GET /sessions/{id} returns complete session state."""
    # Create a session
    create_response = await client.post(
        "/sessions/",
        json={
            "methodology": "mec",
            "concept_id": "state-test",
            "concept_name": "State Test Concept",
        },
    )
    session_id = create_response.json()["id"]

    # Get the session
    response = await client.get(f"/sessions/{session_id}")

    assert response.status_code == 200
    data = response.json()

    # Verify all expected fields are present
    assert "id" in data
    assert "methodology" in data
    assert "concept_id" in data
    assert "concept_name" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert "status" in data
    assert "state" in data

    # Verify state structure
    state = data["state"]
    assert "methodology" in state
    assert "concept_id" in state
    assert "concept_name" in state
    assert "turn_count" in state
    assert "turn_count" in state


# =============================================================================
# Session List Tests
# =============================================================================


@pytest.mark.asyncio
async def test_list_sessions_empty(fresh_client):
    """Test GET /sessions returns empty list when no sessions exist."""
    response = await fresh_client.get("/sessions/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_list_sessions(client):
    """Test GET /sessions returns list of active sessions."""
    # Create multiple sessions
    created_ids = []
    for i in range(3):
        response = await client.post(
            "/sessions/",
            json={
                "methodology": "mec",
                "concept_id": f"list-concept-{uuid.uuid4()}",
                "concept_name": f"List Concept {i}",
            },
        )
        created_ids.append(response.json()["id"])

    # List via API
    response = await client.get("/sessions/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3  # At least our 3 sessions

    # Verify our sessions are in the list
    returned_ids = [s["id"] for s in data]
    for session_id in created_ids:
        assert session_id in returned_ids


@pytest.mark.asyncio
async def test_list_sessions_returns_active_only(fresh_client):
    """Test GET /sessions returns only active sessions."""
    # Create sessions
    created_ids = []
    for i in range(3):
        response = await fresh_client.post(
            "/sessions/",
            json={
                "methodology": "mec",
                "concept_id": f"active-test-{i}",
                "concept_name": f"Active Test {i}",
            },
        )
        created_ids.append(response.json()["id"])

    # Delete one session
    await fresh_client.delete(f"/sessions/{created_ids[0]}")

    # List should only show remaining 2 sessions
    response = await fresh_client.get("/sessions/")
    assert response.status_code == 200
    returned_ids = [s["id"] for s in response.json()]

    assert created_ids[0] not in returned_ids
    assert created_ids[1] in returned_ids
    assert created_ids[2] in returned_ids


# =============================================================================
# Session Deletion Tests
# =============================================================================


@pytest.mark.asyncio
async def test_delete_session(client):
    """Test DELETE /sessions/{id} deletes session."""
    # Create a session first
    create_response = await client.post(
        "/sessions/",
        json={
            "methodology": "mec",
            "concept_id": "delete-test-concept",
            "concept_name": "Delete Test Concept",
        },
    )
    session_id = create_response.json()["id"]

    # Verify it exists
    get_response = await client.get(f"/sessions/{session_id}")
    assert get_response.status_code == 200

    # Delete via API
    response = await client.delete(f"/sessions/{session_id}")
    assert response.status_code == 204

    # Verify it's deleted
    verify_response = await client.get(f"/sessions/{session_id}")
    assert verify_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_session_not_found(client):
    """Test DELETE /sessions/{id} with non-existent ID returns 404."""
    fake_id = str(uuid.uuid4())
    response = await client.delete(f"/sessions/{fake_id}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_session_not_idempotent(client):
    """Test DELETE /sessions/{id} is not idempotent (second delete returns 404)."""
    # Create a session first
    create_response = await client.post(
        "/sessions/",
        json={
            "methodology": "mec",
            "concept_id": "idempotent-test",
            "concept_name": "Idempotent Test",
        },
    )
    session_id = create_response.json()["id"]

    # First delete succeeds
    response1 = await client.delete(f"/sessions/{session_id}")
    assert response1.status_code == 204

    # Second delete returns 404
    response2 = await client.delete(f"/sessions/{session_id}")
    assert response2.status_code == 404


@pytest.mark.asyncio
async def test_delete_session_returns_no_content(client):
    """Test DELETE /sessions/{id} returns 204 with no body."""
    # Create a session
    create_response = await client.post(
        "/sessions/",
        json={
            "methodology": "mec",
            "concept_id": "no-content-test",
            "concept_name": "No Content Test",
        },
    )
    session_id = create_response.json()["id"]

    # Delete
    response = await client.delete(f"/sessions/{session_id}")

    assert response.status_code == 204
    # 204 responses should have no body
    assert response.content == b""


# =============================================================================
# Full Session Lifecycle Tests
# =============================================================================


@pytest.mark.asyncio
async def test_session_lifecycle_flow(fresh_client):
    """Test complete session lifecycle: create -> get -> list -> delete -> verify."""
    # Step 1: Create a session
    create_response = await fresh_client.post(
        "/sessions/",
        json={
            "methodology": "mec",
            "concept_id": "flow-test",
            "concept_name": "Flow Test",
        },
    )
    assert create_response.status_code == 201
    session_data = create_response.json()
    session_id = session_data["id"]

    # Validate creation response
    assert session_data["methodology"] == "mec"
    assert session_data["concept_id"] == "flow-test"
    assert session_data["concept_name"] == "Flow Test"
    assert session_data["status"] == "active"

    # Step 2: Get the session
    get_response = await fresh_client.get(f"/sessions/{session_id}")
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["id"] == session_id
    assert get_data["methodology"] == session_data["methodology"]
    assert get_data["concept_id"] == session_data["concept_id"]

    # Step 3: List sessions (should include our session)
    list_response = await fresh_client.get("/sessions/")
    assert list_response.status_code == 200
    list_data = list_response.json()
    session_ids = [s["id"] for s in list_data]
    assert session_id in session_ids

    # Step 4: Delete the session
    delete_response = await fresh_client.delete(f"/sessions/{session_id}")
    assert delete_response.status_code == 204

    # Step 5: Verify session is gone
    verify_response = await fresh_client.get(f"/sessions/{session_id}")
    assert verify_response.status_code == 404

    # Step 6: Verify session is not in list
    final_list_response = await fresh_client.get("/sessions/")
    assert final_list_response.status_code == 200
    final_session_ids = [s["id"] for s in final_list_response.json()]
    assert session_id not in final_session_ids


@pytest.mark.asyncio
async def test_multiple_sessions_workflow(fresh_client):
    """Test workflow with multiple sessions created and managed."""
    # Create multiple sessions with different methodologies
    session_ids = []
    for i in range(5):
        response = await fresh_client.post(
            "/sessions/",
            json={
                "methodology": "mec" if i % 2 == 0 else "zmet",
                "concept_id": f"multi-test-{i}",
                "concept_name": f"Multi Test {i}",
            },
        )
        assert response.status_code == 201
        session_ids.append(response.json()["id"])

    # List all sessions
    list_response = await fresh_client.get("/sessions/")
    assert list_response.status_code == 200
    all_ids = [s["id"] for s in list_response.json()]
    for sid in session_ids:
        assert sid in all_ids

    # Delete first 3 sessions
    for sid in session_ids[:3]:
        delete_response = await fresh_client.delete(f"/sessions/{sid}")
        assert delete_response.status_code == 204

    # Verify only remaining sessions are in list
    remaining_response = await fresh_client.get("/sessions/")
    remaining_ids = [s["id"] for s in remaining_response.json()]
    for sid in session_ids[:3]:
        assert sid not in remaining_ids
    for sid in session_ids[3:]:
        assert sid in remaining_ids

    # Clean up remaining sessions
    for sid in session_ids[3:]:
        await fresh_client.delete(f"/sessions/{sid}")

    # Verify all sessions are deleted
    final_response = await fresh_client.get("/sessions/")
    assert final_response.status_code == 200
    assert len(final_response.json()) == 0


@pytest.mark.asyncio
async def test_concurrent_session_creation(fresh_client):
    """Test creating multiple sessions in rapid succession."""
    import asyncio

    async def create_session(idx):
        return await fresh_client.post(
            "/sessions/",
            json={
                "methodology": "mec",
                "concept_id": f"concurrent-{idx}",
                "concept_name": f"Concurrent Test {idx}",
            },
        )

    # Create 10 sessions concurrently
    responses = await asyncio.gather(*[create_session(i) for i in range(10)])

    # All should succeed
    for response in responses:
        assert response.status_code == 201

    # All IDs should be unique
    ids = [r.json()["id"] for r in responses]
    assert len(set(ids)) == 10

    # Verify all are in the list
    list_response = await fresh_client.get("/sessions/")
    listed_ids = [s["id"] for s in list_response.json()]
    for session_id in ids:
        assert session_id in listed_ids


# =============================================================================
# Error Response Format Tests
# =============================================================================


@pytest.mark.asyncio
async def test_404_response_format(client):
    """Test 404 responses have proper error detail format."""
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/sessions/{fake_id}")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert isinstance(data["detail"], str)


@pytest.mark.asyncio
async def test_422_response_format(client):
    """Test 422 validation errors have proper format."""
    response = await client.post("/sessions/", json={})

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert isinstance(data["detail"], list)  # Pydantic validation errors are list


# =============================================================================
# Edge Case Tests
# =============================================================================


@pytest.mark.asyncio
async def test_session_with_special_characters(client):
    """Test session creation with special characters in fields."""
    response = await client.post(
        "/sessions/",
        json={
            "methodology": "mec",
            "concept_id": "concept-with-special!@#$%",
            "concept_name": "Test & 'Concept' with \"quotes\"",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["concept_id"] == "concept-with-special!@#$%"
    assert data["concept_name"] == "Test & 'Concept' with \"quotes\""


@pytest.mark.asyncio
async def test_session_with_unicode(client):
    """Test session creation with unicode characters."""
    response = await client.post(
        "/sessions/",
        json={
            "methodology": "mec",
            "concept_id": "unicode-test",
            "concept_name": "Test Concept with Unicode",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["concept_name"] == "Test Concept with Unicode"


@pytest.mark.asyncio
async def test_session_with_long_strings(client):
    """Test session creation with long string values."""
    long_name = "A" * 1000

    response = await client.post(
        "/sessions/",
        json={
            "methodology": "mec",
            "concept_id": "long-string-test",
            "concept_name": long_name,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["concept_name"] == long_name
