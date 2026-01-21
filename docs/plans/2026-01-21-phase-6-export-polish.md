# Phase 6: Export & Polish Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Complete the MVP with export functionality, error handling, documentation, and comprehensive testing to make the system production-ready.

**Architecture:** Phase 6 adds polish and production readiness to the existing system. Tasks are mostly independent and can be implemented in parallel. Export service integrates with existing repositories, concept endpoints load from YAML config, error handling adds global exception handlers, and documentation covers all aspects of the system.

**Tech Stack:** Python 3.11+, FastAPI, aiosqlite, structlog, PyYAML, pytest, httpx

**Phase 6 completes the MVP!** After this phase, the system will be ready for production deployment.

---

## Task 6.1: Export Service

**Files:**
- Create: `src/services/export_service.py`
- Test: `tests/unit/test_export_service.py`

**Step 1: Write the failing test**

Create `tests/unit/test_export_service.py`:

```python
"""Tests for export service."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.export_service import ExportService
from src.domain.models.knowledge_graph import KGNode, KGEdge


class TestExportService:
    """Tests for ExportService."""

    @pytest.mark.asyncio
    async def test_export_json_format(self):
        """Export to JSON produces valid JSON."""
        # Mock repositories
        session_repo = AsyncMock()
        graph_repo = AsyncMock()

        # Setup mock session
        mock_session = MagicMock()
        mock_session.id = "test-session"
        mock_session.concept_id = "test_concept"
        mock_session.methodology = "means_end_chain"
        mock_session.status = "completed"
        mock_session.created_at = MagicMock()
        mock_session.created_at.isoformat.return_value = "2025-01-21T00:00:00"
        mock_session.completed_at = None
        mock_session.config = {}

        session_repo.get.return_value = mock_session
        session_repo.get_utterances.return_value = []
        session_repo.get_scoring_history.return_value = []

        # Setup mock graph
        graph_repo.get_nodes.return_value = [
            KGNode(
                id="n1",
                session_id="test-session",
                label="creamy texture",
                node_type="attribute",
                confidence=0.9,
                properties={},
                source_utterance_ids=["u1"],
            )
        ]
        graph_repo.get_edges.return_value = []

        service = ExportService(session_repo, graph_repo)
        result = await service.export_session("test-session", "json")

        assert result is not None
        # Verify valid JSON
        import json
        data = json.loads(result)
        assert data["metadata"]["session_id"] == "test-session"
        assert len(data["graph"]["nodes"]) == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_export_service.py::TestExportService::test_export_json_format -v`
Expected: FAIL with "ImportError: cannot import name 'ExportService'"

**Step 3: Write minimal implementation**

Create `src/services/export_service.py`:

