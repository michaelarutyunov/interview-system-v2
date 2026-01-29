# Interview System v2 - Development Guide

Guide for setting up development environment, running tests, and contributing to the Interview System v2 project.

## Table of Contents

- [Setting Up Development Environment](#setting-up-development-environment)
- [Running Tests](#running-tests)
- [Code Style](#code-style)
- [Adding Features](#adding-features)
- [Debugging](#debugging)
- [Architecture](#architecture)
- [Contributing](#contributing)

---

## Setting Up Development Environment

### Prerequisites

- Python 3.11 or higher
- Git
- Anthropic API key

### Initial Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd interview-system-v2
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # or
   .venv\Scripts\activate  # Windows
   ```

3. **Install uv (if not already installed):**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

4. **Install dependencies:**
   ```bash
   uv sync --dev
   ```

   This installs:
   - Core dependencies (FastAPI, uvicorn, aiosqlite, etc.)
   - Dev dependencies (pytest, ruff, pyright)

5. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your Anthropic API key
   ```

6. **Initialize the database:**
   ```bash
   # The database will be created automatically on first run
   # Or run tests to create test database
   uv run pytest
   ```

7. **Verify installation:**
   ```bash
   # Run health check
   uv run python -c "from src.core.config import settings; print(f'Config loaded: {settings.debug}')"

   # Start server
   uv run uvicorn src.main:app --reload
   ```

### IDE Setup

#### VS Code

Recommended extensions:
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Ruff (ms-python.ruff)

Create `.vscode/settings.json`:
```json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": "explicit"
  },
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "[python]": {
    "editor.defaultFormatter": "ms-python.ruff"
  }
}
```

#### PyCharm

1. Open project directory
2. Settings → Project → Python Interpreter → Add → Existing Environment
3. Select `.venv/bin/python`
4. Settings → Tools → Ruff → Enable (install Ruff plugin if needed)
5. Configure Ruff for formatting and import sorting

---

## Running Tests

### Test Structure

```
tests/
├── unit/              # Unit tests (fast, isolated)
│   ├── test_extraction_service.py
│   ├── test_session_service.py
│   ├── test_graph_service.py
│   └── ...
└── integration/       # Integration tests (slower, real dependencies)
    ├── test_session_flow.py
    └── test_turn_api.py
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run with coverage report
uv run pytest --cov=src --cov-report=html --cov-report=term

# Run specific test file
uv run pytest tests/unit/test_extraction_service.py

# Run specific test
uv run pytest tests/unit/test_extraction_service.py::test_extract_concepts

# Run only unit tests
uv run pytest tests/unit/

# Run only integration tests
uv run pytest tests/integration/

# Run with pytest watch (auto-rerun on changes)
uv run ptw
```

### Coverage Targets

- Unit test coverage: >80%
- Integration test coverage: >60%
- Overall coverage: >70%

### Writing Tests

#### Unit Tests

Test individual functions/classes in isolation:

```python
import pytest
from src.services.extraction_service import ExtractionService

@pytest.fixture
def extraction_service():
    return ExtractionService()

@pytest.mark.asyncio
async def test_extract_concepts(extraction_service):
    text = "I love yogurt because it's healthy and convenient"
    result = await extraction_service.extract_concepts(text)

    assert len(result.concepts) > 0
    assert any(c.text == "healthy" for c in result.concepts)
```

#### Integration Tests

Test multiple components working together:

```python
import pytest
from httpx import AsyncClient
from src.main import app

@pytest.mark.asyncio
async def test_complete_session_flow():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create session
        response = await client.post(
            "/sessions",
            json={"concept_id": "yogurt_consumption"}
        )
        assert response.status_code == 201
        session_id = response.json()["id"]

        # Start session
        response = await client.post(f"/sessions/{session_id}/start")
        assert response.status_code == 200

        # Submit turn
        response = await client.post(
            f"/sessions/{session_id}/turns",
            json={"text": "I buy yogurt for breakfast"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["should_continue"] == True
```

### Test Fixtures

Common fixtures in `tests/conftest.py`:

```python
import pytest
import aiosqlite
from src.services.session_service import SessionService

@pytest.fixture
async def test_db():
    """Create in-memory test database."""
    db = await aiosqlite.connect(":memory:")
    # Run migrations
    yield db
    await db.close()

@pytest.fixture
async def session_service(test_db):
    """Create session service with test database."""
    # Initialize with test repositories
    return SessionService(...)
```

---

## Code Style

### Formatting and Linting

We use **ruff** for both formatting and linting:

```bash
# Check and fix all issues
ruff check src/ tests/ --fix

# Format all code
ruff format src/ tests/

# Check formatting without making changes
ruff format --check src/ tests/
```

Configuration in `pyproject.toml`:
```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "W", "N"]
```

### Type Checking

We use **pyright** for static type checking:

```bash
# Type check all code (via LSP or CLI)
pyright src/

# Type check specific file
pyright src/services/session_service.py
```

### Pre-commit Workflow

Before committing code:
```bash
# 1. Check and fix linting issues
ruff check src/ tests/ --fix

# 2. Format code
ruff format src/ tests/

# 3. Run type checker
pyright src/

# 4. Run tests
uv run pytest
```

All checks must pass before committing.

---

## Adding Features

### Adding a New API Endpoint

1. **Define schemas in `src/api/schemas.py`:**
   ```python
   from pydantic import BaseModel

   class MyRequest(BaseModel):
       field: str

   class MyResponse(BaseModel):
       result: str
   ```

2. **Create route in `src/api/routes/`:**
   ```python
   from fastapi import APIRouter

   router = APIRouter(prefix="/myfeature", tags=["myfeature"])

   @router.post("", response_model=MyResponse)
   async def my_endpoint(request: MyRequest):
       return MyResponse(result=request.field)
   ```

3. **Register in `src/main.py`:**
   ```python
   from src.api.routes.myfeature import router as myfeature_router
   app.include_router(myfeature_router)
   ```

4. **Add tests:**
   ```python
   # tests/integration/test_myfeature.py
   import pytest
   from httpx import AsyncClient
   from src.main import app

   @pytest.mark.asyncio
   async def test_my_endpoint():
       async with AsyncClient(app=app, base_url="http://test") as client:
           response = await client.post(
               "/myfeature",
               json={"field": "test"}
           )
           assert response.status_code == 200
   ```

### Adding a New Service

1. **Create service file in `src/services/`:**
   ```python
   # src/services/my_service.py
   from typing import Protocol

   class MyService:
       def __init__(self, dependency: SomeRepository):
           self._repo = dependency

       async def do_something(self, input: str) -> str:
           # Business logic here
           result = await self._repo.query(input)
           return self._process(result)
   ```

2. **Add unit tests:**
   ```python
   # tests/unit/test_my_service.py
   import pytest
   from src.services.my_service import MyService

   @pytest.mark.asyncio
   async def test_do_something():
       service = MyService(mock_repository)
       result = await service.do_something("input")
       assert result == "expected"
   ```

3. **Integrate with existing services if needed**

### Adding a New Prompt

1. **Create prompt template in `src/llm/prompts/`:**
   ```python
   # src/llm/prompts/my_feature.py
   from anthropic.types import MessageParam

   def build_my_prompt(context: dict) -> list[MessageParam]:
       return [
           {
               "role": "user",
               "content": f"""Process this: {context['input']}"""
           }
       ]
   ```

2. **Use in service:**
   ```python
   from src.llm.prompts.my_feature import build_my_prompt

   async def my_service_method(self, input: str):
       messages = build_my_prompt({"input": input})
       response = await self.llm_client.generate(messages)
       return response
   ```

### Adding a New Methodology

**Signal Pools Architecture (ADR-014)**: Methodologies are now defined using YAML-based configuration files that combine signals from shared pools with strategy definitions. This replaces the old folder-per-methodology approach.

1. **Create YAML config in `src/methodologies/config/`:**
   ```yaml
   # src/methodologies/config/my_methodology.yaml
   methodology:
     name: my_methodology
     display_name: "My Interview Methodology"
     description: "Brief description of the methodology"

     # Signal definitions (namespaced)
     signals:
       graph:
         - graph.node_count
         - graph.max_depth
         - graph.orphan_count
       llm:
         - llm.response_depth
         - llm.sentiment
         - llm.topics
       temporal:
         - temporal.strategy_repetition_count
         - temporal.turns_since_focus_change
       meta:
         - meta.interview_progress
         - meta.exploration_score

     # Strategy definitions (weighted by signals)
     strategies:
       - name: deepen
         technique: laddering
         signal_weights:
           llm.response_depth.surface: 0.8
           graph.max_depth: 0.5
         focus_preference: shallow

       - name: broaden
         technique: elaboration
         signal_weights:
           llm.response_depth.deep: 0.7
           graph.coverage_breadth: 0.6
         focus_preference: recent
   ```

2. **The methodology is automatically available:**
   ```python
   from src.methodologies import get_registry

   # Load methodology
   registry = get_registry()
   config = registry.get_methodology("my_methodology")

   # Use with MethodologyStrategyService
   from src.services.methodology_strategy_service import MethodologyStrategyService
   service = MethodologyStrategyService()
   strategy, focus, alternatives, signals = await service.select_strategy(
       context, graph_state, response_text
   )
   ```

3. **Key components:**
   - **Signals**: Auto-detected from shared pools (graph/, llm/, temporal/, meta/)
   - **Techniques**: Reusable question generation modules (laddering, elaboration, probing, validation)
   - **Strategies**: Methodology-specific "when-to-use" logic defined in YAML
   - **Focus Selection**: Centralized in FocusSelectionService

**For more details:**
- [ADR-014](../adr/ADR-014-signal-pools-architecture.md) - Full signal pools architecture
- [Implementation Plan](../plans/refactor-signals-strategies-plan.md) - Migration details

### Adding a New Signal

**Signal Pools Architecture (ADR-014)**: Signals are grouped by data source into pools. Add new signals to the appropriate pool.

1. **Determine signal pool:**
   - `graph/` - Signals from knowledge graph (node_count, max_depth, orphan_count)
   - `llm/` - LLM-based signals from response text (response_depth, sentiment, topics)
   - `temporal/` - Turn-level temporal signals (strategy_repetition_count, turns_since_focus_change)
   - `meta/` - Composite signals derived from other signals (interview_progress, exploration_score)

2. **Create signal class:**
   ```python
   # src/methodologies/signals/graph/my_signal.py
   from typing import Any
   from src.methodologies.signals.common import SignalDetector, SignalCostTier, RefreshTrigger

   class MySignal(SignalDetector):
       """My custom signal description."""

       signal_name = "graph.my_signal"
       cost_tier = SignalCostTier.LOW  # FREE, LOW, MEDIUM, HIGH
       refresh_trigger = RefreshTrigger.PER_TURN  # PER_RESPONSE, PER_TURN, PER_SESSION

       async def detect(
           self,
           context: "PipelineContext",
           graph_state: "GraphState",
           response_text: str,
       ) -> dict[str, Any]:
           # Your signal detection logic here
           value = await self._calculate_value(graph_state)
           return {self.signal_name: value}

       async def _calculate_value(self, graph_state: "GraphState") -> float:
           # Implementation
           return graph_state.node_count * 0.5
   ```

3. **Export from pool `__init__.py`:**
   ```python
   # src/methodologies/signals/graph/__init__.py
   from .my_signal import MySignal

   __all__ = ["MySignal"]
   ```

4. **Register in signal registry:**
   ```python
   # src/methodologies/signals/registry.py
   SIGNAL_CLASSES = {
       # ... existing signals
       "graph.my_signal": MySignal,
   }
   ```

5. **Add to methodology YAML config:**
   ```yaml
   # src/methodologies/config/means_end_chain.yaml
   signals:
     graph:
       - graph.node_count
       - graph.max_depth
       - graph.my_signal  # Add your new signal
   ```

6. **Add tests:**
   ```python
   # tests/methodologies/signals/graph/test_my_signal.py
   import pytest
   from src.methodologies.signals.graph.my_signal import MySignal

   @pytest.mark.asyncio
   async def test_my_signal_detection(context, graph_state):
       signal = MySignal()
       result = await signal.detect(context, graph_state, "test response")
       assert "graph.my_signal" in result
       assert result["graph.my_signal"] >= 0
   ```

**LLM Signals** (fresh per response):
```python
# src/methodologies/signals/llm/my_llm_signal.py
from src.methodologies.signals.llm.common import BaseLLMSignal

class MyLLMSignal(BaseLLMSignal):
    """Fresh LLM analysis signal."""

    signal_name = "llm.my_llm_signal"
    # cost_tier = SignalCostTier.HIGH (inherited from BaseLLMSignal)
    # refresh_trigger = RefreshTrigger.PER_RESPONSE (inherited)

    async def _analyze_with_llm(self, response_text: str) -> dict[str, Any]:
        # Your LLM analysis logic here
        # Always computed fresh per response
        return {self.signal_name: await self._call_llm(response_text)}
```

### Adding a New Technique

**Techniques** are reusable "how-to" modules for generating questions. They are shared across all methodologies.

1. **Create technique class:**
   ```python
   # src/methodologies/techniques/my_technique.py
   from src.methodologies.techniques.base import Technique

   class MyTechnique(Technique):
       """My custom question generation technique."""

       name = "my_technique"
       description = "Brief description of what this technique does"

       async def generate_questions(
           self,
           focus: str | None,
           context: "PipelineContext",
       ) -> list[str]:
           # Generate questions based on focus and context
           questions = [
               f"Tell me more about {focus}...",
               f"Why is {focus} important to you?",
           ]

           # Access signals for conditional logic
           if context.signals.get("graph.max_depth", 0) < 2:
               questions.append(f"And what does that mean for you?")

           return questions
   ```

2. **Export from techniques module:**
   ```python
   # src/methodologies/techniques/__init__.py
   from .my_technique import MyTechnique

   __all__ = ["MyTechnique", "LadderingTechnique", ...]
   ```

3. **Register in methodology registry:**
   ```python
   # src/methodologies/registry.py
   TECHNIQUE_CLASSES = {
       # ... existing techniques
       "my_technique": MyTechnique,
   }
   ```

4. **Use in methodology YAML config:**
   ```yaml
   # src/methodologies/config/means_end_chain.yaml
   strategies:
     - name: my_strategy
       technique: my_technique  # Use your new technique
       signal_weights:
         graph.max_depth: 0.5
       focus_preference: shallow
   ```

5. **Add tests:**
   ```python
   # tests/methodologies/techniques/test_my_technique.py
   import pytest
   from src.methodologies.techniques.my_technique import MyTechnique

   @pytest.mark.asyncio
   async def test_my_technique_generates_questions(context):
       technique = MyTechnique()
       questions = await technique.generate_questions("test focus", context)
       assert len(questions) > 0
       assert all(isinstance(q, str) for q in questions)
   ```

---

## Debugging

### Logging

The system uses structured logging with `structlog`:

```python
import structlog

log = structlog.get_logger(__name__)

# Log with context
log.info(
    "processing_turn",
    session_id=session_id,
    turn_number=turn_number,
    text_length=len(text)
)

# Log warning
log.warning(
    "session_not_found",
    session_id=session_id
)

# Log error
log.error(
    "extraction_failed",
    error=str(e),
    error_type=type(e).__name__
)
```

View logs in console:
```bash
# Logs are output to stdout in JSON format
uvicorn src.main:app --reload | jq
```

### Debug Mode

Enable debug mode in `.env`:
```env
DEBUG=true
```

This enables:
- Detailed error messages
- CORS for all origins
- Auto-reload on code changes
- Detailed request logging

### Using pdb

Add breakpoints in code:
```python
import pdb

def my_function():
    result = calculate()
    pdb.set_trace()  # Execution stops here
    return result
```

Or use breakpoint() (Python 3.7+):
```python
def my_function():
    result = calculate()
    breakpoint()  # Equivalent to pdb.set_trace()
    return result
```

### VS Code Debugging

Create `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["src.main:app", "--reload"],
      "envFile": "${workspaceFolder}/.env",
      "console": "integratedTerminal"
    },
    {
      "name": "Pytest",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["tests/unit/test_session_service.py", "-v"],
      "console": "integratedTerminal"
    }
  ]
}
```

### Database Inspection

Use SQLite CLI to inspect database:
```bash
sqlite3 data/interview.db

# List tables
.tables

# View schema
.schema sessions

# Query data
SELECT * FROM sessions LIMIT 5;

# Exit
.quit
```

Or use DB Browser for SQLite (GUI):
```bash
# Install
sudo apt install sqlitebrowser  # Ubuntu
brew install --cask db-browser-for-sqlite  # Mac

# Open
sqlitebrowser data/interview.db
```

---

## Error Handling Standards

### Exception Hierarchy

All custom exceptions inherit from `InterviewSystemError`:

```
InterviewSystemError (base)
├── ConfigurationError
├── LLMError
│   ├── LLMTimeoutError
│   ├── LLMRateLimitError
│   ├── LLMContentFilterError
│   ├── LLMResponseParseError
│   └── LLMInvalidResponseError
├── SessionError
│   ├── SessionNotFoundError
│   ├── SessionCompletedError
│   └── SessionAbandonedError
├── ExtractionError
├── ValidationError
└── GraphError
    ├── NodeNotFoundError
    └── DuplicateNodeError
```

### API Error Responses

All error responses follow this structure:

```json
{
  "error": {
    "type": "ExceptionClassName",
    "message": "Human-readable error message"
  }
}
```

### Status Code Mapping

| Exception | Status Code | Use Case |
|-----------|-------------|----------|
| `SessionNotFoundError` | 404 | Session doesn't exist |
| `ValidationError` | 400 | Invalid input |
| `SessionCompletedError` | 400 | Modifying completed session |
| `LLMTimeoutError` | 504 | LLM call timed out |
| `LLMRateLimitError` | 429 | Rate limit exceeded |
| `InterviewSystemError` | 500 | Other system errors |
| `ConfigurationError` | 500 | Configuration issues |

### Raising Exceptions in Services

```python
from src.domain.errors import SessionNotFoundError, ValidationError

async def get_session(self, session_id: str) -> Session:
    session = await self.session_repo.get(session_id)
    if not session:
        raise SessionNotFoundError(f"Session '{session_id}' not found")
    return session

async def validate_input(self, text: str) -> None:
    if not text or len(text.strip()) == 0:
        raise ValidationError("Input text cannot be empty")
```

### Security Considerations

- Configuration errors return generic messages (don't expose internal details)
- Unhandled exceptions don't expose stack traces to clients
- Sensitive information (API keys, passwords) never logged
- Error messages are user-friendly but informative

---

## Logging Standards

### Configuration

All logging uses `structlog` with context-bound loggers:

```python
from src.core.logging import get_logger

log = get_logger(__name__)
```

### Event Logging Standards

| Event | Level | Required Fields |
|-------|-------|-----------------|
| Request received | INFO | endpoint, method, session_id |
| LLM call start | DEBUG | provider, model, prompt_tokens |
| LLM call complete | INFO | provider, model, latency_ms, tokens_used |
| LLM call failed | ERROR | provider, model, error_type, error_message |
| Extraction complete | INFO | session_id, turn_number, concept_count |
| Strategy selected | INFO | session_id, turn_number, strategy |
| Session created | INFO | session_id, methodology, concept_id |
| Session completed | INFO | session_id, turns, coverage, duration_seconds |
| Database query | DEBUG | query, table, rows_affected |
| Error | ERROR | error_type, error_message, context |

### Level Guidelines

- **DEBUG**: Detailed diagnostics (database queries, LLM prompts, token counts)
- **INFO**: Normal operations (requests, responses, completions)
- **WARNING**: Recoverable issues (fallbacks, retries, deprecated usage)
- **ERROR**: Errors that affect operation (API failures, validation errors)
- **CRITICAL**: System-wide failures (service unavailable, data corruption)

### Binding Context

Always bind relevant context to loggers:

```python
from src.core.logging import bind_context, get_logger

# Bind request-scoped context
bind_context(session_id=session.id, request_id=request_id)

# Or bind to a specific logger instance
log = log.bind(session_id=session.id, turn_number=turn.number)
```

### Examples

**Basic Logging:**
```python
from src.core.logging import get_logger

log = get_logger(__name__)

# Info level - normal operations
log.info("session_created", session_id=session.id, methodology=session.methodology)

# Error level - with context
log.error(
    "llm_call_failed",
    provider="openai",
    model="gpt-4",
    error_type=str(type(e).__name__),
    error_message=str(e),
)
```

**Structured Data:**
```python
# Always log structured data as keyword arguments
log.info(
    "extraction_complete",
    session_id=session.id,
    turn_number=turn.number,
    concept_count=len(concepts),
    concepts=[c.name for c in concepts],
)
```

### What Not to Log

- Passwords, API keys, or secrets
- Large payloads (log size/offset instead)
- PII in production (anonymize or hash)
- Full request bodies in production (log metadata only)

---

## Architecture

### Layered Architecture

```
┌─────────────────────────────────────────┐
│           API Layer (FastAPI)           │  HTTP handlers, routing
├─────────────────────────────────────────┤
│         Service Layer (Business)        │  Orchestration, logic
├─────────────────────────────────────────┤
│          Domain Layer (Models)          │  Core entities
├─────────────────────────────────────────┤
│      Persistence Layer (Repositories)   │  Data access
├─────────────────────────────────────────┤
│         Infrastructure (LLM, DB)        │  External services
└─────────────────────────────────────────┘
```

### Key Design Patterns

- **Pipeline Pattern** (ADR-008): Turn processing through 10 independent stages
- **Repository Pattern**: Data access abstraction
- **Service Layer**: Business logic encapsulation
- **Dependency Injection**: FastAPI Depends for testability
- **Factory Pattern**: Service creation with dependencies
- **Strategy Pattern**: Scoring metrics and question strategies

### Pipeline Architecture (ADR-008)

The core turn processing flow uses a pipeline pattern with 10 independent stages:

```
SessionService.process_turn()
    │
    └─→ TurnPipeline.execute(TurnContext)
            │
            ├─→ ContextLoadingStage       # Load session metadata
            ├─→ UtteranceSavingStage      # Save user input
            ├─→ ExtractionStage           # Extract concepts
            ├─→ GraphUpdateStage          # Update knowledge graph
            ├─→ StateComputationStage     # Recompute graph state
            ├─→ StrategySelectionStage    # Select strategy (scoring)
            ├─→ ContinuationStage         # Decide to continue
            ├─→ QuestionGenerationStage   # Generate next question
            ├─→ ResponseSavingStage       # Save system response
            └─→ ScoringPersistenceStage   # Save scoring data
```

**TurnContext** is the data bucket that flows through stages:
```python
@dataclass
class TurnContext:
    session_id: str
    user_input: str
    turn_number: int
    methodology: str = ""
    graph_state: Optional[GraphState] = None
    extraction: Optional[ExtractionResult] = None
    strategy: str = "deepen"
    next_question: str = ""
    should_continue: bool = True
    # ... and more
```

**Key principle**: Each stage only reads/writes TurnContext. No stage calls another stage directly. This makes changes isolated and safe.

**For more details**:
- `docs/data_flow_diagram.md` - Complete pipeline flow documentation
- `docs/raw_ideas/pipeline_architecture_visualization.md` - Before/after comparison with examples
- `docs/adr/008-internal-api-boundaries-pipeline-pattern.md` - Full ADR

### Pipeline Contracts (ADR-010 Phase 2)

ADR-010 Phase 2 introduced typed Pydantic models for all pipeline stage inputs and outputs:

**Key Benefits:**
- **Type Safety**: Runtime validation prevents data corruption
- **Traceability**: `source_utterance_id` links extraction results to specific utterances
- **Freshness Tracking**: `computed_at` timestamps prevent using stale graph state
- **Documentation**: Field descriptions serve as inline documentation

**Contract Models Location:**
```python
# src/domain/models/pipeline_contracts.py
class ContextLoadingOutput(BaseModel):
    """Output from ContextLoadingStage with session metadata and graph state."""
    session_id: str
    methodology: str
    concept_id: str
    graph_state: GraphState
    computed_at: datetime  # Freshness tracking

class StrategySelectionOutput(BaseModel):
    """Output from StrategySelectionStage with scoring breakdown."""
    strategy: Dict[str, Any]
    focus: Focus
    scoring_result: Optional[ScoringResult]
    alternative_strategies: List[ScoredStrategy]
```

**Traceability Pattern:**
All extraction data includes `source_utterance_id`:
```python
# ExtractionResult
ExtractedConcept(
    text="oat milk is creamy",
    node_type="attribute",
    source_utterance_id="utter_123",  # Links to UtteranceSavingOutput
)

# QualitativeSignalSet
QualitativeSignalSet(
    turn_number=5,
    source_utterance_id="utter_123",  # Same utterance
    generated_at=datetime.now(timezone.utc),
    llm_model="moonshot-v1-8k",
    prompt_version="v2.1",
)
```

**For more details:**
- `docs/adr/010-formalize-pipeline-contracts-strengthen-data-models.md` - Full ADR
- `docs/pipeline_contracts.md` - Stage-by-stage contract documentation
- `docs/data_flow_paths.md` - Traceability chain visualization

### Concept-Driven Coverage (ADR-008)

The system uses a two-layer architecture for interview guidance:

```
CONCEPT (WHAT to explore)          METHODOLOGY (HOW to explore)
┌─────────────────────────┐        ┌─────────────────────────┐
│ ELEMENTS                │        │ NODE TYPES (ladder)     │
│ ├─ creamy_texture       │        │ ├─ attribute            │
│ ├─ plant_based          │   ×    │ ├─ functional_conseq    │
│ └─ sustainable          │        │ ├─ psychosocial_conseq  │
│    (semantic targets)   │        │ └─ value                │
└─────────────────────────┘        └─────────────────────────┘
           │                                  │
           └──────────────┬───────────────────┘
                          ▼
              NODES (Extracted Knowledge)
    ┌─────────────────────────────────────────────┐
    │ "silky foam"     → linked to: creamy_texture │
    │ (type: attribute)                            │
    │                                              │
    │ "feels indulgent" → linked to: creamy_texture│
    │ (type: psychosocial_consequence)             │
    └─────────────────────────────────────────────┘
```

**Key Components:**
- `src/core/concept_loader.py` - Load concept definitions with caching
- `src/domain/models/concept.py` - Concept, ConceptElement, CoverageState models
- `src/services/depth_calculator.py` - Chain validation for depth tracking

**Coverage State:**
```python
coverage_state = {
    "elements": {
        1: {  # "Creamy texture"
            "covered": True,
            "linked_node_ids": ["node_123"],
            "types_found": ["attribute"],
            "depth_score": 0.5,  # Chain validation
        },
    },
    "elements_covered": 1,
    "elements_total": 6,
    "overall_depth": 0.25,
}
```

**For more details:**
- `docs/concept_system.md` - Complete concept system documentation
- `docs/adr/008-concept-element-coverage-system.md` - Full ADR

### Directory Structure

```
src/
├── api/                    # HTTP interface
│   ├── routes/            # Route handlers
│   └── schemas.py         # Request/response models
├── core/                  # Configuration, logging
│   ├── concept_loader.py  # Load concept definitions (ADR-008)
│   └── schema_loader.py   # Load methodology schemas
├── domain/                # Business entities
│   └── models/            # Pydantic models
│       ├── concept.py     # Concept, ConceptElement, CoverageState (ADR-008)
│       ├── knowledge_graph.py  # KGNode, KGEdge, GraphState, SaturationMetrics
│       ├── extraction.py  # ExtractionResult, ExtractedConcept, ExtractedRelationship
│       ├── pipeline_contracts.py  # Stage I/O models (ADR-010)
│       └── turn.py        # TurnContext, TurnResult, Focus
├── llm/                   # LLM integration
│   ├── client.py
│   └── prompts/
├── methodologies/         # Methodology module (ADR-014)
│   ├── signals/           # Shared signal pools
│   │   ├── common.py      # SignalDetector, enums
│   │   ├── graph/         # Graph-based signals
│   │   ├── llm/           # LLM-based signals (fresh per response)
│   │   ├── temporal/      # Temporal signals
│   │   ├── meta/          # Composite signals
│   │   └── registry.py    # ComposedSignalDetector
│   ├── techniques/        # Shared technique pool
│   │   ├── laddering.py
│   │   ├── elaboration.py
│   │   ├── probing.py
│   │   └── validation.py
│   ├── config/            # YAML methodology definitions
│   │   ├── means_end_chain.yaml
│   │   └── jobs_to_be_done.yaml
│   ├── registry.py        # MethodologyRegistry (YAML loader)
│   └── scoring.py         # Strategy scoring with signal weights
├── persistence/           # Data persistence
│   ├── database.py
│   ├── migrations/
│   └── repositories/      # Session, Graph, Utterance repositories
└── services/              # Business logic
    ├── depth_calculator.py  # Chain validation for depth (ADR-008)
    ├── methodology_strategy_service.py  # YAML-based strategy selection
    ├── focus_selection_service.py  # Centralized focus selection
    ├── turn_pipeline/     # Pipeline orchestrator (ADR-008)
    │   ├── stages/        # 10 independent stages
    │   ├── base.py        # TurnStage base class
    │   ├── context.py     # PipelineContext dataclass
    │   ├── pipeline.py    # TurnPipeline orchestrator
    │   └── result.py      # TurnResult model
    └── ...
```

---

## Contributing

### Development Workflow

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes:**
   - Write code following style guidelines
   - Add/update tests
   - Update documentation if needed

3. **Run tests:**
   ```bash
   uv run pytest
   ruff check src/ tests/
   ruff format --check src/ tests/
   uv run pyright src/
   ```

4. **Commit changes:**
   ```bash
   git add .
   git commit -m "feat: add my new feature"
   ```

5. **Push and create PR:**
   ```bash
   git push origin feature/my-feature
   # Create PR on GitHub
   ```

### Commit Messages

Follow conventional commits:

```
feat: add new scoring metric
fix: handle empty extraction results
docs: update API documentation
test: add integration tests for session flow
refactor: simplify service initialization
chore: upgrade dependencies
```

### Pull Request Guidelines

- Title should summarize changes
- Description should explain why and what
- Link related issues
- Ensure all tests pass
- Request review from maintainer

### Code Review Criteria

- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] Performance considered
- [ ] Security considered

### Getting Help

- Check existing issues
- Read documentation
- Ask in PR comments
- Contact maintainers

---

## Common Issues

### Import Errors

```bash
# ModuleNotFoundError: No module named 'src'
# Solution: Install dependencies with uv
uv sync --dev
```

### Database Lock Errors

```python
# aiosqlite.OperationalError: database is locked
# Solution: Use separate databases for testing
# Or close connections properly
```

### LLM Rate Limits

```python
# anthropic.RateLimitError
# Solution: Implement exponential backoff
# Or cache responses
```

### Test Failures

```bash
# Tests fail intermittently
# Solution: Check for async issues
# Ensure proper cleanup in fixtures
# Use explicit waits for async operations
```

---

## Performance Tips

1. **Use async/await properly** - Don't block the event loop
2. **Batch database operations** - Use transactions
3. **Cache LLM responses** - Reduce API calls
4. **Use connection pooling** - Reuse database connections
5. **Profile before optimizing** - Use cProfile or py-spy

---

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Anthropic API Documentation](https://docs.anthropic.com/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [pytest Documentation](https://docs.pytest.org/)

---

## License

MIT License - see LICENSE file for details
