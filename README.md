# Interview System v2

Adaptive interview system for qualitative consumer research using LLM-powered knowledge extraction, signal pools, and graph-based analysis with intelligent backtracking.

## Features

### Core Capabilities
- **Adaptive Interviewing**: AI-powered questioning that adapts based on respondent answers using methodology-based signal detection
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
- **Graph-Driven**: Deprecated - use Exploratory mode

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
│   ├── api/
│   │   ├── routes/          # API endpoints (sessions, synthetic, simulation, concepts, health)
│   │   └── schemas.py       # Pydantic models for request/response
│   ├── core/
│   │   ├── config_loader.py # YAML configuration loader
│   │   ├── concept_loader.py # Concept configuration loader
│   │   ├── persona_loader.py # Persona configuration loader
│   │   ├── schema_loader.py # Methodology schema loader
│   │   ├── exceptions.py    # Custom exceptions
│   │   └── logging.py       # Structured logging setup
│   ├── domain/
│   │   └── models/          # Domain models (Session, Utterance, Extraction, Graph, NodeState)
│   ├── llm/
│   │   ├── client.py        # Anthropic API client (with light/heavy variants)
│   │   └── prompts/         # Prompt templates (extraction, questioning, synthetic, qualitative)
│   ├── methodologies/
│   │   ├── config/          # YAML methodology configurations (MEC, JTBD, CIM, etc.)
│   │   ├── registry.py      # Methodology registry and signal detector factory
│   │   ├── scoring.py       # Strategy scoring with phase weights
│   │   ├── signals/         # Signal detectors (graph, llm, temporal, meta, technique)
│   │   └── techniques/      # Question technique templates
│   ├── persistence/
│   │   ├── database.py      # Database connection management
│   │   ├── migrations/      # Database schema migrations
│   │   └── repositories/    # Data access layer (Session, Graph, Utterance)
│   ├── services/
│   │   ├── extraction_service.py     # Concept extraction logic
│   │   ├── focus_selection_service.py # Focus node selection
│   │   ├── graph_service.py          # Knowledge graph management
│   │   ├── methodology_strategy_service.py # Strategy selection with signal pools
│   │   ├── node_state_tracker.py     # Node state tracking for exhaustion detection
│   │   ├── question_service.py       # Question generation
│   │   ├── session_service.py        # Session orchestration
│   │   ├── simulation_service.py     # AI-to-AI simulation testing
│   │   ├── turn_pipeline/            # Pipeline architecture for turn processing
│   │   │   ├── context.py            # Pipeline context
│   │   │   └── stages/               # Individual pipeline stages
│   │   └── export_service.py         # Export functionality
│   └── main.py              # FastAPI application entry point
├── tests/
│   ├── calibration/         # Signal weight calibration tests
│   ├── integration/         # Integration tests (E2E, phase-based, joint scoring)
│   ├── methodology/signals/ # Signal detection tests
│   ├── performance/         # Performance tests (node exhaustion)
│   ├── synthetic/           # Synthetic interview tests
│   └── unit/                # Unit tests
├── ui/
│   ├── components/          # Streamlit UI components
│   └── streamlit_app.py     # Demo UI
├── config/
│   ├── concepts/            # Concept configuration YAML files
│   ├── methodologies/       # Methodology YAML configurations
│   └── personas/            # Persona configuration YAML files
├── docs/                    # Documentation (ADR, system design, data flows, API)
├── synthetic_interviews/    # Generated synthetic interview outputs
├── .env.example             # Environment template
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
- **Simulation**: `POST /simulation/run` - Run AI-to-AI simulation interview
- **Concepts**: `GET /concepts` - List available concepts
- **Personas**: `GET /personas` - List available personas

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
                "concept_id": "oat_milk_v2",
                "mode": "exploratory",
                "config": {"concept_name": "Oat Milk"}
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

            print(f"Strategy: {result['strategy_selected']}")
            print(f"Phase: {result.get('phase', 'unknown')}")
            print(f"Signals: {result.get('signals', {})}")

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

### Using Synthetic Respondents