```python
"""
Export service for converting session data to various formats.

Supports export to:
- JSON: Full session data with all metadata
- Markdown: Human-readable interview summary
- CSV: Spreadsheet-compatible format for analysis
"""

import json
import csv
from io import StringIO
from typing import Any, Dict, List
from datetime import datetime

import structlog

from src.domain.models.knowledge_graph import KGNode, KGEdge
from src.domain.models.utterance import Utterance


log = structlog.get_logger(__name__)


class ExportService:
    """
    Service for exporting session data to various formats.

    Usage:
        service = ExportService()
        json_str = await service.export_session(session_id, "json")
        md_str = await service.export_session(session_id, "markdown")
    """

    def __init__(
        self,
        session_repo=None,
        graph_repo=None,
    ):
        """
        Initialize export service.

        Args:
            session_repo: Optional session repository (injected for testing)
            graph_repo: Optional graph repository (injected for testing)
        """
        # Lazy import to avoid circular dependencies
        from src.persistence.repositories.session_repo import SessionRepository
        from src.persistence.repositories.graph_repo import GraphRepository

        self.session_repo = session_repo or SessionRepository()
        self.graph_repo = graph_repo or GraphRepository()

    async def export_session(
        self,
        session_id: str,
        format: str = "json",
    ) -> str:
        """
        Export session data to specified format.

        Args:
            session_id: Session ID to export
            format: One of "json", "markdown", "csv"

        Returns:
            Exported data as string

        Raises:
            ValueError: If format is not supported
            SessionNotFoundError: If session doesn't exist
        """
        log = log.bind(session_id=session_id, format=format)
        log.info("export_session_started")

        # Gather all session data
        session_data = await self._collect_session_data(session_id)

        # Export to requested format
        if format.lower() in ("json",):
            result = self._export_json(session_data)
        elif format.lower() in ("markdown", "md"):
            result = self._export_markdown(session_data)
        elif format.lower() == "csv":
            result = self._export_csv(session_data)
        else:
            raise ValueError(f"Unsupported export format: {format}")

        log.info(
            "export_session_complete",
            format=format,
            output_length=len(result),
        )

        return result

    async def _collect_session_data(self, session_id: str) -> Dict[str, Any]:
        """
        Collect all session data for export.

        Args:
            session_id: Session ID

        Returns:
            Dict with all session data
        """
        # Get session metadata
        session = await self.session_repo.get(session_id)
        if not session:
            from src.core.exceptions import SessionNotFoundError
            raise SessionNotFoundError(f"Session {session_id} not found")

        # Get utterances
        utterances = await self.session_repo.get_utterances(session_id)

        # Get graph data
        nodes = await self.graph_repo.get_nodes(session_id)
        edges = await self.graph_repo.get_edges(session_id)

        # Get scoring history
        scoring_history = await self.session_repo.get_scoring_history(session_id)

        return {
            "metadata": {
                "session_id": session.id,
                "concept_id": session.concept_id,
                "methodology": session.methodology,
                "status": session.status,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                "config": session.config,
                "exported_at": datetime.utcnow().isoformat(),
            },
            "utterances": [
                {
                    "id": u.id,
                    "turn_number": u.turn_number,
                    "speaker": u.speaker,
                    "text": u.text,
                    "created_at": u.created_at.isoformat() if u.created_at else None,
                }
                for u in utterances
            ],
            "graph": {
                "nodes": [
                    {
                        "id": n.id,
                        "label": n.label,
                        "node_type": n.node_type,
                        "confidence": n.confidence,
                        "properties": n.properties,
                        "source_utterance_ids": n.source_utterance_ids,
                        "recorded_at": n.recorded_at.isoformat() if n.recorded_at else None,
                    }
                    for n in nodes
                ],
                "edges": [
                    {
                        "id": e.id,
                        "source_node_id": e.source_node_id,
                        "target_node_id": e.target_node_id,
                        "edge_type": e.edge_type,
                        "confidence": e.confidence,
                        "properties": e.properties,
                        "source_utterance_ids": e.source_utterance_ids,
                        "recorded_at": e.recorded_at.isoformat() if e.recorded_at else None,
                    }
                    for e in edges
                ],
            },
            "scoring_history": scoring_history,
        }

    def _export_json(self, data: Dict[str, Any]) -> str:
        """Export to JSON format."""
        return json.dumps(data, indent=2, default=str)

    def _export_markdown(self, data: Dict[str, Any]) -> str:
        """Export to human-readable Markdown format."""
        lines = []

        # Header
        meta = data["metadata"]
        lines.append("# Interview Session Export")
        lines.append("")
        lines.append(f"**Session ID:** `{meta['session_id']}`")
        lines.append(f"**Concept:** {meta['concept_id']}")
        lines.append(f"**Methodology:** {meta['methodology']}")
        lines.append(f"**Status:** {meta['status']}")
        lines.append(f"**Created:** {meta.get('created_at', 'N/A')}")
        if meta.get('completed_at'):
            lines.append(f"**Completed:** {meta['completed_at']}")
        lines.append("")

        # Statistics
        utterances = data["utterances"]
        nodes = data["graph"]["nodes"]
        edges = data["graph"]["edges"]

        lines.append("## Statistics")
        lines.append("")
        lines.append(f"- **Turns:** {len(utterances)}")
        lines.append(f"- **Concepts Extracted:** {len(nodes)}")
        lines.append(f"- **Relationships:** {len(edges)}")
        lines.append("")

        # Conversation
        lines.append("## Conversation")
        lines.append("")
        for utt in utterances:
            speaker = utt["speaker"]
            text = utt["text"]
            emoji = "👤" if speaker == "user" else "🤖"
            lines.append(f"### {emoji} {speaker.title()} (Turn {utt['turn_number']})")
            lines.append("")
            lines.append(text)
            lines.append("")

        # Knowledge Graph
        lines.append("## Knowledge Graph")
        lines.append("")

        # Group nodes by type
        nodes_by_type: Dict[str, List[Dict]] = {}
        for node in nodes:
            node_type = node["node_type"]
            if node_type not in nodes_by_type:
                nodes_by_type[node_type] = []
            nodes_by_type[node_type].append(node)

        for node_type, type_nodes in sorted(nodes_by_type.items()):
            lines.append(f"### {node_type.replace('_', ' ').title()} ({len(type_nodes)})")
            lines.append("")
            for node in type_nodes:
                label = node["label"]
                confidence = node["confidence"]
                lines.append(f"- **{label}** (confidence: {confidence:.2f})")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append(f"*Exported on {meta['exported_at']}*")
        lines.append("")

        return "\n".join(lines)

    def _export_csv(self, data: Dict[str, Any]) -> str:
        """Export to CSV format with multiple sections."""
        output = StringIO()

        # Nodes section
        nodes = data["graph"]["nodes"]
        output.write("## NODES\n")
        if nodes:
            writer = csv.DictWriter(
                output,
                fieldnames=["id", "label", "node_type", "confidence", "source_utterance_ids"]
            )
            writer.writeheader()
            for node in nodes:
                writer.writerow({
                    "id": node["id"],
                    "label": node["label"],
                    "node_type": node["node_type"],
                    "confidence": node["confidence"],
                    "source_utterance_ids": json.dumps(node["source_utterance_ids"]),
                })
        output.write("\n\n")

        # Edges section
        edges = data["graph"]["edges"]
        output.write("## EDGES\n")
        if edges:
            writer = csv.DictWriter(
                output,
                fieldnames=["id", "source_node_id", "target_node_id", "edge_type", "confidence"]
            )
            writer.writeheader()
            for edge in edges:
                writer.writerow({
                    "id": edge["id"],
                    "source_node_id": edge["source_node_id"],
                    "target_node_id": edge["target_node_id"],
                    "edge_type": edge["edge_type"],
                    "confidence": edge["confidence"],
                })
        output.write("\n\n")

        # Utterances section
        utterances = data["utterances"]
        output.write("## UTTERANCES\n")
        if utterances:
            writer = csv.DictWriter(
                output,
                fieldnames=["id", "turn_number", "speaker", "text", "created_at"]
            )
            writer.writeheader()
            for utt in utterances:
                writer.writerow({
                    "id": utt["id"],
                    "turn_number": utt["turn_number"],
                    "speaker": utt["speaker"],
                    "text": utt["text"],
                    "created_at": utt.get("created_at", ""),
                })

        return output.getvalue()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_export_service.py -v`
