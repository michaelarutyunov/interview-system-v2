"""Smoke tests verifying API client can parse all backend response fields.

These tests catch field name mismatches, missing fields, and type changes
between the frontend's api_client.py and the backend's response schemas.
They do NOT test Streamlit rendering — only data parsing.

If a backend refactor renames/removes a field the frontend depends on,
these tests will fail with a KeyError or AssertionError.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import httpx

from src.api.schemas import (
    EdgeSchema,
    GraphResponse,
    NodeSchema,
    SessionListResponse,
    SessionResponse,
    SessionStatusResponse,
    StartSessionResponse,
    TurnResponse,
)
from src.api.routes.concepts import ConceptListItem
from ui.api_client import APIClient, SessionInfo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _client() -> APIClient:
    return APIClient(base_url="http://localhost:8000", timeout=5.0)


def _session_response(**overrides) -> dict:
    defaults = dict(
        id="sess-001",
        methodology="means_end_chain",
        concept_id="test_concept",
        status="active",
        config={},
        turn_count=0,
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    defaults.update(overrides)
    return SessionResponse(**defaults).model_dump(mode="json")


# ---------------------------------------------------------------------------
# POST /sessions — create_session
# ---------------------------------------------------------------------------


class TestCreateSession:
    """Frontend reads: id, concept_id, status, opening_question?, created_at?"""

    def test_parses_all_required_fields(self):
        data = _session_response()
        with patch("httpx.Client") as mock_client_cls:
            mock_resp = (
                mock_client_cls.return_value.__enter__.return_value.post.return_value
            )
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = data

            result = _client().create_session(concept_id="test_concept")

        assert isinstance(result, SessionInfo)
        assert result.id == "sess-001"
        assert result.concept_id == "test_concept"
        assert result.status == "active"

    def test_parses_optional_created_at(self):
        ts = "2026-04-27T12:00:00+00:00"
        data = _session_response(created_at=ts)
        with patch("httpx.Client") as mock_client_cls:
            mock_resp = (
                mock_client_cls.return_value.__enter__.return_value.post.return_value
            )
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = data

            result = _client().create_session(concept_id="test_concept")

        assert result.created_at is not None

    def test_session_response_has_no_opening_question(self):
        data = _session_response()
        # SessionResponse schema doesn't include opening_question —
        # that comes from the separate /start endpoint
        assert "opening_question" not in data
        with patch("httpx.Client") as mock_client_cls:
            mock_resp = (
                mock_client_cls.return_value.__enter__.return_value.post.return_value
            )
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = data

            result = _client().create_session(concept_id="test_concept")

        assert result.opening_question is None


# ---------------------------------------------------------------------------
# POST /sessions/{id}/start — start_session
# ---------------------------------------------------------------------------


class TestStartSession:
    """Frontend reads: opening_question"""

    def test_parses_opening_question(self):
        data = StartSessionResponse(
            session_id="sess-001", opening_question="Tell me about..."
        ).model_dump(mode="json")
        with patch("httpx.Client") as mock_client_cls:
            mock_resp = (
                mock_client_cls.return_value.__enter__.return_value.post.return_value
            )
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = data

            result = _client().start_session("sess-001")

        assert result == "Tell me about..."

    def test_empty_opening_question(self):
        data = StartSessionResponse(
            session_id="sess-001", opening_question=""
        ).model_dump(mode="json")
        with patch("httpx.Client") as mock_client_cls:
            mock_resp = (
                mock_client_cls.return_value.__enter__.return_value.post.return_value
            )
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = data

            result = _client().start_session("sess-001")

        assert result == ""


# ---------------------------------------------------------------------------
# POST /sessions/{id}/turns — submit_turn
# ---------------------------------------------------------------------------


class TestSubmitTurn:
    """Frontend reads: next_question, should_continue, strategy_selected,
    latency_ms, focus_node_id"""

    def _turn_response(self, **overrides) -> dict:
        defaults = dict(
            turn_number=1,
            extracted={"concepts": [], "relationships": []},
            graph_state={"node_count": 0, "edge_count": 0},
            scoring={},
            strategy_selected="ascend",
            focus_node_id="node-001",
            next_question="Why is that important?",
            should_continue=True,
            latency_ms=1200,
            signals=None,
            strategy_alternatives=None,
        )
        defaults.update(overrides)
        return TurnResponse(**defaults).model_dump(mode="json")

    def test_parses_all_frontend_fields(self):
        data = self._turn_response()
        with patch("httpx.Client") as mock_client_cls:
            mock_resp = (
                mock_client_cls.return_value.__enter__.return_value.post.return_value
            )
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = data

            result = _client().submit_turn("sess-001", "because quality matters")

        assert result["next_question"] == "Why is that important?"
        assert result["should_continue"] is True
        assert result["strategy_selected"] == "ascend"
        assert result["latency_ms"] == 1200
        assert result["focus_node_id"] == "node-001"

    def test_parses_null_focus_node_id(self):
        data = self._turn_response(focus_node_id=None)
        with patch("httpx.Client") as mock_client_cls:
            mock_resp = (
                mock_client_cls.return_value.__enter__.return_value.post.return_value
            )
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = data

            result = _client().submit_turn("sess-001", "test")

        assert result["focus_node_id"] is None

    def test_parses_should_continue_false(self):
        data = self._turn_response(should_continue=False)
        with patch("httpx.Client") as mock_client_cls:
            mock_resp = (
                mock_client_cls.return_value.__enter__.return_value.post.return_value
            )
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = data

            result = _client().submit_turn("sess-001", "test")

        assert result["should_continue"] is False


# ---------------------------------------------------------------------------
# GET /sessions/{id}/status — get_session_status
# ---------------------------------------------------------------------------


class TestGetSessionStatus:
    """Frontend reads: turn_number, phase, canonical_node_count,
    max_turns, status, should_continue, strategy_selected"""

    def _status_response(self, **overrides) -> dict:
        defaults = dict(
            turn_number=5,
            max_turns=20,
            status="active",
            should_continue=True,
            strategy_selected="ascend",
            strategy_reasoning="Gap detected above",
            phase="mid",
            focus_tracing=[],
            canonical_node_count=3,
        )
        defaults.update(overrides)
        return SessionStatusResponse(**defaults).model_dump(mode="json")

    def test_parses_all_frontend_fields(self):
        data = self._status_response()
        with patch("httpx.Client") as mock_client_cls:
            mock_resp = (
                mock_client_cls.return_value.__enter__.return_value.get.return_value
            )
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = data

            result = _client().get_session_status("sess-001")

        assert result["turn_number"] == 5
        assert result["phase"] == "mid"
        assert result["canonical_node_count"] == 3
        assert result["max_turns"] == 20

    def test_graceful_fallback_on_http_error(self):
        with patch("httpx.Client") as mock_client_cls:
            mock_resp = (
                mock_client_cls.return_value.__enter__.return_value.get.return_value
            )
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404", request=MagicMock(), response=MagicMock()
            )

            result = _client().get_session_status("sess-001")

        assert result["turn_number"] == 0
        assert result["coverage"] == 0.0
        assert result["should_continue"] is True


# ---------------------------------------------------------------------------
# GET /sessions/{id}/graph — get_session_graph
# ---------------------------------------------------------------------------


class TestGetSessionGraph:
    """Frontend reads: nodes[].id, nodes[].label, nodes[].node_type,
    edges[].source_id, edges[].target_id"""

    def _graph_response(self) -> dict:
        return GraphResponse(
            nodes=[
                NodeSchema(
                    id="n1",
                    label="Quality",
                    node_type="attribute",
                    confidence=0.9,
                    properties={},
                ),
                NodeSchema(
                    id="n2",
                    label="Safety",
                    node_type="attribute",
                    confidence=0.8,
                    properties={},
                ),
            ],
            edges=[
                EdgeSchema(
                    id="e1",
                    source_id="n1",
                    target_id="n2",
                    edge_type="leads_to",
                    confidence=0.7,
                    properties={},
                ),
            ],
            node_count=2,
            edge_count=1,
        ).model_dump(mode="json")

    def test_parses_nodes_and_edges(self):
        data = self._graph_response()
        with patch("httpx.Client") as mock_client_cls:
            mock_resp = (
                mock_client_cls.return_value.__enter__.return_value.get.return_value
            )
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = data

            result = _client().get_session_graph("sess-001")

        nodes = result["nodes"]
        edges = result["edges"]
        assert len(nodes) == 2
        assert nodes[0]["id"] == "n1"
        assert nodes[0]["label"] == "Quality"
        assert nodes[0]["node_type"] == "attribute"
        assert len(edges) == 1
        assert edges[0]["source_id"] == "n1"
        assert edges[0]["target_id"] == "n2"

    def test_graceful_fallback_on_http_error(self):
        with patch("httpx.Client") as mock_client_cls:
            mock_resp = (
                mock_client_cls.return_value.__enter__.return_value.get.return_value
            )
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404", request=MagicMock(), response=MagicMock()
            )

            result = _client().get_session_graph("sess-001")

        assert result["nodes"] == []
        assert result["edges"] == []


# ---------------------------------------------------------------------------
# GET /sessions — list_sessions
# ---------------------------------------------------------------------------


class TestListSessions:
    """Frontend reads: sessions, total"""

    def test_parses_session_list(self):
        data = SessionListResponse(
            sessions=[_session_response()],
            total=1,
        ).model_dump(mode="json")
        with patch("httpx.Client") as mock_client_cls:
            mock_resp = (
                mock_client_cls.return_value.__enter__.return_value.get.return_value
            )
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = data

            result = _client().list_sessions()

        assert "sessions" in result
        assert result["total"] == 1
        assert len(result["sessions"]) == 1


# ---------------------------------------------------------------------------
# GET /concepts — list_concepts
# ---------------------------------------------------------------------------


class TestListConcepts:
    """Frontend reads: [].id, [].name, [].methodology, [].element_count"""

    def test_parses_concept_list(self):
        data = [
            ConceptListItem(
                id="glp1_food_mec",
                name="GLP-1 Food Choices",
                methodology="means_end_chain",
                element_count=12,
            ).model_dump(mode="json")
        ]
        with patch("httpx.Client") as mock_client_cls:
            mock_resp = (
                mock_client_cls.return_value.__enter__.return_value.get.return_value
            )
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = data

            result = _client().list_concepts()

        assert len(result) == 1
        assert result[0]["id"] == "glp1_food_mec"
        assert result[0]["name"] == "GLP-1 Food Choices"
        assert result[0]["methodology"] == "means_end_chain"
        assert result[0]["element_count"] == 12


# ---------------------------------------------------------------------------
# Schema field presence — catches renames/removals in backend schemas
# ---------------------------------------------------------------------------


class TestSchemaFieldPresence:
    """Verify every field the frontend accesses exists in the backend schema.

    These tests will fail if a backend refactor renames or removes a field,
    catching contract breaks before they reach production.
    """

    def test_session_response_has_frontend_fields(self):
        fields = set(SessionResponse.model_fields.keys())
        required = {"id", "concept_id", "status", "created_at"}
        assert required.issubset(fields), f"Missing: {required - fields}"

    def test_turn_response_has_frontend_fields(self):
        fields = set(TurnResponse.model_fields.keys())
        required = {
            "next_question",
            "should_continue",
            "strategy_selected",
            "latency_ms",
            "focus_node_id",
        }
        assert required.issubset(fields), f"Missing: {required - fields}"

    def test_status_response_has_frontend_fields(self):
        fields = set(SessionStatusResponse.model_fields.keys())
        required = {"turn_number", "phase", "canonical_node_count"}
        assert required.issubset(fields), f"Missing: {required - fields}"

    def test_graph_response_has_frontend_fields(self):
        node_fields = set(NodeSchema.model_fields.keys())
        edge_fields = set(EdgeSchema.model_fields.keys())
        graph_fields = set(GraphResponse.model_fields.keys())

        assert {"id", "label", "node_type"}.issubset(node_fields)
        assert {"source_id", "target_id"}.issubset(edge_fields)
        assert {"nodes", "edges"}.issubset(graph_fields)

    def test_start_response_has_frontend_fields(self):
        fields = set(StartSessionResponse.model_fields.keys())
        assert "opening_question" in fields

    def test_concept_list_item_has_frontend_fields(self):
        fields = set(ConceptListItem.model_fields.keys())
        required = {"id", "name", "methodology", "element_count"}
        assert required.issubset(fields), f"Missing: {required - fields}"
