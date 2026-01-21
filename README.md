# Interview System v2

Adaptive interview system for qualitative consumer research.

## Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env
# Edit .env with your API key

# Run tests
pytest

# Start server
uvicorn src.main:app --reload
```

## Demo UI

The demo UI provides a visual interface for conducting interviews.

### Running the UI

1. Start the FastAPI backend:
```bash
uvicorn src.main:app --reload
```

2. In a new terminal, start the Streamlit UI:
```bash
streamlit run ui/streamlit_app.py
```

3. Open http://localhost:8501 in your browser

### Features

- **Chat Interface**: Conduct interviews with real-time responses
- **Knowledge Graph**: Visualize extracted concepts and relationships
- **Metrics Panel**: Track coverage, scoring, and strategy selection
- **Session Controls**: Create, load, and delete sessions

### Dependencies

```bash
pip install streamlit plotly networkx
```

## Documentation

- [PRD](PRD.md) - Product requirements
- [Engineering Guide](ENGINEERING_GUIDE.md) - Technical specifications