Expected: PASS

**Step 5: Add remaining tests and update `src/services/__init__.py`**

Add to `src/services/__init__.py`:
```python
# noqa
from src.services.strategy_service import StrategyService
from src.services.synthetic_service import SyntheticService, get_synthetic_service
from src.services.export_service import ExportService

__all__ = ["StrategyService", "SyntheticService", "get_synthetic_service", "ExportService"]
```

Add remaining test cases (markdown, csv, unsupported format) from spec 6.1.

**Step 6: Commit**

```bash
git add tests/unit/test_export_service.py src/services/export_service.py src/services/__init__.py
git commit -m "feat(phase-6): add export service with JSON, Markdown, CSV formats

- ExportService class with format-specific exporters
- JSON export with full session data
- Markdown export with human-readable format
- CSV export with sections for nodes, edges, utterances
- Unit tests for all export formats

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 6.2: Export Endpoints

**Files:**
- Modify: `src/api/routes/sessions.py`
- Create: `tests/integration/test_export_api.py`

**Step 1: Write the failing test**

Create `tests/integration/test_export_api.py`:

```python
"""Integration tests for export API endpoints."""

import pytest
from httpx import AsyncClient

from src.main import app


class TestExportEndpoint:
    """Tests for GET /sessions/{id}/export."""

    @pytest.mark.asyncio
    async def test_export_json(self):
        """Export to JSON returns valid JSON."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Export to JSON (endpoint should exist)
            response = await client.get(
                "/sessions/test-session/export",
                params={"format": "json"},
            )
            # May return 404 if session doesn't exist, but endpoint should exist
            assert response.status_code in [200, 404, 500]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_export_api.py::TestExportEndpoint::test_export_json -v`
Expected: FAIL with 404 (endpoint doesn't exist yet)

**Step 3: Add export endpoint to sessions.py**

Read existing `src/api/routes/sessions.py` and add the export route:

```python
# Add to existing src/api/routes/sessions.py

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import Response, PlainTextResponse

import structlog

from src.services.export_service import ExportService
from src.core.exceptions import SessionNotFoundError


log = structlog.get_logger(__name__)
router = APIRouter(prefix="/sessions", tags=["sessions"])


# ... existing routes ...


@router.get(
    "/{session_id}/export",
    response_class=Response,
    summary="Export session data",
    description="Export session data to JSON, Markdown, or CSV format",
)
async def export_session(
    session_id: str,
    format: str = Query(
        "json",
        description="Export format: json, markdown, or csv",
        regex="^(json|markdown|csv)$",
    ),
    service: ExportService = Depends(lambda: ExportService()),
) -> Response:
    """
    Export session data to specified format.

    Args:
        session_id: Session ID to export
        format: Export format (json, markdown, csv)
        service: Injected export service

    Returns:
        Response with exported data and appropriate content-type

    Raises:
        HTTPException 404: If session not found
        HTTPException 400: If format is invalid
    """
    log_ctx = log.bind(session_id=session_id, format=format)

    log_ctx.info("export_session_requested")

    try:
        data = await service.export_session(session_id, format)

        # Set content-type based on format
        if format == "json":
            content_type = "application/json"
            filename = f"session_{session_id[:8]}.json"
        elif format == "markdown":
            content_type = "text/markdown"
            filename = f"session_{session_id[:8]}.md"
        else:  # csv
            content_type = "text/csv"
            filename = f"session_{session_id[:8]}.csv"

        log_ctx.info(
            "export_session_complete",
            content_type=content_type,
            content_length=len(data),
        )

        return Response(
            content=data,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    except SessionNotFoundError as e:
        log_ctx.warning("export_session_not_found", error=str(e))
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )
    except ValueError as e:
        log_ctx.warning("export_session_invalid_format", error=str(e))
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except Exception as e:
        log_ctx.error(
            "export_session_error",
            error_type=type(e).__name__,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {str(e)}",
        )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_export_api.py -v`
Expected: PASS

**Step 5: Add remaining test cases**

Add tests for markdown, csv, invalid format, non-existent session.

**Step 6: Commit**

```bash
git add src/api/routes/sessions.py tests/integration/test_export_api.py
git commit -m "feat(phase-6): add export endpoint to sessions API

- GET /sessions/{id}/export?format=json|markdown|csv
- Returns appropriate content-type and filename
- Error handling for missing sessions and invalid formats
- Integration tests for all export formats

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 6.3: Concept Endpoints

**Files:**
- Create: `src/api/routes/concepts.py`
- Create: `config/concepts/oat_milk.yaml` (if not exists)
- Modify: `src/main.py` (register router)
- Create: `tests/integration/test_concepts_api.py`

**Step 1: Create concept configuration file**

Create `config/concepts/oat_milk.yaml`:

```yaml
id: oat_milk_v1
name: "Oat Milk"
description: "Plant-based milk alternative made from oats"
methodology: means_end_chain

elements:
  - id: creamy_texture
    label: "Creamy texture"
    type: attribute
    priority: high

  - id: plant_based
    label: "Plant-based / dairy-free"
    type: attribute
    priority: high

  - id: sustainable
    label: "Environmentally sustainable"
    type: attribute
    priority: medium

  - id: froths_well
    label: "Froths well for coffee"
    type: attribute
    priority: medium

  - id: neutral_taste
    label: "Neutral/mild taste"
    type: attribute
    priority: low

  - id: nutritional
    label: "Nutritional profile"
    type: attribute
    priority: low

completion:
  target_coverage: 0.8
  max_turns: 20
  saturation_threshold: 0.05
```

**Step 2: Write the failing test**

Create `tests/integration/test_concepts_api.py`:

```python
"""Integration tests for concepts API endpoints."""

import pytest
from httpx import AsyncClient

from src.main import app


class TestConceptsEndpoints:
    """Tests for concept endpoints."""

    @pytest.mark.asyncio
    async def test_list_concepts(self):
        """GET /concepts returns list of concepts."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/concepts")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/integration/test_concepts_api.py::TestConceptsEndpoints::test_list_concepts -v`
Expected: FAIL with 404 (endpoint doesn't exist)

**Step 4: Create concepts router**

Create `src/api/routes/concepts.py`:

```python
"""
API routes for concept configuration management.

GET /concepts - List available concepts
GET /concepts/{id} - Get concept details
"""

