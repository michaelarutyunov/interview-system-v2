"""Integration tests for API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
import tempfile
from pathlib import Path


@pytest.fixture
def test_db_path():
    """Create a temporary database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test.db"


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


@pytest.mark.asyncio
async def test_root_endpoint(app_with_test_db):
    """Root endpoint returns basic info."""
    transport = ASGITransport(app=app_with_test_db)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Interview System v2"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health_endpoint(app_with_test_db):
    """Health endpoint returns system status."""
    # Initialize database first
    from src.persistence.database import init_database
    from src.core.config import settings
    await init_database(settings.database_path)

    transport = ASGITransport(app=app_with_test_db)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "components" in data
    assert "database" in data["components"]


@pytest.mark.asyncio
async def test_liveness_endpoint(app_with_test_db):
    """Liveness probe returns alive status."""
    transport = ASGITransport(app=app_with_test_db)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_readiness_endpoint(app_with_test_db):
    """Readiness probe checks database."""
    from src.persistence.database import init_database
    from src.core.config import settings
    await init_database(settings.database_path)

    transport = ASGITransport(app=app_with_test_db)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
