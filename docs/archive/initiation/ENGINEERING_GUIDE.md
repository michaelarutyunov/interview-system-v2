# Adaptive Interview System v2: Engineering Guide

**Status:** Draft  
**Date:** January 2026  
**Companion to:** PRD v2.0

---

## 1. Purpose

This guide defines **how** to build the system specified in the PRD. It covers code patterns, library choices, configuration schemas, and engineering constraints that ensure consistency across implementation.

**Scope:** This guide is prescriptive. Deviations require explicit justification.

---

## 2. Technology Stack

### 2.1 Core Stack

| Component | Choice | Version | Rationale |
|-----------|--------|---------|-----------|
| **Language** | Python | 3.11.x | Stable async, avoid 3.14 edge cases |
| **Web Framework** | FastAPI | 0.109+ | Async-native, OpenAPI generation |
| **Database** | SQLite | 3.40+ | Zero config, JSON1 extension for graphs |
| **Async SQLite** | aiosqlite | 0.19+ | Async wrapper for SQLite |
| **HTTP Client** | httpx | 0.26+ | Async HTTP for LLM calls |
| **Validation** | Pydantic | 2.x | Data models, settings management |
| **Logging** | structlog | 24.x | Structured logging |
| **Testing** | pytest + pytest-asyncio | 8.x | Async test support |
| **Config** | PyYAML + Pydantic | - | YAML files validated by Pydantic |

### 2.2 Optional/Future Stack

| Component | Choice | When to Add |
|-----------|--------|-------------|
| **PostgreSQL** | asyncpg | Multi-user or >10K sessions |
| **Redis** | redis-py async | Cross-instance session sharing |
| **Task Queue** | arq | Background processing |
| **Embeddings** | sentence-transformers | Semantic deduplication |

### 2.3 Explicitly Avoided

| Library | Reason |
|---------|--------|
| **SQLAlchemy ORM** | Overhead for simple graph patterns; raw SQL preferred |
| **Celery** | Overkill for single-user; arq if needed |
| **LangChain** | Abstraction layer adds complexity without clear benefit |
| **spaCy/NLTK** | Keyword-dependent; LLM-based extraction preferred |

---

## 3. Project Structure

```
interview-system-v2/
├── src/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry point
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── sessions.py        # /sessions endpoints
│   │   │   ├── concepts.py        # /concepts endpoints
│   │   │   ├── synthetic.py       # /synthetic endpoints
│   │   │   └── health.py          # /health endpoint
│   │   ├── dependencies.py        # FastAPI dependencies (DB, services)
│   │   └── schemas.py             # Pydantic request/response models
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Settings management
│   │   ├── logging.py             # structlog configuration
│   │   └── exceptions.py          # Custom exceptions
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── models/
│   │   │   ├── session.py         # Session domain model
│   │   │   ├── utterance.py       # Utterance model
│   │   │   ├── concept.py         # Stimulus concept model
│   │   │   ├── knowledge_graph.py # KG node/edge models
│   │   │   └── conversational_graph.py  # CG models
│   │   └── enums.py               # Shared enumerations
│   ├── services/
│   │   ├── __init__.py
│   │   ├── session_service.py     # Session orchestration
│   │   ├── extraction_service.py  # Concept/relationship extraction
│   │   ├── graph_service.py       # Knowledge graph operations
│   │   ├── scoring_service.py     # Coverage, depth, saturation scoring
│   │   ├── strategy_service.py    # Strategy selection
│   │   ├── question_service.py    # Question generation
│   │   └── synthetic_service.py   # Synthetic respondent
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py              # LLM client abstraction
│   │   ├── prompts/
│   │   │   ├── extraction.py      # Extraction prompts
│   │   │   ├── question.py        # Question generation prompts
│   │   │   └── synthetic.py       # Synthetic respondent prompts
│   │   └── parsers.py             # Response parsing utilities
│   ├── persistence/
│   │   ├── __init__.py
│   │   ├── database.py            # SQLite connection management
│   │   ├── repositories/
│   │   │   ├── session_repo.py
│   │   │   ├── graph_repo.py
│   │   │   └── concept_repo.py
│   │   └── migrations/
│   │       └── 001_initial.sql
│   └── utils/
│       ├── __init__.py
│       └── text.py                # Text processing utilities
├── config/
│   ├── default.yaml               # Default configuration
│   ├── methodologies/
│   │   └── means_end_chain.yaml   # MEC methodology config
│   ├── concepts/
│   │   └── example_oat_milk.yaml  # Example stimulus concept
│   └── scoring/
│       └── default.yaml           # Scoring parameters
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Shared fixtures
│   ├── unit/
│   │   ├── test_extraction.py
│   │   ├── test_scoring.py
│   │   └── test_graph.py
│   ├── integration/
│   │   ├── test_session_flow.py
│   │   └── test_api.py
│   └── fixtures/
│       ├── concepts/
│       ├── responses/
│       └── graphs/
├── scripts/
│   ├── run_synthetic_interview.py # Run automated test interview
│   └── export_session.py          # Export session to JSON/MD
├── specs/                         # Loopable implementation specs
│   ├── phase-1/
│   ├── phase-2/
│   └── ...
├── pyproject.toml
├── README.md
└── .env.example
```