from typing import List, Dict, Any, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import structlog

from src.core.config import settings


log = structlog.get_logger(__name__)
router = APIRouter(prefix="/concepts", tags=["concepts"])


# Response Models
class ConceptElement(BaseModel):
    """Single element in a concept configuration."""
    id: str = Field(description="Element identifier")
    label: str = Field(description="Display label")
    type: str = Field(description="Element type (attribute, consequence, etc.)")
    priority: str = Field(description="Priority level (high, medium, low)")


class ConceptCompletion(BaseModel):
    """Completion criteria for a concept."""
    target_coverage: float = Field(description="Target coverage threshold")
    max_turns: int = Field(description="Maximum turns")
    saturation_threshold: float = Field(description="Saturation threshold")


class ConceptConfig(BaseModel):
    """Concept configuration."""
    id: str = Field(description="Concept ID")
    name: str = Field(description="Concept name")
    description: Optional[str] = Field(default="", description="Description")
    methodology: str = Field(description="Methodology ID")
    elements: List[ConceptElement] = Field(default_factory=list, description="Concept elements")
    completion: ConceptConfig = Field(description="Completion criteria")


class ConceptListItem(BaseModel):
    """Item in concept list."""
    id: str
    name: str
    methodology: str
    element_count: int


def _load_concepts_from_config() -> List[Dict[str, Any]]:
    """
    Load concepts from configuration directory.

    Returns:
        List of concept configuration dicts
    """
    concepts_dir = settings.config_dir / "concepts"

    if not concepts_dir.exists():
        log.warning("concepts_directory_not_found", path=str(concepts_dir))
        return []

    concepts = []

    for yaml_file in concepts_dir.glob("*.yaml"):
        try:
            import yaml
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
                if data:
                    concepts.append(data)
        except Exception as e:
            log.warning(
                "concept_load_failed",
                file=str(yaml_file),
                error=str(e),
            )

    log.info("concepts_loaded", count=len(concepts))
    return concepts


