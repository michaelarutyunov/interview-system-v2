# Interview System v2

Adaptive interview system for qualitative consumer research using LLM-powered knowledge extraction and graph-based analysis.

## Features

- **Adaptive Interviewing**: AI-powered questioning that adapts based on respondent answers using two-tier scoring
- **Knowledge Graph Extraction**: Automatic extraction of concepts and relationships from responses
- **Multi-Dimensional Scoring**: Coverage, depth, saturation, engagement, and strategy diversity metrics
- **Dynamic Strategy Selection**: 9 strategies (deepen, broaden, bridge, synthesis, contrast, ease, etc.) selected via weighted scoring
- **Phase-Based Modulation**: Exploratory → focused → closing phases with adaptive strategy preferences
- **LLM Qualitative Signals**: Semantic understanding of respondent engagement, reasoning quality, and knowledge state
- **MEC Chain Depth Analysis**: BFS traversal for accurate depth measurement in Means-End Chain methodology
- **Synthetic Respondents**: Test your interviews with AI-generated personas
- **Multiple Export Formats**: Export sessions as JSON, Markdown, or CSV
- **Demo UI**: Interactive Streamlit interface for conducting interviews
- **RESTful API**: Complete API for programmatic access

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Anthropic API key (for Claude LLM)
- [uv](https://github.com/astral-sh/uv) (recommended Python package manager)
- Git

### Installation

```bash
# Clone the repository
git clone <repository-url>
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

# Run pyright (type checking)
uv run pyright src/
```

## Project Structure

```
interview-system-v2/
├── src/
│   ├── api/
│   │   ├── routes/          # API endpoints (sessions, synthetic, concepts, health)
│   │   └── schemas.py       # Pydantic models for request/response
│   ├── core/
│   │   ├── config.py        # Configuration settings (YAML-based)
│   │   ├── exceptions.py    # Custom exceptions
│   │   └── logging.py       # Structured logging setup
│   ├── domain/
│   │   └── models/          # Domain models (Session, Utterance, Extraction, Graph, Focus)
│   ├── llm/
│   │   ├── client.py        # Anthropic API client (with light/heavy variants)
│   │   └── prompts/         # Prompt templates (extraction, questioning, synthetic, qualitative)
│   ├── persistence/
│   │   ├── database.py      # Database connection management
│   │   ├── migrations/      # Database schema migrations
│   │   └── repositories/    # Data access layer (Session, Graph, Utterance)
│   ├── services/
│   │   ├── extraction_service.py  # Concept extraction logic
│   │   ├── graph_service.py       # Knowledge graph management
│   │   ├── question_service.py    # Question generation
│   │   ├── scoring/               # Two-tier scoring system
│   │   │   ├── tier1/            # Hard constraint scorers (vetoes)
│   │   │   ├── tier2/            # Weighted additive scorers
│   │   │   ├── two_tier/         # Scoring engine orchestration
│   │   │   ├── graph_utils.py    # Graph analysis utilities
│   │   │   ├── signal_helpers.py # Signal extraction helpers
│   │   │   └── llm_signals.py    # LLM qualitative signal extraction
│   │   ├── strategy_service.py    # Strategy selection logic
│   │   ├── session_service.py     # Session orchestration
│   │   ├── turn_pipeline/         # Pipeline architecture for turn processing
│   │   ├── synthetic_service.py   # Synthetic respondent generation
│   │   └── export_service.py      # Export functionality
│   └── main.py              # FastAPI application entry point
├── tests/
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
├── ui/
│   └── streamlit_app.py    # Demo UI
├── config/
│   ├── scoring.yaml        # Scoring system configuration
│   ├── interview_config.yaml # Interview phases and settings
│   ├── concepts/           # Concept configuration YAML files
│   └── methodologies/      # Methodology schema definitions (node/edge types)
├── docs/                   # Documentation
├── .env.example            # Environment template
├── pyproject.toml          # Project configuration
└── README.md
```

## API Documentation Reference

For detailed API documentation, see [docs/API.md](docs/API.md).

Quick reference:

- **Sessions**: `POST /sessions` - Create new interview session
- **Start**: `POST /sessions/{id}/start` - Start session and get opening question
- **Turn**: `POST /sessions/{id}/turns` - Submit respondent response
- **Export**: `GET /sessions/{id}/export` - Export session data
- **Scoring**: `GET /sessions/{id}/scoring/{turn}` - View scoring details for a turn
- **Graph**: `GET /sessions/{id}/graph` - Get knowledge graph nodes and edges
- **Synthetic**: `POST /synthetic/respond` - Generate synthetic response
- **Concepts**: `GET /concepts` - List available concepts

### API Usage Example

```python
import httpx

async def conduct_interview():
    base_url = "http://localhost:8000"

    # Create session
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/sessions",
            json={
                "methodology": "means_end_chain",
                "concept_id": "yogurt_consumption",
                "mode": "test",
                "config": {"concept_name": "Yogurt Consumption"}
            }
        )
        session = response.json()
        session_id = session["id"]

        # Start session
        response = await client.post(f"{base_url}/sessions/{session_id}/start")
        start_data = response.json()
        question = start_data["opening_question"]

        # Process turns
        while True:
            print(f"Question: {question}")

            # Get user input (in real app, this would be from UI)
            user_text = input("Your answer: ")

            # Submit turn
            response = await client.post(
                f"{base_url}/sessions/{session_id}/turns",
                json={"text": user_text}
            )
            result = response.json()

            print(f"Extracted {len(result['extracted']['concepts'])} concepts")
            print(f"Coverage: {result['scoring']['coverage']:.2%}")
            print(f"Strategy: {result['strategy_selected']}")

            if not result["should_continue"]:
                print("Interview complete!")
                break

            question = result["next_question"]

        # Export session
        response = await client.get(
            f"{base_url}/sessions/{session_id}/export",
            params={"format": "markdown"}
        )
        print(response.text)
```

## Usage Examples

### Using the Demo UI

1. Start the backend server: `uv run uvicorn src.main:app --reload`
2. Start the UI: `uv run streamlit run ui/streamlit_app.py`
3. Open http://localhost:8501
4. Create a new session or load existing one
5. Conduct interview through chat interface
6. View knowledge graph visualization
7. View scoring details for each turn
8. Export results when complete

### Using the Synthetic Respondent

```bash
# Generate a single synthetic response
curl -X POST http://localhost:8000/synthetic/respond \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What do you look for when buying yogurt?",
    "session_id": "test-session-123",
    "persona": "health_conscious"
  }'

# List available personas
curl http://localhost:8000/synthetic/personas
```

### Exporting Session Data

```bash
# Export as JSON
curl http://localhost:8000/sessions/{session_id}/export?format=json \
  -o session_export.json

# Export as Markdown
curl http://localhost:8000/sessions/{session_id}/export?format=markdown \
  -o session_export.md

# Export as CSV
curl http://localhost:8000/sessions/{session_id}/export?format=csv \
  -o session_export.csv
```

## Development

For development guidelines, see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

Key development commands:

```bash
# Format code
uv run ruff format .

# Run linting (with auto-fix)
uv run ruff check . --fix

# Type checking
uv run pyright src/

# Run specific test category
uv run pytest tests/unit/
uv run pytest tests/integration/

# Run tests with coverage
uv run pytest --cov=src --cov-report=html
```

## Architecture Overview

The system uses a layered architecture with pipeline pattern for turn processing:

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Layer (FastAPI)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Turn Pipeline Architecture                      │ │
│  │  1. ContextLoading → 2. Extraction → 3. GraphUpdate        │ │
│  │  4. StateComputation → 5. StrategySelection → 6. QuestionGen │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Two-Tier Scoring Engine                         │ │
│  │  Tier 1: Hard Constraints (Veto Checks)                     │ │
│  │  Tier 2: Weighted Additive Scoring                          │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│                        Service Layer                             │
│  • SessionService (orchestration)                                │
│  • ExtractionService (concept extraction)                        │
│  • QuestionService (question generation)                         │
│  • GraphService (knowledge graph)                                │
│  • StrategyService (strategy selection)                          │
│  • ExportService (data export)                                   │
├─────────────────────────────────────────────────────────────────┤
│                        Domain Layer                              │
│  • Session, Utterance, Extraction, GraphState, Focus            │
├─────────────────────────────────────────────────────────────────┤
│                       Persistence Layer                          │
│  • SQLite + aiosqlite                                            │
│  • Repository pattern (Session, Graph, Utterance)               │
├─────────────────────────────────────────────────────────────────┤
│                        LLM Integration                           │
│  • Anthropic Claude (Haiku for light tasks, Sonnet for complex) │
│  • Qualitative signal extraction                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

- **Turn Pipeline**: Modular stages for processing each respondent turn
- **Two-Tier Scoring**: Hard constraints (vetoes) + weighted additive scoring
- **Strategy Selection**: Dynamic selection from 9 strategies based on graph state
- **Qualitative Signals**: LLM-based extraction of engagement, reasoning, and knowledge state
- **MEC Chain Depth**: BFS traversal for accurate depth measurement

### Configuration-Driven Design

The system is heavily configuration-driven via YAML:

- `config/scoring.yaml` - Strategies, scorers, phase profiles, weights
- `config/interview_config.yaml` - Phases, turn limits, thresholds
- `config/methodologies/*.yaml` - Node/edge types per methodology
- `config/concepts/*.yaml` - Element definitions per concept

## Scoring System

For detailed scoring system documentation, see [src/services/scoring/README_scoring.md](src/services/scoring/README_scoring.md).

**Key Features:**
- **Tier 1 (Vetoes)**: KnowledgeCeilingScorer, ElementExhaustedScorer, RecentRedundancyScorer
- **Tier 2 (Weighted)**: CoverageGapScorer, AmbiguityScorer, DepthBreadthBalanceScorer, EngagementScorer, StrategyDiversityScorer, NoveltyScorer, ClusterSaturationScorer, ContrastOpportunityScorer, PeripheralReadinessScorer
- **Phase Multipliers**: Adaptive strategy preferences per interview stage
- **LLM Qualitative Signals**: 6 signal types for nuanced understanding

## Methodologies

The system supports multiple qualitative research methodologies defined in YAML:

- **Means-End Chain**: Explores attribute → consequence → value chains
- **Laddering**: Deepens understanding through progressive questioning
- **Critical Incident**: Examines specific experiences and behaviors

Methodology schemas (node types, edge types, and validation rules) are defined in `config/methodologies/` (see [ADR-007](docs/adr/007-yaml-based-methodology-schema.md)).

## Documentation

- [PRD](PRD.md) - Product Requirements Document
- [Engineering Guide](ENGINEERING_GUIDE.md) - Technical specifications
- [API Documentation](docs/API.md) - Complete API reference
- [Development Guide](docs/DEVELOPMENT.md) - Development setup and guidelines
- [Scoring Architecture](src/services/scoring/README_scoring.md) - Scoring system details
- [ADR Index](docs/adr/README.md) - Architecture Decision Records

## Architecture Decision Records

Key ADRs:
- [ADR-004](docs/adr/004-two-tier-scoring-system.md) - Two-tier scoring system
- [ADR-006](docs/adr/006-scoring-architecture.md) - Enhanced scoring architecture
- [ADR-007](docs/adr/007-yaml-based-methodology-schema.md) - YAML-based methodology schemas
- [ADR-008](docs/adr/008-internal-api-boundaries-pipeline-pattern.md) - Pipeline pattern for turn processing

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for guidelines.

## Support

For issues and questions, please use the GitHub issue tracker.
