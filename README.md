# Interview System v2

Graph-led conversational interview system with adaptive strategy selection, dual-graph knowledge representation, and plug-in methodology configurations. Supports AI-to-AI simulation for rapid methodology testing.

## Features

- **6 methodologies**: Means-End Chain (strict/flex), Jobs-to-be-Done, Critical Incident, Customer Journey Mapping, Repertory Grid — each self-contained in YAML with its own ontology, signals, and strategies
- **Dual-graph architecture**: Surface graph preserves respondent language; canonical graph provides stable deduplicated signals
- **14-stage turn pipeline**: Context loading → extraction → graph dedup → canonical slots → state computation → joint strategy-node scoring → question generation
- **Chain-aware strategies**: ascend, ground, bridge, branch, anchor, revitalize, elaborate — gated by chain topology signals (gap.above, gap.below, is_orphan)
- **Phase-based adaptation**: early/mid/late phases with methodology-specific strategy multipliers. Explicit phase control via `--phase-turns` flag
- **AI-to-AI simulation**: Test methodologies against synthetic personas (baseline_cooperative, brief_responder, etc.)
- **Causal chain extraction**: Post-hoc analytical layer with direction-based chain rules, completeness tiers, and reverse edge recovery
- **Interview export & review**: Structured export (transcript, chains, graph, scoring, latency) and qualitative insight generation

## Quick Start

### Prerequisites

- Python 3.11+
- Anthropic API key
- [uv](https://github.com/astral-sh/uv)

### Install

```bash
git clone https://github.com/michaelarutyunov/interview-system-v2.git
cd interview-system-v2
uv sync
cp .env.example .env   # add your ANTHROPIC_API_KEY
```

### Run a Simulation

```bash
# Quick test with default 10 turns
uv run python scripts/run_simulation.py \
  --concept zerofizz_beverage_jtbd \
  --persona baseline_cooperative

# Explicit phase control (4 early, 4 mid, 2 late)
uv run python scripts/run_simulation.py \
  --concept zerofizz_beverage_jtbd \
  --persona baseline_cooperative \
  --phase-turns 4-4-2

# See available concepts and personas
uv run python scripts/run_simulation.py --help
```

### Export and Review

```bash
# Export all artifacts from a simulation
uv run python scripts/reporting/export_interview.py synthetic_interviews/<file>.json

# Generate qualitative review
# (use /interview-review on the export folder in Claude Code)
```

### Start the API

```bash
uv run uvicorn src.main:app --reload   # → http://localhost:8000/docs
```

### Run Tests

```bash
uv run pytest
uv run ruff check . --fix
```

## Project Structure

```
├── src/
│   ├── api/                        # FastAPI routes and schemas
│   ├── core/                       # Configuration, logging, exceptions
│   ├── domain/models/              # Pydantic models (Session, Graph, Pipeline)
│   ├── llm/prompts/                # Extraction and question generation prompts
│   ├── methodologies/              # YAML loader, strategy scoring
│   ├── persistence/repositories/   # SQLite + aiosqlite
│   ├── services/
│   │   └── turn_pipeline/stages/   # 14 pipeline stages
│   └── signals/                    # graph/, llm/, session/, meta/ signal pools
├── config/
│   ├── methodologies/              # 6 methodology YAMLs (ontology, strategies, phases)
│   ├── chain_rules/                # Direction-based chain construction rules
│   ├── concepts/                   # Research topic definitions
│   └── personas/                   # Synthetic respondent profiles
├── scripts/
│   ├── run_simulation.py           # AI-to-AI interview runner
│   └── reporting/                  # Export, causal chain extraction
├── tests/                          # Unit, pipeline, and signal tests
├── docs/                           # System design, simulation guide, ADRs
├── .claude/                        # Claude Code config: agents, context docs, skills
└── reports/interviews/             # Simulation exports (gitignored)
```

## Configuration

All interview behavior is YAML-driven. Key config locations:

| What | Where |
|------|-------|
| Methodology definitions | `config/methodologies/{name}.yaml` |
| Chain construction rules | `config/chain_rules/{methodology}.yaml` |
| Interview config (phase proportions, dedup thresholds) | `config/interview_config.yaml` |
| Research topics | `config/concepts/*.yaml` |
| Synthetic personas | `config/personas/domains/*.yaml` |

For development conventions, agent routing, known failure modes, and subsystem specs, see `CLAUDE.md` and `.claude/context/`.

## Documentation

| Document | Purpose |
|----------|---------|
| `CLAUDE.md` | Development conventions, routing, known failure modes |
| `docs/SYSTEM_DESIGN.md` | System architecture |
| `docs/interview_ai_simulation.md` | AI-to-AI simulation guide |
| `docs/API.md` | API reference |
| `docs/DEVELOPMENT.md` | Development setup and scripts |
| `.claude/context/` | Subsystem specifications (extraction, scoring, signals, graph, phases, chain rules) |

## License

MIT