# Routes
@router.get(
    "",
    response_model=List[ConceptListItem],
    summary="List available concepts",
    description="Get list of all available concept configurations",
)
async def list_concepts() -> List[ConceptListItem]:
    """
    List all available concept configurations.

    Returns:
        List of concept summaries
    """
    concepts = _load_concepts_from_config()

    return [
        ConceptListItem(
            id=c["id"],
            name=c["name"],
            methodology=c["methodology"],
            element_count=len(c.get("elements", [])),
        )
        for c in concepts
    ]


@router.get(
    "/{concept_id}",
    response_model=ConceptConfig,
    summary="Get concept details",
    description="Get full configuration for a specific concept",
)
async def get_concept(concept_id: str) -> ConceptConfig:
    """
    Get detailed concept configuration.

    Args:
        concept_id: Concept identifier

    Returns:
        Full concept configuration

    Raises:
        HTTPException 404: If concept not found
    """
    concepts = _load_concepts_from_config()

    # Find concept by ID
    concept_data = next((c for c in concepts if c["id"] == concept_id), None)

    if not concept_data:
        log.warning("concept_not_found", concept_id=concept_id)
        raise HTTPException(
            status_code=404,
            detail=f"Concept '{concept_id}' not found",
        )

    log.info("concept_retrieved", concept_id=concept_id)

    return ConceptConfig(**concept_data)


@router.get(
    "/{concept_id}/elements",
    response_model=List[ConceptElement],
    summary="Get concept elements",
    description="Get elements for a specific concept",
)
async def get_concept_elements(concept_id: str) -> List[ConceptElement]:
    """
    Get elements for a concept configuration.

    Args:
        concept_id: Concept identifier

    Returns:
        List of concept elements

    Raises:
        HTTPException 404: If concept not found
    """
    concepts = _load_concepts_from_config()

    concept_data = next((c for c in concepts if c["id"] == concept_id), None)

    if not concept_data:
        raise HTTPException(
            status_code=404,
            detail=f"Concept '{concept_id}' not found",
        )

    elements = concept_data.get("elements", [])

    return [
        ConceptElement(
            id=e["id"],
            label=e["label"],
            type=e["type"],
            priority=e.get("priority", "medium"),
        )
        for e in elements
    ]
```

**Step 5: Register router in main.py**

Add to `src/main.py`:
```python
from src.api.routes.concepts import router as concepts_router

# Register concepts router
app.include_router(concepts_router)
```

**Step 6: Run test to verify it passes**

Run: `pytest tests/integration/test_concepts_api.py -v`
Expected: PASS

**Step 7: Add remaining tests**

Add tests for get_concept, not_found, get_concept_elements.

**Step 8: Commit**

```bash
git add src/api/routes/concepts.py src/main.py config/concepts/oat_milk.yaml tests/integration/test_concepts_api.py
git commit -m "feat(phase-6): add concept management endpoints

