# ui/api_client.py
"""API client for communicating with FastAPI backend.

Supports both synchronous and asynchronous usage patterns:

**Synchronous (for Streamlit, scripts, blocking contexts):**
    client = APIClient()
    session = client.create_session(...)  # sync call

**Asynchronous (for agents, async frameworks):**
    client = APIClient()
    session = await client.create_session_async(...)  # async call

See ADR-001: docs/adr/001-sync-async-dual-api.md
"""

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
    """HTTP client for the Interview System API.

    Provides dual sync/async interface:
    - Sync methods: For Streamlit UI and blocking contexts
    - Async methods: For agent orchestration and async frameworks

    Args:
        base_url: API base URL (default: http://localhost:8000)
        timeout: Request timeout in seconds (default: 30.0)
    """

    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 30.0):
        """Initialize API client."""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ============ SYNC METHODS (for Streamlit, blocking contexts) ============

    def create_session(
        self,
        concept_id: str,
        methodology: str = "means_end_chain",
        config: Optional[Dict[str, Any]] = None,
    ) -> SessionInfo:
        """Create a new interview session (synchronous).

        Args:
            concept_id: Concept configuration identifier
            methodology: Interview methodology (default: "means_end_chain")
            config: Optional configuration dict

        Returns:
            SessionInfo with session details
        """
        if config is None:
            config = {}

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/sessions",
                json={
                    "concept_id": concept_id,
                    "methodology": methodology,
                    "config": config,
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

    def submit_turn(
        self,
        session_id: str,
        user_input: str,
    ) -> Dict[str, Any]:
        """Submit a turn to the session (synchronous).

        Args:
            session_id: Session identifier
            user_input: User's response text

        Returns:
            Turn result with next question and metadata
        """
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/sessions/{session_id}/turns",
                json={"text": user_input},
            )
            response.raise_for_status()
            return response.json()

    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get current session status (synchronous).

        Note: The /status endpoint doesn't exist yet, so this returns
        basic session info from the /sessions/{id} endpoint.

        Args:
            session_id: Session identifier

        Returns:
            Session status with turn count, coverage, strategy
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.base_url}/sessions/{session_id}")
                response.raise_for_status()
                data = response.json()
                # Transform SessionResponse to status-like format
                return {
                    "turn_number": data.get("turn_count", 0),
                    "max_turns": 20,  # Default
                    "coverage": 0.0,   # Not available in SessionResponse
                    "target_coverage": 0.8,
                    "status": data.get("status", "unknown"),
                    "should_continue": data.get("status") == "active",
                    "strategy_selected": "unknown",  # Not available
                }
        except httpx.HTTPStatusError as e:
            # If endpoint doesn't exist, return default status
            return {
                "turn_number": 0,
                "max_turns": 20,
                "coverage": 0.0,
                "target_coverage": 0.8,
                "status": "active",
                "should_continue": True,
                "strategy_selected": "unknown",
            }

    def get_session_graph(self, session_id: str) -> Dict[str, Any]:
        """Get session knowledge graph (synchronous).

        Note: The /graph endpoint doesn't exist yet.

        Args:
            session_id: Session identifier

        Returns:
            Empty graph data
        """
        # Graph endpoint doesn't exist yet, return empty graph
        return {
            "nodes": [],
            "edges": [],
            "node_count": 0,
            "edge_count": 0,
        }

    def list_sessions(self) -> Dict[str, Any]:
        """List all sessions (synchronous).

        Returns:
            Dict with 'sessions' list and 'total' count
        """
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(f"{self.base_url}/sessions")
            response.raise_for_status()
            return response.json()

    def start_session(self, session_id: str) -> str:
        """Start an interview session and get the opening question (synchronous).

        Args:
            session_id: Session identifier

        Returns:
            The opening question text
        """
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/sessions/{session_id}/start")
            response.raise_for_status()
            data = response.json()
            return data.get("opening_question", "")

    def close(self):
        """Close the HTTP client (no-op, clients are auto-closed)."""
        pass

    # ============ ASYNC METHODS (for agents, async frameworks) ============

    async def create_session_async(
        self,
        concept_id: str,
        methodology: str = "means_end_chain",
        config: Optional[Dict[str, Any]] = None,
    ) -> SessionInfo:
        """Create a new interview session (asynchronous).

        Args:
            concept_id: Concept configuration identifier
            methodology: Interview methodology (default: "means_end_chain")
            config: Optional configuration dict

        Returns:
            SessionInfo with session details
        """
        if config is None:
            config = {}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/sessions",
                json={
                    "concept_id": concept_id,
                    "methodology": methodology,
                    "config": config,
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

    async def submit_turn_async(
        self,
        session_id: str,
        user_input: str,
    ) -> Dict[str, Any]:
        """Submit a turn to the session (asynchronous).

        Args:
            session_id: Session identifier
            user_input: User's response text

        Returns:
            Turn result with next question and metadata
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/sessions/{session_id}/turns",
                json={"text": user_input},
            )
            response.raise_for_status()
            return response.json()

    async def get_session_status_async(self, session_id: str) -> Dict[str, Any]:
        """Get current session status (asynchronous).

        Note: The /status endpoint doesn't exist yet, so this returns
        basic session info from the /sessions/{id} endpoint.

        Args:
            session_id: Session identifier

        Returns:
            Session status with turn count, coverage, strategy
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/sessions/{session_id}")
                response.raise_for_status()
                data = response.json()
                # Transform SessionResponse to status-like format
                return {
                    "turn_number": data.get("turn_count", 0),
                    "max_turns": 20,
                    "coverage": 0.0,
                    "target_coverage": 0.8,
                    "status": data.get("status", "unknown"),
                    "should_continue": data.get("status") == "active",
                    "strategy_selected": "unknown",
                }
        except httpx.HTTPStatusError:
            return {
                "turn_number": 0,
                "max_turns": 20,
                "coverage": 0.0,
                "target_coverage": 0.8,
                "status": "active",
                "should_continue": True,
                "strategy_selected": "unknown",
            }

    async def get_session_graph_async(self, session_id: str) -> Dict[str, Any]:
        """Get session knowledge graph (asynchronous).

        Note: The /graph endpoint doesn't exist yet.

        Args:
            session_id: Session identifier

        Returns:
            Empty graph data
        """
        # Graph endpoint doesn't exist yet
        return {
            "nodes": [],
            "edges": [],
            "node_count": 0,
            "edge_count": 0,
        }

    async def list_sessions_async(self) -> Dict[str, Any]:
        """List all sessions (asynchronous).

        Returns:
            Dict with 'sessions' list and 'total' count
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/sessions")
            response.raise_for_status()
            return response.json()

    async def start_session_async(self, session_id: str) -> str:
        """Start an interview session and get the opening question (asynchronous).

        Args:
            session_id: Session identifier

        Returns:
            The opening question text
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/sessions/{session_id}/start")
            response.raise_for_status()
            data = response.json()
            return data.get("opening_question", "")

    async def close_async(self):
        """Close the HTTP client (no-op, clients are auto-closed)."""
        pass
