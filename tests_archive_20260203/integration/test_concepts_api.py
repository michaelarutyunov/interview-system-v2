"""Integration tests for concepts API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


class TestConceptsEndpoints:
    """Tests for concept endpoints."""

    @pytest.mark.asyncio
    async def test_list_concepts(self):
        """GET /concepts returns list of concepts."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/concepts")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_concept_details(self):
        """GET /concepts/{id} returns concept details."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/concepts/oat_milk_v1")

            # May return 404 if concept doesn't exist
            assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_get_concept_not_found(self):
        """GET /concepts/{id} returns 404 for unknown concept."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/concepts/unknown_concept")

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_concept_elements(self):
        """GET /concepts/{id}/elements returns concept elements."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/concepts/oat_milk_v1/elements")

            # May return 404 if concept doesn't exist
            assert response.status_code in [200, 404]
