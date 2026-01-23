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

3. **Install dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

   This installs:
   - Core dependencies (FastAPI, uvicorn, aiosqlite, etc.)
   - Dev dependencies (pytest, black, isort, mypy)

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your Anthropic API key
   ```

5. **Initialize the database:**
   ```bash
   # The database will be created automatically on first run
   # Or run tests to create test database
   pytest
   ```

6. **Verify installation:**
   ```bash
   # Run health check
   python -c "from src.core.config import settings; print(f'Config loaded: {settings.debug}')"

   # Start server
   uvicorn src.main:app --reload
   ```

### IDE Setup

#### VS Code

Recommended extensions:
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Black Formatter (ms-python.black-formatter)
- isort (ms-python.isort)

Create `.vscode/settings.json`:
```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length=100"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"]
}
```

#### PyCharm

1. Open project directory
2. Settings → Project → Python Interpreter → Add → Existing Environment
3. Select `.venv/bin/python`
4. Settings → Tools → Black → Enable
5. Settings → Tools → External Tools → Add isort

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
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=src --cov-report=html --cov-report=term

# Run specific test file
pytest tests/unit/test_extraction_service.py

# Run specific test
pytest tests/unit/test_extraction_service.py::test_extract_concepts

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run with pytest watch (auto-rerun on changes)
ptw
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

### Formatting

We use **Black** for code formatting:

```bash
# Format all code
black src/ tests/

# Check formatting without making changes
black --check src/ tests/

# Format specific file
black src/services/session_service.py
```

Configuration in `pyproject.toml`:
```toml
[tool.black]
line-length = 100
target-version = ['py311']
```

### Import Sorting

We use **isort** for import organization:

```bash
# Sort all imports
isort src/ tests/

# Check without making changes
isort --check-only src/ tests/

# Sort specific file
isort src/services/session_service.py
```

Configuration in `pyproject.toml`:
```toml
[tool.isort]
profile = "black"
line_length = 100
```

### Type Checking

We use **mypy** for static type checking:

```bash
# Type check all code
mypy src/

# Type check specific file
mypy src/services/session_service.py

# Type check with strict mode
mypy --strict src/
```

### Linting

We use **pylint** for code quality:

```bash
# Lint all code
pylint src/

# Lint specific file
pylint src/services/session_service.py

# Lint with specific configuration
pylint --rcfile=.pylintrc src/
```

### Pre-commit Hooks

Install pre-commit hooks for automatic checks:

```bash
pip install pre-commit
pre-commit install
```

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.1
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

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

### Adding a New Scoring Metric

1. **Create scorer in `src/services/scoring/`:**
   ```python
   # src/services/scoring/my_metric.py
   from .base import ScoringMetric

   class MyMetric(ScoringMetric):
       def __init__(self, weight: float = 1.0):
           super().__init__(name="my_metric", weight=weight)

       async def calculate(self, graph: KnowledgeGraph) -> float:
           # Calculate metric based on graph state
           return 0.5
   ```

2. **Register in arbitration service:**
   ```python
   # src/services/scoring/arbitration.py
   from .my_metric import MyMetric

   class ScoringArbitrator:
       def __init__(self):
           self.metrics = [
               CoverageMetric(),
               DepthMetric(),
               SaturationMetric(),
               MyMetric(weight=0.5),  # Add new metric
           ]
   ```

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

Methodology schemas define the ontology (node types, edge types, valid connections) and are stored as YAML files in `config/methodologies/`. See [ADR-007](../adr/007-yaml-based-methodology-schema.md) for details.

1. **Create YAML schema in `config/methodologies/`:**
   ```yaml
   # config/methodologies/my_methodology.yaml
   name: my_methodology
   version: "1.0"
   description: "Brief description of the methodology"

   node_types:
     - name: concept
       description: "Core concept or idea"
       examples:
         - "example 1"
         - "example 2"

   edge_types:
     - name: relates_to
       description: "Semantic relationship"

   valid_connections:
     relates_to:
       - [concept, concept]  # concept can relate to concept
   ```

2. **Load schema in services:**
   ```python
   from src.core.schema_loader import load_methodology

   # In service __init__
   def __init__(self, methodology: str = "my_methodology"):
       self.schema = load_methodology(methodology)

   # Validate against schema
   if not self.schema.is_valid_node_type(node_type):
       log.warning("invalid_node_type", type=node_type)
   ```

3. **Schema is automatically used for:**
   - Extraction validation (invalid types/connections rejected)
   - LLM prompt generation (node/edge descriptions)
   - Graph constraints enforcement

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

- **Repository Pattern**: Data access abstraction
- **Service Layer**: Business logic encapsulation
- **Dependency Injection**: FastAPI Depends for testability
- **Factory Pattern**: Service creation with dependencies
- **Strategy Pattern**: Scoring metrics and question strategies

### Directory Structure

```
src/
├── api/                    # HTTP interface
│   ├── routes/            # Route handlers
│   └── schemas.py         # Request/response models
├── core/                  # Configuration, logging
├── domain/                # Business entities
│   └── models/
├── llm/                   # LLM integration
│   ├── client.py
│   └── prompts/
├── persistence/           # Data persistence
│   ├── database.py
│   ├── migrations/
│   └── repositories/
└── services/              # Business logic
    ├── scoring/
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
   pytest
   black --check src/ tests/
   isort --check-only src/ tests/
   mypy src/
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
# Solution: Install in editable mode
pip install -e .
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