---

## 4. Configuration System

### 4.1 Principles

1. **YAML for domain configuration** (concepts, methodologies, scoring)
2. **Environment variables for secrets** (API keys)
3. **Pydantic for validation** (all YAML loaded into Pydantic models)
4. **No hardcoded thresholds** in business logic

### 4.2 Settings Model

```python
# src/core/config.py

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Paths
    config_dir: Path = Field(default=Path("config"))
    data_dir: Path = Field(default=Path("data"))
    
    # Database
    database_path: Path = Field(default=Path("data/interview.db"))
    
    # LLM
    llm_provider: str = Field(default="anthropic")
    anthropic_api_key: Optional[str] = Field(default=None)
    llm_model: str = Field(default="claude-sonnet-4-20250514")
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=1024)
    llm_timeout_seconds: float = Field(default=30.0)
    
    # Interview defaults
    default_max_turns: int = Field(default=20)
    default_target_coverage: float = Field(default=0.8)
    
    # Server
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)
    debug: bool = Field(default=False)


settings = Settings()
```

### 4.3 Methodology Configuration Schema

```yaml
# config/methodologies/means_end_chain.yaml

id: means_end_chain
name: "Means-End Chain Analysis"
description: "Laddering technique linking Attributes → Consequences → Values"

# Node type schema
node_types:
  - id: attribute
    label: "Attribute"
    description: "Concrete product feature or characteristic"
    abstraction_level: low
    is_terminal: false
    
  - id: functional_consequence
    label: "Functional Consequence"  
    description: "Tangible outcome from using the product"
    abstraction_level: medium
    is_terminal: false
    
  - id: psychosocial_consequence
    label: "Psychosocial Consequence"
    description: "Emotional or social outcome"
    abstraction_level: medium_high
    is_terminal: false
    
  - id: instrumental_value
    label: "Instrumental Value"
    description: "Preferred mode of behavior"
    abstraction_level: high
    is_terminal: false
    
  - id: terminal_value
    label: "Terminal Value"
    description: "End-state of existence"
    abstraction_level: highest
    is_terminal: true

# Valid relationship types
edge_types:
  - id: leads_to
    label: "Leads To"
    description: "Causal or enabling relationship"
    
  - id: revises
    label: "Revises"
    description: "Contradiction - newer belief supersedes older"

# Laddering constraints
laddering:
  valid_progressions:
    - [attribute, functional_consequence]
    - [attribute, psychosocial_consequence]
    - [functional_consequence, psychosocial_consequence]
    - [functional_consequence, instrumental_value]
    - [psychosocial_consequence, instrumental_value]
    - [psychosocial_consequence, terminal_value]
    - [instrumental_value, terminal_value]
  
  probe_templates:
    attribute: "Why is {concept} important to you?"
    functional_consequence: "What does {concept} enable you to do?"
    psychosocial_consequence: "How does {concept} make you feel?"
    instrumental_value: "Why is {concept} important in your life?"
```

### 4.4 Stimulus Concept Schema

```yaml
# config/concepts/example_oat_milk.yaml

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

opening:
  style: warm
  template: "I'd like to understand your thoughts about {product_name}. What comes to mind when you think about it?"

completion:
  target_coverage: 0.8
  max_turns: 20
  saturation_threshold: 0.05
```

---

## 5. Logging with structlog

### 5.1 Configuration