```bash
# Generate a single synthetic response
curl -X POST http://localhost:8000/synthetic/respond \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What do you look for when buying oat milk?",
    "session_id": "test-session-123",
    "persona_id": "health_conscious"
  }'

# List available personas
curl http://localhost:8000/personas
```

### Running AI-to-AI Simulations

```bash
# Run a simulation interview
curl -X POST http://localhost:8000/simulation/run \
  -H "Content-Type: application/json" \
  -d '{
    "concept_id": "oat_milk_v2",
    "methodology": "means_end_chain",
    "persona_id": "health_conscious",
    "max_turns": 10
  }'

# Run simulation with custom config
curl -X POST http://localhost:8000/simulation/run \
  -H "Content-Type: application/json" \
  -d '{
    "concept_id": "oat_milk_v2",
    "methodology": "means_end_chain",
    "persona_id": "price_sensitive",
    "max_turns": 15,
    "mode": "exploratory"
  }'
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

# Run specific test category
uv run pytest tests/unit/
uv run pytest tests/integration/
uv run pytest tests/calibration/

# Run tests with coverage
uv run pytest --cov=src --cov-report=html
```

## Architecture Overview

The system uses a layered architecture with pipeline pattern for turn processing and signal pools for decision-making:

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Layer (FastAPI)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│ │              Turn Pipeline Architecture (10 stages)            │ │
│  │  1. ContextLoading → 2. UtteranceSaving → 3. Extraction     │ │
│  │  4. GraphUpdate → 5. StateComputation → 6. StrategySelection│ │
│  │  7. Continuation → 8. QuestionGeneration → 9. ResponseSaving │ │
│  │  10. ScoringPersistence                                       │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │         Methodology-Based Strategy Selection                  │ │
│  │  • Signal Pools: Graph, LLM, Temporal, Meta                  │ │
│  │  • Phase Weights: Early/Mid/Late multipliers                  │ │
│  │  • Node Exhaustion Detection + Backtracking (D1)             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│                        Service Layer                             │
│  • SessionService (orchestration)                                │
│  • MethodologyStrategyService (strategy + focus selection)        │
│  • ExtractionService (concept extraction)                        │
│  • QuestionService (question generation)                         │
│  • NodeStateTracker (node state tracking)                        │
│  • SimulationService (AI-to-AI testing)                          │
│  • ExportService (data export)                                   │
├─────────────────────────────────────────────────────────────────┤
│                        Domain Layer                              │
│  • Session, Utterance, Extraction, GraphState, NodeState        │
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

- **Turn Pipeline**: 10 modular stages for processing each respondent turn
- **Signal Pools**: 5 signal pools (Graph, LLM, Temporal, Meta, Technique) for comprehensive context
- **MethodologyStrategyService**: Strategy selection using YAML configs and signal detection
- **NodeStateTracker**: Tracks node visitation, yields, and exhaustion for backtracking
- **Phase-Based Weights & Bonuses**: Interview phase multipliers (multiplicative) and bonuses (additive) adjust strategy preferences
- **D1 Architecture**: Joint strategy-node scoring with node exhaustion awareness

### Configuration-Driven Design

The system is heavily configuration-driven via YAML:

- `config/methodologies/*.yaml` - Methodology configs with signals, strategies, techniques, phases
- `config/concepts/*.yaml` - Concept definitions with element mappings
- `config/personas/*.yaml` - Persona definitions for synthetic interviews

Example methodology config structure:
```yaml
name: means_end_chain
display_name: Means-End Chain
description: Explores attribute → consequence → value chains

signals:
  graph.max_depth:
    class: graph.depth.GraphMaxDepthSignal
  llm.response_depth:
    class: llm.depth.ResponseDepthSignal
  meta.interview.phase:
    class: meta.interview_phase.InterviewPhaseSignal

strategies:
  deepen:
    signal_weights:
      graph.max_depth.low: 2.0
      llm.response_depth.surface: 1.5
    focus_preference: deep
    technique: deepen

phases:
  early:
    signal_weights:    # Multiplicative weights
      deepen: 1.5
      clarify: 1.2
      reflect: 0.8
    phase_bonuses:     # Additive bonuses
      broaden: 0.2
  mid:
    signal_weights:
      deepen: 1.0
      clarify: 1.0
      reflect: 1.0
  late:
    signal_weights:
      deepen: 0.5
      clarify: 0.8
      reflect: 1.8
    phase_bonuses:
      synthesize: 0.3
      validate: 0.2
```

