# Interview System v2

Adaptive interview system for qualitative consumer research using LLM-powered knowledge extraction and graph-based analysis.

## Features

- **Adaptive Interviewing**: AI-powered questioning that adapts based on respondent answers
- **Knowledge Graph Extraction**: Automatic extraction of concepts and relationships from responses
- **Multi-Dimensional Scoring**: Coverage, depth, and saturation metrics for interview quality
- **Strategy Selection**: Dynamic question strategy selection (broaden, deepen, bridge, pivot)
- **Synthetic Respondents**: Test your interviews with AI-generated personas
- **Multiple Export Formats**: Export sessions as JSON, Markdown, or CSV
- **Demo UI**: Interactive Streamlit interface for conducting interviews
- **RESTful API**: Complete API for programmatic access

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Anthropic API key (for Claude LLM)
- Git

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd interview-system-v2

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install dependencies
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
uvicorn src.main:app --reload
```

The API will be available at `http://localhost:8000`

API documentation (Swagger UI): `http://localhost:8000/docs`

### Start the Demo UI (Optional)

In a new terminal:

```bash
streamlit run ui/streamlit_app.py
```

The UI will be available at `http://localhost:8501`

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_session_service.py

# Run with verbose output
pytest -v
```

## Project Structure

```
interview-system-v2/
├── src/
│   ├── api/
│   │   ├── routes/          # API endpoints (sessions, synthetic, concepts, health)
│   │   └── schemas.py       # Pydantic models for request/response
│   ├── core/
│   │   ├── config.py        # Configuration settings
│   │   ├── exceptions.py    # Custom exceptions
│   │   └── logging.py       # Structured logging setup
│   ├── domain/
│   │   └── models/          # Domain models (Session, Utterance, Extraction, Graph)
│   ├── llm/
│   │   ├── client.py        # Anthropic API client
│   │   └── prompts/         # Prompt templates for extraction, questioning, synthetic
│   ├── persistence/
│   │   ├── database.py      # Database connection management
│   │   ├── migrations/      # Database schema migrations
│   │   └── repositories/    # Data access layer (Session, Graph)
│   ├── services/
│   │   ├── extraction_service.py  # Concept extraction logic
│   │   ├── graph_service.py       # Knowledge graph management
│   │   ├── question_service.py    # Question generation
│   │   ├── scoring/               # Scoring algorithms (coverage, depth, saturation)
│   │   ├── strategy_service.py    # Strategy selection logic
│   │   ├── session_service.py     # Session orchestration
│   │   ├── synthetic_service.py   # Synthetic respondent generation
│   │   └── export_service.py      # Export functionality
│   └── main.py              # FastAPI application entry point
├── tests/
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
├── ui/
│   └── streamlit_app.py    # Demo UI
├── config/
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

1. Start the backend server: `uvicorn src.main:app --reload`
2. Start the UI: `streamlit run ui/streamlit_app.py`
3. Open http://localhost:8501
4. Create a new session or load existing one
5. Conduct interview through chat interface
6. View knowledge graph visualization
7. Export results when complete

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
black src/ tests/
isort src/ tests/

# Type checking
mypy src/

# Run linting
pylint src/

# Run specific test category
pytest tests/unit/
pytest tests/integration/
```

## Architecture Overview

The system uses a layered architecture:

1. **API Layer**: FastAPI routes handling HTTP requests/responses
2. **Service Layer**: Business logic (extraction, questioning, scoring, strategy)
3. **Domain Layer**: Core models (Session, Utterance, KnowledgeGraph)
4. **Persistence Layer**: Database operations using SQLite
5. **LLM Integration**: Anthropic Claude for AI-powered features

### Key Components

- **ExtractionService**: Extracts concepts and relationships from text
- **QuestionService**: Generates contextually relevant questions
- **Scoring System**: Multi-dimensional metrics (coverage, depth, saturation)
- **StrategyService**: Selects questioning strategy based on scores
- **SessionService**: Orchestrates the entire interview flow
- **SyntheticService**: Generates realistic synthetic responses
- **ExportService**: Formats session data for export

## Methodologies

The system supports multiple qualitative research methodologies:

- **Means-End Chain**: Explores attribute → consequence → value chains
- **Laddering**: Deepens understanding through progressive questioning
- **Critical Incident**: Examines specific experiences and behaviors

Methodology schemas (node types, edge types, and validation rules) are defined in `config/methodologies/` as YAML files (see [ADR-007](docs/adr/007-yaml-based-methodology-schema.md)). Concepts are configured via YAML files in `config/concepts/`.

## Documentation

- [PRD](PRD.md) - Product Requirements Document
- [Engineering Guide](ENGINEERING_GUIDE.md) - Technical specifications
- [API Documentation](docs/API.md) - Complete API reference
- [Development Guide](docs/DEVELOPMENT.md) - Development setup and guidelines

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for guidelines.

## Support

For issues and questions, please use the GitHub issue tracker.