```python
# src/core/logging.py

import logging
import structlog
from structlog.typing import Processor
from typing import List

from src.core.config import settings


def configure_logging() -> None:
    """Configure structlog for the application."""
    
    shared_processors: List[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.ExtraAdder(),
    ]
    
    if settings.debug:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    else:
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ]
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a logger instance with the given name."""
    return structlog.get_logger(name)
```

### 5.2 Usage Patterns

```python
from src.core.logging import get_logger

log = get_logger(__name__)

async def process_turn(session_id: str, turn_number: int, response: str):
    log_ctx = log.bind(session_id=session_id, turn_number=turn_number)
    
    log_ctx.info("processing_turn", response_length=len(response))
    
    try:
        result = await extract_concepts(response)
        log_ctx.info(
            "extraction_complete",
            concept_count=len(result.concepts),
            relationship_count=len(result.relationships)
        )
        return result
    except ExtractionError as e:
        log_ctx.error("extraction_failed", error_type=type(e).__name__, error_message=str(e))
        raise
```

### 5.3 Logging Standards

| Event | Level | Required Fields |
|-------|-------|-----------------|
| Request received | INFO | `endpoint`, `method`, `session_id` (if applicable) |
| LLM call start | DEBUG | `provider`, `model`, `prompt_tokens` (estimated) |
| LLM call complete | INFO | `provider`, `model`, `latency_ms`, `tokens_used` |
| LLM call failed | ERROR | `provider`, `model`, `error_type`, `error_message` |
| Extraction complete | INFO | `session_id`, `turn_number`, `concept_count` |
| Strategy selected | INFO | `session_id`, `turn_number`, `strategy`, `scores` |
| Session created | INFO | `session_id`, `methodology`, `concept_id` |
| Session completed | INFO | `session_id`, `turns`, `coverage`, `duration_seconds` |

---

## 6. LLM Integration

### 6.1 Client Abstraction

```python
# src/llm/client.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
import httpx
import structlog

from src.core.config import settings

log = structlog.get_logger(__name__)


@dataclass
class LLMResponse:
    """Standardized LLM response."""
    content: str
    model: str
    usage: Dict[str, int]
    latency_ms: float
    raw_response: Optional[Dict[str, Any]] = None


class LLMClient(ABC):
    """Abstract base for LLM providers."""
    
    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        pass


class AnthropicClient(LLMClient):
    """Anthropic Claude client."""
    
    def __init__(self):
        self.api_key = settings.anthropic_api_key
        self.model = settings.llm_model
        self.base_url = "https://api.anthropic.com/v1"
        self.timeout = settings.llm_timeout_seconds
        
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")
    
    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        import time
        start = time.perf_counter()
        
        headers = {
            "x-api-key": self.api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": self.model,
            "max_tokens": max_tokens or settings.llm_max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        if system:
            payload["system"] = system
        if temperature is not None:
            payload["temperature"] = temperature
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
        
        latency_ms = (time.perf_counter() - start) * 1000
        
        log.info(
            "llm_call_complete",
            provider="anthropic",
            model=self.model,
            latency_ms=round(latency_ms, 2),
            input_tokens=data["usage"]["input_tokens"],
            output_tokens=data["usage"]["output_tokens"]
        )
        
        return LLMResponse(
            content=data["content"][0]["text"],
            model=data["model"],
            usage={
                "input_tokens": data["usage"]["input_tokens"],
                "output_tokens": data["usage"]["output_tokens"]
            },
            latency_ms=latency_ms,
            raw_response=data
        )


def get_llm_client() -> LLMClient:
    """Factory for LLM client based on configuration."""
    if settings.llm_provider == "anthropic":
        return AnthropicClient()
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
```

---

## 7. Error Handling

### 7.1 Exception Hierarchy

```python
# src/core/exceptions.py

class InterviewSystemError(Exception):
    """Base exception for all application errors."""
    pass


class ConfigurationError(InterviewSystemError):
    """Invalid configuration."""
    pass


class LLMError(InterviewSystemError):
    """Base for LLM-related errors."""
    pass


class LLMTimeoutError(LLMError):
    """LLM call timed out."""
    pass


class LLMRateLimitError(LLMError):
    """LLM rate limit exceeded."""
    pass


class ExtractionError(InterviewSystemError):
    """Failed to extract concepts from response."""
    pass


class SessionError(InterviewSystemError):
    """Session-related error."""
    pass


class SessionNotFoundError(SessionError):
    """Session does not exist."""
    pass


class SessionCompletedError(SessionError):
    """Attempted operation on completed session."""
    pass
```