## Signal Pools Architecture

The system uses five signal pools for comprehensive context awareness:

| Pool | Namespace | Examples | Purpose |
|------|-----------|----------|---------|
| **Graph (Global)** | `graph.*` | node_count, max_depth, orphan_count, chain_completion | Knowledge graph state |
| **Graph (Node)** | `graph.node.*` | exhausted, exhaustion_score, focus_streak, recency_score | Per-node state |
| **LLM** | `llm.*` | response_depth, sentiment, uncertainty, hedging_language | Semantic understanding |
| **Temporal** | `temporal.*` | strategy_repetition_count, turns_since_strategy_change | History tracking |
| **Meta (Global)** | `meta.*` | interview.phase, interview_progress | Composite signals |
| **Meta (Node)** | `meta.node.*` | opportunity (exhausted/probe_deeper/fresh) | Node opportunity |
| **Technique (Node)** | `technique.node.*` | strategy_repetition (consecutive same strategy on node) | Per-node technique |

For details, see [ADR-014: Signal Pools Architecture](docs/adr/ADR-014-signal-pools-architecture.md).

## Node Exhaustion Detection

The D1 architecture implements intelligent backtracking when nodes stop yielding new information:

- **Node State Tracking**: Tracks visitation count, consecutive visits, yield history
- **Exhaustion Detection**: Multiple signals detect exhausted nodes (yield stagnation, focus streak, strategy repetition)
- **Backtracking**: Automatically shifts focus to fresh nodes with better opportunity scores
- **Opportunity Scoring**: Ranks nodes by freshness, orphan status, and recent yield

For details, see [ADR-015: Node Exhaustion Backtracking](docs/adr/ADR-015-node-exhaustion-backtracking.md).

## Methodologies

The system supports multiple qualitative research methodologies defined in YAML:

- **Means-End Chain**: Explores attribute → consequence → value chains
- **Jobs to Be Done**: Explores functional and emotional jobs
- **Critical Incident**: Examines specific experiences and behaviors
- **Customer Journey Mapping**: Maps customer experience across touchpoints
- **Repertory Grid**: Elicits personal constructs

Methodology configurations are in `config/methodologies/` and include:
- Signal detectors (graph, llm, temporal, meta, technique)
- Strategies with signal weights
- Question techniques
- Phase-based weights (multiplicative) and bonuses (additive)
- Node/edge type definitions

## Documentation

- [SYSTEM_DESIGN](docs/SYSTEM_DESIGN.md) - Narrative system architecture
- [API Documentation](docs/API.md) - Complete API reference
- [Data Flow Paths](docs/data_flow_paths.md) - Critical data flow diagrams
- [Pipeline Contracts](docs/pipeline_contracts.md) - Stage read/write specifications
- [Development Guide](docs/DEVELOPMENT.md) - Development setup and guidelines
- [Synthetic Personas](docs/synthetic_personas.md) - AI persona system
- [ADR Index](docs/adr/README.md) - Architecture Decision Records

## Architecture Decision Records

Key ADRs:
- [ADR-008](docs/adr/008-internal-api-boundaries-pipeline-pattern.md) - Pipeline pattern for turn processing
- [ADR-010](docs/adr/010-formalize-pipeline-contracts-strengthen-data-models.md) - Pipeline contracts formalization
- [ADR-014](docs/adr/ADR-014-signal-pools-architecture.md) - Signal pools architecture
- [ADR-015](docs/adr/ADR-015-node-exhaustion-backtracking.md) - Node exhaustion detection and backtracking

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for guidelines.

## Support

For issues and questions, please use the GitHub issue tracker.
