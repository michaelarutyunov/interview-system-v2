# ui/api_client.py
"""API client for communicating with FastAPI backend."""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import httpx


@dataclass
class SessionInfo:
    """Information about an interview session."""
    id: str
    concept_id: str
    status: str
    opening_question: Optional[str] = None
    created_at: Optional[str] = None


class APIClient:
    """Client for making HTTP requests to the FastAPI backend."""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 30.0):
        """Initialize API client."""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def create_session(
        self,
        concept_id: str,
        max_turns: int = 20,
        target_coverage: float = 0.8,
    ) -> SessionInfo:
        """Create a new interview session."""
        client = self._get_client()
        response = await client.post(
            f"{self.base_url}/sessions",
            json={
                "concept_id": concept_id,
                "max_turns": max_turns,
                "target_coverage": target_coverage,
            },
        )
        response.raise_for_status()
        data = response.json()

        return SessionInfo(
            id=data["id"],
            concept_id=data["concept_id"],
            status=data["status"],
            opening_question=data.get("opening_question"),
            created_at=data.get("created_at"),
        )

    async def submit_turn(
        self,
        session_id: str,
        user_input: str,
    ) -> Dict[str, Any]:
        """Submit a turn to the session."""
        client = self._get_client()
        response = await client.post(
            f"{self.base_url}/sessions/{session_id}/turns",
            json={"user_input": user_input},
        )
        response.raise_for_status()
        return response.json()

    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get current session status."""
        client = self._get_client()
        response = await client.get(f"{self.base_url}/sessions/{session_id}/status")
        response.raise_for_status()
        return response.json()

    async def get_session_graph(self, session_id: str) -> Dict[str, Any]:
        """Get session knowledge graph."""
        client = self._get_client()
        response = await client.get(f"{self.base_url}/sessions/{session_id}/graph")
        response.raise_for_status()
        return response.json()

    async def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions."""
        client = self._get_client()
        response = await client.get(f"{self.base_url}/sessions")
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