### 7.2 Graceful Degradation

```python
async def extract_with_degradation(response: str, context: dict, llm_client: LLMClient):
    """Extract concepts with graceful degradation."""
    log = structlog.get_logger(__name__)
    
    try:
        result = await full_extraction(response, context, llm_client)
        return result
        
    except LLMTimeoutError:
        log.warning("extraction_degraded", reason="timeout")
        return ExtractionResult(concepts=[], relationships=[], discourse_markers=[])
        
    except LLMRateLimitError:
        log.warning("extraction_degraded", reason="rate_limit")
        return ExtractionResult(concepts=[], relationships=[], discourse_markers=[])
```

---

## 8. Database Schema

```sql
-- src/persistence/migrations/001_initial.sql

-- Sessions table
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    methodology TEXT NOT NULL,
    concept_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    config JSON NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT
);

-- Utterances (conversational graph persistence)
CREATE TABLE utterances (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    turn_number INTEGER NOT NULL,
    speaker TEXT NOT NULL,
    text TEXT NOT NULL,
    discourse_markers JSON DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(session_id, turn_number, speaker)
);

CREATE INDEX idx_utterances_session ON utterances(session_id);

-- Knowledge graph nodes
CREATE TABLE kg_nodes (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    label TEXT NOT NULL,
    node_type TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.8,
    properties JSON DEFAULT '{}',
    source_utterance_ids JSON NOT NULL,
    recorded_at TEXT NOT NULL DEFAULT (datetime('now')),
    superseded_by TEXT REFERENCES kg_nodes(id),
    UNIQUE(session_id, label, node_type, superseded_by)
);

CREATE INDEX idx_kg_nodes_session ON kg_nodes(session_id);

-- Knowledge graph edges
CREATE TABLE kg_edges (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    source_node_id TEXT NOT NULL REFERENCES kg_nodes(id),
    target_node_id TEXT NOT NULL REFERENCES kg_nodes(id),
    edge_type TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.8,
    properties JSON DEFAULT '{}',
    source_utterance_ids JSON NOT NULL,
    recorded_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(source_node_id, target_node_id, edge_type)
);

CREATE INDEX idx_kg_edges_session ON kg_edges(session_id);

-- Scoring history
CREATE TABLE scoring_history (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    turn_number INTEGER NOT NULL,
    coverage_score REAL NOT NULL,
    depth_score REAL NOT NULL,
    saturation_score REAL NOT NULL,
    strategy_selected TEXT NOT NULL,
    strategy_reasoning TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(session_id, turn_number)
);
```

---

## 9. Testing Strategy

### 9.1 Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Fast, isolated tests
│   ├── test_extraction.py
│   ├── test_scoring.py
│   └── test_graph.py
├── integration/             # Tests with real dependencies
│   ├── test_api.py
│   └── test_session_flow.py
└── fixtures/
    ├── concepts/
    └── responses/
```

### 9.2 Key Fixtures

```python
# tests/conftest.py

import pytest
import pytest_asyncio
import tempfile
from pathlib import Path

from src.core.config import Settings
from src.persistence.database import init_database


@pytest.fixture
def test_settings():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Settings(
            config_dir=Path("config"),
            data_dir=Path(tmpdir),
            database_path=Path(tmpdir) / "test.db",
            debug=True,
            anthropic_api_key="test-key"
        )


@pytest_asyncio.fixture
async def test_db(test_settings):
    await init_database(test_settings.database_path)
    yield test_settings.database_path
```

---

## 10. Code Style

- **Black** for formatting (line length: 100)
- **isort** for imports
- **Type hints** required for all public functions

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Files | snake_case | `session_service.py` |
| Classes | PascalCase | `SessionService` |
| Functions | snake_case | `process_turn` |
| Constants | UPPER_SNAKE | `MAX_RETRY_ATTEMPTS` |

---

## Appendix: Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | - | Anthropic API key |
| `LLM_MODEL` | No | `claude-sonnet-4-20250514` | Model to use |
| `DATABASE_PATH` | No | `data/interview.db` | SQLite path |
| `DEBUG` | No | `false` | Enable debug mode |
