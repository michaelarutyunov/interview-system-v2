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

## Documentation

- [PRD](PRD.md) - Product requirements
- [Engineering Guide](ENGINEERING_GUIDE.md) - Technical specifications