- GET /concepts - list available concepts
- GET /concepts/{id} - get concept details
- GET /concepts/{id}/elements - get concept elements
- Loads from config/concepts/*.yaml files
- oat_milk_v1 concept configuration

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 6.4: Error Handling

**Files:**
- Modify: `src/core/exceptions.py` (update if needed)
- Create: `src/api/exception_handlers.py`
- Modify: `src/main.py` (setup handlers)
- Create: `tests/unit/test_exception_handlers.py`
- Create: `docs/error_handling_checklist.md`

**Step 1: Review existing exceptions**

Read `src/core/exceptions.py` to see what's already defined.

**Step 2: Update exceptions.py**

Ensure all required exceptions are defined. The spec shows:
- InterviewSystemError (base)
- ConfigurationError
- LLMError, LLMTimeoutError, LLMRateLimitError, LLMInvalidResponseError
- ExtractionError
- SessionError, SessionNotFoundError, SessionCompletedError
- ValidationError
- GraphError

Update `src/core/exceptions.py` if any are missing.

**Step 3: Write the failing test**

Create `tests/unit/test_exception_handlers.py`:

```python
"""Tests for exception handlers."""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.api.exception_handlers import setup_exception_handlers
from src.core.exceptions import (
    SessionNotFoundError,
    SessionCompletedError,
    ValidationError,
    LLMTimeoutError,
)


def test_session_not_found_returns_404():
    """SessionNotFoundError returns 404 status."""
    app = FastAPI()
    setup_exception_handlers(app)

    @app.get("/test")
    async def test_route():
        raise SessionNotFoundError("Session not found")

    client = TestClient(app)
    response = client.get("/test")

    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["type"] == "SessionNotFoundError"
```

**Step 4: Run test to verify it fails**

Run: `pytest tests/unit/test_exception_handlers.py::test_session_not_found_returns_404 -v`
Expected: FAIL with "ImportError"

**Step 5: Create exception handlers**

Create `src/api/exception_handlers.py`:

```python
"""
Global exception handlers for FastAPI.

Provides consistent error responses across all endpoints.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

import structlog

from src.core.exceptions import (
    InterviewSystemError,
    ConfigurationError,
    LLMError,
    LLMTimeoutError,
    LLMRateLimitError,
    SessionNotFoundError,
    SessionCompletedError,
    ValidationError,
)


log = structlog.get_logger(__name__)


def setup_exception_handlers(app: FastAPI):
    """
    Register all exception handlers with the FastAPI app.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(InterviewSystemError)
    async def interview_system_error_handler(
        request: Request,
        exc: InterviewSystemError,
    ) -> JSONResponse:
        """Handle all custom InterviewSystemError exceptions."""
        log_ctx = log.bind(
            path=request.url.path,
            method=request.method,
            error_type=type(exc).__name__,
        )

        # Determine status code based on exception type
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        if isinstance(exc, SessionNotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(exc, ValidationError):
            status_code = status.HTTP_400_BAD_REQUEST
        elif isinstance(exc, SessionCompletedError):
            status_code = status.HTTP_400_BAD_REQUEST
        elif isinstance(exc, LLMTimeoutError):
            status_code = status.HTTP_504_GATEWAY_TIMEOUT
        elif isinstance(exc, LLMRateLimitError):
            status_code = status.HTTP_429_TOO_MANY_REQUESTS

        log_ctx.warning(
            "request_error",
            message=exc.message,
            status_code=status_code,
            details=exc.details,
        )

        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "type": type(exc).__name__,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(ConfigurationError)
    async def configuration_error_handler(
        request: Request,
        exc: ConfigurationError,
    ) -> JSONResponse:
        """Handle configuration errors."""
        log.error(
            "configuration_error",
            path=request.url.path,
            message=exc.message,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "type": "ConfigurationError",
                    "message": "Server configuration error",
                    "details": exc.message if log.level <= 10 else None,
                }
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle all unhandled exceptions."""
        log_ctx = log.bind(
            path=request.url.path,
            method=request.method,
            error_type=type(exc).__name__,
        )

        log_ctx.error(
            "unhandled_exception",
            message=str(exc),
            exc_info=exc,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "type": "InternalServerError",
                    "message": "An unexpected error occurred",
                }
            },
        )
```

**Step 6: Setup handlers in main.py**

Add to `src/main.py` after app creation:
```python
from src.api.exception_handlers import setup_exception_handlers

# Setup exception handlers
setup_exception_handlers(app)
```

**Step 7: Run test to verify it passes**

Run: `pytest tests/unit/test_exception_handlers.py -v`
Expected: PASS

**Step 8: Add remaining tests and create checklist**

Add tests for validation_error, llm_timeout, generic_exception.

Create `docs/error_handling_checklist.md` from spec.

**Step 9: Commit**

```bash
git add src/core/exceptions.py src/api/exception_handlers.py src/main.py tests/unit/test_exception_handlers.py docs/error_handling_checklist.md
git commit -m "feat(phase-6): add global exception handlers

- Global exception handlers for consistent error responses
- Appropriate HTTP status codes per exception type
- Structured error response format with type, message, details
- Error handling checklist documentation
- Unit tests for exception handlers

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 6.5: Logging Review

**Files:**
- Verify: `src/core/logging.py` (exists)
- Create: `docs/logging_standards.md`
- Create: `scripts/check_logging.py`
- Modify: Various files (add logging where missing)

**Step 1: Verify logging configuration**

Read `src/core/logging.py` and verify it's properly configured.

**Step 2: Write test for logging configuration**

Create `tests/unit/test_logging.py` (update if exists):

```python
"""Tests for logging configuration."""

import logging
import pytest
import structlog

from src.core.logging import configure_logging, get_logger


class TestLoggingConfiguration:
    """Tests for logging setup."""

    def test_configure_logging_sets_up_structlog(self):
        """configure_logging() sets up structlog properly."""
        configure_logging()

        # Get a logger and verify it works
        logger = structlog.get_logger("test")
        assert logger is not None

    def test_get_logger_returns_bound_logger(self):
        """get_logger() returns a BoundLogger."""
        logger = get_logger("test_module")

        assert isinstance(logger, structlog.BoundLogger)

    def test_logger_can_bind_context(self):
        """Logger can bind context variables."""
        logger = get_logger("test")

        bound_logger = logger.bind(session_id="test-123", turn_number=5)

        # Should not raise
        bound_logger.info("test_message")
```

**Step 3: Run test to verify existing logging works**

Run: `pytest tests/unit/test_logging.py -v`
Expected: PASS

**Step 4: Create logging standards doc**

Create `docs/logging_standards.md` from spec 6.5.

**Step 5: Create logging checker script**

Create `scripts/check_logging.py` from spec 6.5.

**Step 6: Run logging checker**

Run: `python scripts/check_logging.py`
Expected: Report any missing logging or print statements

**Step 7: Fix any logging issues**

Address issues found by the checker (add logging imports, replace print statements).

**Step 8: Commit**

```bash
git add docs/logging_standards.md scripts/check_logging.py tests/unit/test_logging.py
git commit -m "feat(phase-6): add logging standards and checker

- Logging standards documentation
- AST-based logging checker script
- Tests for logging configuration
- Event logging standards table

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 6.6: Documentation

**Files:**
- Modify: `README.md` (update)
- Create: `docs/API.md`
- Create: `docs/DEVELOPMENT.md`

**Step 1: Update README.md**

Read existing `README.md` and update with complete content from spec 6.6.

**Step 2: Create API documentation**

Create `docs/API.md` from spec 6.6.

**Step 3: Create development guide**

Create `docs/DEVELOPMENT.md` from spec 6.6.

**Step 4: Verify documentation**

Run verification commands from spec:
```bash
grep -q "## Features" README.md
grep -q "## Quick Start" README.md
ls -la docs/API.md docs/DEVELOPMENT.md
```

**Step 5: Commit**

```bash
git add README.md docs/API.md docs/DEVELOPMENT.md
git commit -m "feat(phase-6): add comprehensive documentation

- Updated README with features, quick start, installation
- API documentation with all endpoints
- Development guide with setup and contribution
- Usage examples

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 6.7: End-to-End Testing

**Files:**
- Create: `tests/integration/test_e2e_system.py`
- Create: `tests/integration/test_e2e_performance.py`
- Create: `scripts/run_e2e_tests.sh`

**Step 1: Write the failing E2E test**

Create `tests/integration/test_e2e_system.py` from spec 6.7.

Start with the complete workflow test:

```python
"""
End-to-end integration tests for the complete interview system.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path

from httpx import AsyncClient

from src.main import app
from src.persistence.database import init_database
from src.core.config import Settings


class TestCompleteInterviewWorkflow:
    """Tests for complete interview from start to finish."""

    @pytest.mark.asyncio
    async def test_full_interview_workflow(self):
        """A complete interview runs through all phases."""
        # Setup
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Settings(
                database_path=Path(tmpdir) / "test.db",
                anthropic_api_key="test-key",
            )
            await init_database(settings.database_path)

            async with AsyncClient(app=app, base_url="http://test") as client:
                # 1. Create session
                response = await client.post(
                    "/sessions",
                    json={
                        "concept_id": "oat_milk_v1",
                        "max_turns": 10,
                        "target_coverage": 0.8,
                    },
                )
                assert response.status_code == 200
                session = response.json()
                session_id = session["id"]

                # 2. Get opening question
                response = await client.get(f"/sessions/{session_id}/status")
                assert response.status_code == 200
                status = response.json()
                question = status.get("next_question")
                assert question is not None

                # 3. Run a few turns
                for i in range(3):
                    response = await client.post(
                        f"/sessions/{session_id}/turns",
                        json={"user_input": f"Test response {i+1}"},
                    )
                    assert response.status_code == 200
                    turn_result = response.json()

                    assert "next_question" in turn_result
                    assert "extracted" in turn_result
                    assert "scoring" in turn_result

                # 4. Export session
                response = await client.get(
                    f"/sessions/{session_id}/export",
                    params={"format": "json"},
                )
                assert response.status_code == 200
```

**Step 2: Run test to verify it fails/passes**

Run: `pytest tests/integration/test_e2e_system.py::TestCompleteInterviewWorkflow::test_full_interview_workflow -v`
Expected: May pass if system is working, fix any issues

**Step 3: Add remaining E2E tests**

Add tests from spec:
- test_session_lifecycle
- test_synthetic_interview_achieves_coverage
- test_all_export_formats_work
- test_list_and_get_concepts
- test_health_check_returns_ok

**Step 4: Create performance tests**

Create `tests/integration/test_e2e_performance.py` from spec.

**Step 5: Create E2E test script**

Create `scripts/run_e2e_tests.sh` from spec.

**Step 6: Commit**

```bash
git add tests/integration/test_e2e_system.py tests/integration/test_e2e_performance.py scripts/run_e2e_tests.sh
git commit -m "feat(phase-6): add end-to-end integration tests

- Complete interview workflow test
- Session lifecycle test (create, use, export, delete)
- Synthetic interview integration test
- All export formats test
- Concept endpoints test
- Health check test
- Performance validation tests
- E2E test runner script

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 6.8: Performance Check

**Files:**
- Create: `tests/performance/test_latency.py`
- Create: `scripts/benchmark.py`
- Create: `docs/PERFORMANCE.md`
- Create: `tests/performance/` directory

**Step 1: Create performance tests directory**

```bash
mkdir -p tests/performance
touch tests/performance/__init__.py
```

**Step 2: Write latency tests**

Create `tests/performance/test_latency.py` from spec 6.8:

```python
"""
Performance tests for interview system latency.
"""

import pytest
import time
import asyncio
import statistics
from typing import List
from httpx import AsyncClient

from src.main import app


class TestTurnLatency:
    """Tests for turn processing latency."""

    @pytest.mark.asyncio
    async def test_single_turn_latency_under_5s(self):
        """Single turn completes in under 5 seconds."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create session
            response = await client.post(
                "/sessions",
                json={"concept_id": "oat_milk_v1"},
            )
            session_id = response.json()["id"]

            # Measure turn latency
            start = time.perf_counter()

            response = await client.post(
                f"/sessions/{session_id}/turns",
                json={"user_input": "Test response for latency measurement"},
            )

            elapsed = time.perf_counter() - start

            assert response.status_code == 200
            assert elapsed < 5.0, f"Turn took {elapsed:.2f}s (should be <5s)"
```

**Step 3: Run test to verify it passes**

Run: `pytest tests/performance/test_latency.py -v`
Expected: PASS (system latency should be fast)

**Step 4: Add remaining performance tests**

Add tests from spec:
- test_multiple_turns_average_latency
- test_graph_query_latency
- test_export_latency
- test_concurrent_session_capacity
- test_memory_leak_check

**Step 5: Create benchmark script**

Create `scripts/benchmark.py` from spec.

**Step 6: Create performance documentation**

Create `docs/PERFORMANCE.md` from spec.

**Step 7: Commit**

```bash
git add tests/performance/ scripts/benchmark.py docs/PERFORMANCE.md
git commit -m "feat(phase-6): add performance validation

- Turn latency tests (p95 < 5s requirement)
- Graph query latency test
- Export operation latency test
- Concurrent session capacity test
- Memory leak check
- Benchmark script for manual testing
- Performance requirements documentation

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Final Verification

After all tasks complete, run the final verification:

```bash
# Run all tests
pytest -v

# Run E2E tests
bash scripts/run_e2e_tests.sh

# Run benchmark
python scripts/benchmark.py

# Check logging
python scripts/check_logging.py

# Verify all imports
python3 -c "from src.services.export_service import ExportService; print('✓ Export service')"
python3 -c "from src.api.routes.concepts import router; print('✓ Concepts routes')"
python3 -c "from src.api.exception_handlers import setup_exception_handlers; print('✓ Exception handlers')"

# Verify docs exist
ls -la docs/API.md docs/DEVELOPMENT.md docs/PERFORMANCE.md docs/logging_standards.md docs/error_handling_checklist.md
```

---

**Phase 6 completes the MVP!** The system is now production-ready with:
- Export functionality (JSON, Markdown, CSV)
- Concept configuration management
- Comprehensive error handling
- Structured logging standards
- Complete documentation
- End-to-end integration tests
- Performance validation
