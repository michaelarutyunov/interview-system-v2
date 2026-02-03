# Claude Code Quick Reference - Interview System v2

> **Purpose**: This file serves as a quick index for Claude Code to find key project documentation and architecture references.

## Project Overview

The Interview System v2 is a knowledge-graph-based conversational **semi-structured** interview system that uses a **10-stage turn processing pipeline** with adaptive strategy selection.

---

## Beads Workflow (Critical!)

This project uses **bd** (beads) for issue tracking. Beads lives in `.beads/` directory and only reads that directory (does NOT read agents.md or claude.md).

### Quick Commands

```bash
bd ready              # Find available work (no blockers)
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git remote
```

### Session Completion Protocol (MANDATORY)

**When ending a work session, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds

---

## Essential Architecture Documentation

### Pipeline & Data Flow (START HERE)

When working on the turn pipeline, always reference:

| Document | Location | When to Use |
|----------|----------|-------------|
| **Pipeline Stage Contracts** | `docs/pipeline_contracts.md` | Understanding what each stage reads/writes |
| **Data Flow Paths** | `docs/data_flow_paths.md` | Visualizing critical data flows through the pipeline |
| **System Design** | `docs/SYSTEM_DESIGN.md` | Narrative architecture for articles |

### ADRs (Architecture Decision Records)

Key ADRs that define the system architecture:

| ADR | Topic | Location |
|-----|-------|----------|
| ADR-008 | Pipeline Pattern & Internal API Boundaries | `docs/adr/008-internal-api-boundaries-pipeline-pattern.md` |
| ADR-010 | Three-Client LLM Architecture | `docs/adr/010-three-client-llm-architecture.md` |
| ADR-013 | Methodology-Centric Architecture | `docs/adr/0013-methodology-centric-architecture.md` |
| ADR-014 | Signal Pools Architecture | `docs/adr/ADR-014-signal-pools-architecture.md` |
| ADR-008 (alt) | Concept-Driven Coverage System | `docs/adr/008-concept-element-coverage-system.md` |
| ADR-009 | Fail-Fast Error Handling (MVP) | `docs/adr/009-fail-fast-error-handling-mvp.md` |

### Operational Standards

| Document | Purpose | Location |
|----------|---------|----------|
| **Development Guide** | Setup, testing, code style, error handling, logging | `docs/DEVELOPMENT.md` |
| **API Documentation** | Complete API reference with endpoints, schemas, examples | `docs/API.md` |
| **Performance Guidelines** | Performance optimization and monitoring | `docs/PERFORMANCE.md` |

---

## Code Structure

```
src/
├── services/
│   └── turn_pipeline/          # Core pipeline implementation
│       ├── context.py          # PipelineContext dataclass
│       ├── pipeline.py         # TurnPipeline orchestrator
│       └── stages/             # Individual stage implementations
├── methodologies/              # Methodology module (Signal Pools)
│   ├── signals/                # Shared signal pools (graph, llm, temporal, meta)
│   ├── techniques/             # Shared technique pool (laddering, elaboration, etc.)
│   ├── config/                 # YAML methodology definitions
│   └── registry.py             # MethodologyRegistry (YAML loader)
├── domain/
│   └── models/                 # Domain models (GraphState, Utterance, etc.)
└── api/
    └── routes/
        └── sessions.py         # API entry point
```

---

## Quick Reference: Pipeline Stages

| Stage | File | Purpose |
|-------|------|---------|
| 1 | `context_loading_stage.py` | Load session context, graph state |
| 2 | `utterance_saving_stage.py` | Save user input |
| 3 | `extraction_stage.py` | Extract concepts/relationships |
| 4 | `graph_update_stage.py` | Update knowledge graph |
| 5 | `state_computation_stage.py` | Refresh graph state metrics |
| 6 | `strategy_selection_stage.py` | Select questioning strategy (Signal Pools) |
| 7 | `continuation_stage.py` | Decide if interview continues |
| 8 | `question_generation_stage.py` | Generate next question |
| 9 | `response_saving_stage.py` | Save system response |
| 10 | `scoring_persistence_stage.py` | Save scoring, update session |

---

## Quick Reference: Signal Pools Architecture (Phase 6)

Signal pools enable flexible strategy selection by collecting signals from multiple data sources:

| Pool | Namespace | Example Signals |
|------|-----------|-----------------|
| **Graph** | `graph.*` | node_count, max_depth, orphan_count, coverage_breadth |
| **LLM** | `llm.*` | response_depth, sentiment, topics |
| **Temporal** | `temporal.*` | strategy_repetition_count, turns_since_focus_change |
| **Meta** | `meta.*` | interview_progress, exploration_score |

**Key Points:**
- **LLM signals are fresh** - computed every response, no cross-response caching
- **YAML configuration** - methodologies defined in `src/methodologies/config/*.yaml`
- **MethodologyStrategyService** - uses YAML configs for strategy selection
- **FocusSelectionService** - centralizes focus selection based on strategy.focus_preference

---

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

# Strategy selection (Phase 6: Signal Pools)
strategy, focus, signals, strategy_alternatives

# Continuation
should_continue, focus_concept

# Output
next_question, scoring, stage_timings
```

---

## Quick Reference: Critical Data Flows

1. **Turn Count**: Session.state → ContextLoading → turn_number → ... → ScoringPersistence → Session.state += 1
2. **Strategy Selection (Signal Pools)**: graph_state + recent_nodes → MethodologyStrategyService → signal detection → strategy ranking → best strategy
3. **Graph Mutation**: extraction → GraphUpdate → database → StateComputation → graph_state
4. **Strategy History (Diversity)**: Session.state.strategy_history → ContextLoading → temporal.strategy_repetition_count → penalty → ScoringPersistence → append
5. **Traceability Chain (ADR-010)**: user_input → UtteranceSaving → utterance.id → Extraction (source_utterance_id) → GraphUpdate (node.utterance_id)

---

## Common Tasks

### Adding a new pipeline stage

1. Read `docs/pipeline_contracts.md` for the contract format
2. Read `docs/data_flow_paths.md` to understand which paths you intersect
3. Create stage file in `src/services/turn_pipeline/stages/`
4. Add stage to `TurnPipeline` in `src/services/turn_pipeline/pipeline.py`
5. Update `docs/pipeline_contracts.md` with new stage contract
6. Update `docs/data_flow_paths.md` if introducing new data flow

### Adding a new methodology

1. Create YAML config in `src/methodologies/config/my_methodology.yaml`
2. Define signals (from shared pools) and strategies (with signal_weights)
3. The methodology is automatically available via MethodologyRegistry
4. No code changes required - pure YAML configuration

### Adding a new signal

1. Determine signal pool (graph/, llm/, temporal/, meta/)
2. Create signal class in appropriate pool directory
3. Export from pool `__init__.py`
4. Register in signal registry
5. Add to methodology YAML config
6. Add tests

### Debugging state issues

1. Check `docs/data_flow_paths.md` for the relevant path
2. Check `docs/pipeline_contracts.md` for stage contracts
3. Trace through the specific stages that handle that state

---

## Development Tools

- **Package management**: `uv` (not pip)
- **Linting/Formatting**: `ruff`
- **Type checking**: `pyright` (via LSP)
- **Issue tracking**: `bd` (beads)

---

## Documents that should be updated after codebase changes

- `docs/pipeline_contracts.md`
- `docs/data_flow_paths.md`
- `docs/SYSTEM_DESIGN.md`
  
  optionally, if relevant for the implemented changes:
- `docs/DEVELOPMENT.md`
- `docs/API.md`
- `docs/syntheric_personas.md`

---

## Project Files Reference

| File | Purpose |
|------|---------|
| `PRD.md` | Product Requirements Document |
| `ENGINEERING_GUIDE.md` | Engineering guidelines |
| `IMPLEMENTATION_PLAN.md` | Implementation phases |
| `AGENTS.md` | Agent task specifications (legacy - beads in .beads/) |

---

## When in doubt...

1. Check `docs/pipeline_contracts.md` for stage contracts
2. Check `docs/data_flow_paths.md` for data flow
3. Check `docs/SYSTEM_DESIGN.md` for narrative architecture
4. Check `docs/DEVELOPMENT.md` for error handling and logging standards
5. Check relevant ADR in `docs/adr/` for architectural rationale
6. Check `src/services/turn_pipeline/context.py` for PipelineContext schema
7. Check `.beads/` for issue tracking (bd ready)
