# Claude Code Quick Reference - Interview System v2

> **Purpose**: This file serves as a quick index for Claude Code to find key project documentation and architecture references.

## Project Overview

The Interview System v2 is a knowledge-graph-based conversational interview system that uses a **10-stage turn processing pipeline** with adaptive strategy selection.

## Essential Architecture Documentation

### Pipeline & Data Flow (START HERE)

When working on the turn pipeline, always reference:

| Document | Location | When to Use |
|----------|----------|-------------|
| **Pipeline Stage Contracts** | `docs/pipeline_contracts.md` | Understanding what each stage reads/writes |
| **Data Flow Paths** | `docs/data_flow_paths.md` | Visualizing critical data flows through the pipeline |

### ADRs (Architecture Decision Records)

Key ADRs that define the system architecture:

| ADR | Topic | Location |
|-----|-------|----------|
| ADR-008 | Pipeline Pattern & Internal API Boundaries | `docs/adr/008-internal-api-boundaries-pipeline-pattern.md` |
| ADR-010 | Three-Client LLM Architecture | `docs/adr/010-three-client-llm-architecture.md` |
| ADR-004 | Two-Tier Scoring System | `docs/adr/004-two-tier-scoring-system.md` |
| ADR-008 (alt) | Concept-Driven Coverage System | `docs/adr/008-concept-element-coverage-system.md` |
| ADR-009 | Fail-Fast Error Handling (MVP) | `docs/adr/009-fail-fast-error-handling-mvp.md` |

### Operational Standards

| Document | Purpose | Location |
|----------|---------|----------|
| **API Documentation** | Complete API reference with endpoints, schemas, examples | `docs/API.md` |
| **Logging Standards** | Structured logging patterns with `structlog` | `docs/logging_standards.md` |

### Code Structure

```
src/
├── services/
│   └── turn_pipeline/          # Core pipeline implementation
│       ├── context.py          # PipelineContext dataclass
│       ├── pipeline.py         # TurnPipeline orchestrator
│       └── stages/             # Individual stage implementations
├── domain/
│   └── models/                 # Domain models (GraphState, Utterance, etc.)
└── api/
    └── routes/
        └── sessions.py         # API entry point
```

## Quick Reference: Pipeline Stages

| Stage | File | Purpose |
|-------|------|---------|
| 1 | `context_loading_stage.py` | Load session context, graph state |
| 2 | `utterance_saving_stage.py` | Save user input |
| 3 | `extraction_stage.py` | Extract concepts/relationships |
| 4 | `graph_update_stage.py` | Update knowledge graph |
| 5 | `state_computation_stage.py` | Refresh graph state metrics |
| 6 | `strategy_selection_stage.py` | Select questioning strategy |
| 7 | `continuation_stage.py` | Decide if interview continues |
| 8 | `question_generation_stage.py` | Generate next question |
| 9 | `response_saving_stage.py` | Save system response |
| 10 | `scoring_persistence_stage.py` | Save scoring, update session |

## Quick Reference: PipelineContext Fields

```python
# Inputs (immutable)
session_id, user_input

# Session metadata
methodology, concept_id, concept_name, turn_number, mode, max_turns
recent_utterances, strategy_history

# Graph state
graph_state, recent_nodes

# Extraction
extraction (concepts, relationships)

# Utterances
user_utterance, system_utterance

# Graph updates
nodes_added, edges_added

# Strategy
strategy, selection_result, focus

# Continuation
should_continue, focus_concept

# Output
next_question, scoring, stage_timings
```

## Quick Reference: Critical Data Flows

1. **Turn Count**: Session.state → ContextLoading → turn_number → ... → ScoringPersistence → Session.state += 1
2. **Strategy Selection**: graph_state + recent_nodes → Tier 1 (vetoes) → Tier 2 (scoring) → strategy
3. **Graph Mutation**: extraction → GraphUpdate → database → StateComputation → graph_state
4. **Strategy History**: Session.state.strategy_history → ContextLoading → diversity penalty → ScoringPersistence → append

## Common Tasks

### Adding a new pipeline stage

1. Read `docs/pipeline_contracts.md` for the contract format
2. Read `docs/data_flow_paths.md` to understand which paths you intersect
3. Create stage file in `src/services/turn_pipeline/stages/`
4. Add stage to `TurnPipeline` in `src/services/turn_pipeline/pipeline.py`
5. Update `docs/pipeline_contracts.md` with new stage contract
6. Update `docs/data_flow_paths.md` if introducing new data flow

### Modifying strategy selection

1. Read `docs/adr/004-two-tier-scoring-system.md` for scoring algorithm
2. Read `docs/data_flow_paths.md` Path 2 for complete flow
3. Modify scorers in `src/services/turn_pipeline/stages/strategy_selection_stage.py`

### Debugging state issues

1. Check `docs/data_flow_paths.md` for the relevant path
2. Check `docs/pipeline_contracts.md` for stage contracts
3. Trace through the specific stages that handle that state

## Development Tools

- **Package management**: `uv` (not pip)
- **Linting/Formatting**: `ruff`
- **Type checking**: `pyright` (via LSP)

## Project Files Reference

| File | Purpose |
|------|---------|
| `PRD.md` | Product Requirements Document |
| `ENGINEERING_GUIDE.md` | Engineering guidelines |
| `IMPLEMENTATION_PLAN.md` | Implementation phases |
| `AGENTS.md` | Agent task specifications |

## When in doubt...

1. Check `docs/pipeline_contracts.md` for stage contracts
2. Check `docs/data_flow_paths.md` for data flow
3. Check relevant ADR in `docs/adr/` for architectural rationale
4. Check `src/services/turn_pipeline/context.py` for PipelineContext schema
