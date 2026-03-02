# Interview System v2

Adaptive interview system for qualitative consumer research using LLM-powered knowledge extraction, signal pools, and graph-based analysis with intelligent backtracking.

## Features

### Core Capabilities
- **Adaptive Interviewing**: Interview engine that adapts based on respondent answers using methodology-based signal detection
- **Knowledge Graph Extraction**: Automatic extraction of concepts and relationships from responses
- **Node Exhaustion Detection**: Intelligent backtracking when nodes stop yielding new information (D1 architecture)
- **Signal Pools Architecture**: Four signal pools (Graph, LLM, Temporal, Meta) for comprehensive context awareness
- **Phase-Based Strategy Selection**: Early/mid/late interview phases with adaptive strategy preferences via YAML configs
- **Synthetic Respondents**: Test interviews with AI-generated personas for rapid iteration

### Strategy System
- **9 Questioning Strategies**: deepen, clarify, reflect, elaborate, probe, connect, validate, synthesize, bridge
- **Dynamic Scoring**: Strategy selection via YAML-configured signal weights
- **Phase Weights**: Interview phase multipliers (early/mid/late) adjust strategy preferences
- **Focus Selection**: Intelligent node selection based on strategy preferences and node state

### Interview Modes
- **Exploratory** (default): Pure exploration without coverage pressure

### Supported Methodologies
- **Means-End Chain**: Explores attribute → consequence → value chains
- **Jobs to Be Done**: Explores functional and emotional jobs
- **Critical Incident**: Examines specific experiences and behaviors

### Analysis & Export
- **Multiple Export Formats**: JSON, Markdown, CSV
- **Session Scoring**: Turn-by-turn strategy selection and signal tracking
- **Knowledge Graph Visualization**: Real-time graph state in UI

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Anthropic API key (for Claude LLM)
- [uv](https://github.com/astral-sh/uv) (recommended Python package manager)
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/michaelarutyunov/interview-system-v2.git
cd interview-system-v2

# Install dependencies with uv (recommended)
uv sync

# Or with pip
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env

# Edit .env with your API key
# ANTHROPIC_API_KEY=your-actual-api-key-here
```

### Configuration

Edit the `.env` file with your settings:

```env
ANTHROPIC_API_KEY=your-api-key-here
LLM_MODEL=claude-sonnet-4-20250514
DATABASE_PATH=data/interview.db
DEBUG=true
```

## Running the System

### Start the Backend Server

```bash
uv run uvicorn src.main:app --reload
```

The API will be available at `http://localhost:8000`

API documentation (Swagger UI): `http://localhost:8000/docs`

### Start the Demo UI (Optional)

In a new terminal:

```bash
uv run streamlit run ui/streamlit_app.py
```

The UI will be available at `http://localhost:8501`

### Run Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_session_service.py

# Run with verbose output
uv run pytest -v
```

### Run Linters

```bash
# Run ruff (linting + formatting)
uv run ruff check . --fix

# Run ruff format
uv run ruff format .
```

## Project Structure

```
interview-system-v2/
├── src/
│   ├── api/                 # FastAPI routes and schemas
│   ├── core/                # Configuration, logging, exceptions
│   ├── domain/models/       # Pydantic models (Session, Utterance, Graph)
│   ├── llm/                 # Anthropic client and prompt templates
│   ├── methodologies/       # YAML configs, signal detectors, scoring
│   ├── persistence/         # Database (SQLite) and repositories
│   ├── services/            # Business logic and turn pipeline stages
│   └── main.py              # FastAPI entry point
├── tests/                   # Unit, integration, calibration tests
├── ui/                      # Streamlit demo interface
├── config/                  # YAML configs (methodologies, concepts, personas)
├── docs/                    # Architecture docs and ADRs
└── scripts/                 # Simulation and analysis scripts
```

## API Quick Reference

See [docs/API.md](docs/API.md) for complete documentation.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sessions` | POST | Create interview session |
| `/sessions/{id}/start` | POST | Start and get opening question |
| `/sessions/{id}/turns` | POST | Submit respondent response |
| `/sessions/{id}/export` | GET | Export session (JSON/Markdown/CSV) |
| `/sessions/{id}/graph` | GET | Get knowledge graph state |
| `/simulation/run` | POST | Run AI-to-AI simulation |
| `/concepts` | GET | List available concepts |
| `/personas` | GET | List synthetic personas |

Interactive docs: `http://localhost:8000/docs` (when server is running)

## Usage Examples

### Run AI-to-AI Simulation

```bash
# Quick simulation with default settings
uv run python scripts/run_simulation.py oat_milk_v2 health_conscious 10

# Output: synthetic_interviews/TIMESTAMP_oat_milk_v2_health_conscious.json
```

### Using the Demo UI

```bash
# Terminal 1: Start backend
uv run uvicorn src.main:app --reload

# Terminal 2: Start UI
uv run streamlit run ui/streamlit_app.py

# Open http://localhost:8501
```

### Export Session Data

```bash
# Export as JSON, Markdown, or CSV
curl http://localhost:8000/sessions/{session_id}/export?format=markdown
```

## Development

For development guidelines, see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

Key development commands:

```bash
# Format code
uv run ruff format .

# Run linting (with auto-fix)
uv run ruff check . --fix

# Run specific test category
uv run pytest tests/unit/
uv run pytest tests/integration/
uv run pytest tests/calibration/

# Run tests with coverage
uv run pytest --cov=src --cov-report=html
```

## Architecture Overview

The system uses a layered architecture with a 12-stage pipeline for turn processing:

```
API Layer (FastAPI)
       ↓
Turn Pipeline (12 stages)
  1. ContextLoading → 2. UtteranceSaving → 2.5. SRLPreprocessing [opt]
  3. Extraction → 4. GraphUpdate → 4.5. SlotDiscovery [opt]
  5. StateComputation → 6. StrategySelection → 7. Continuation
  8. QuestionGeneration → 9. ResponseSaving → 10. ScoringPersistence
       ↓
Service Layer (Session, Strategy, Extraction, Graph, Simulation)
       ↓
Persistence Layer (SQLite + aiosqlite)
```

### Key Concepts

- **Signal Pools**: Graph, LLM, Temporal, Meta, and Technique signals feed into strategy scoring
- **Node Exhaustion**: Intelligent backtracking when nodes stop yielding new information
- **Phase-Based Adaptation**: Early/mid/late interview phases with different strategy preferences
- **Configuration-Driven**: All methodologies, signals, and strategies defined in YAML

See [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md) for detailed architecture documentation.

## Documentation

| Document | Purpose |
|----------|---------|
| [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md) | System architecture |
| [docs/API.md](docs/API.md) | API reference |
| [docs/data_flow_paths.md](docs/data_flow_paths.md) | Data flow diagrams |
| [docs/pipeline_contracts.md](docs/pipeline_contracts.md) | Pipeline stage contracts |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Development setup |

## License

MIT License
