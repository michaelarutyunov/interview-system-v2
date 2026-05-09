# Claude Code Quick Reference - Interview System v2

A graph-led conversational interview system with adaptive strategy selection via Signal Pools.
Features a dual graph architecture with conversation (surface) and canonical graphs with semantically deduplicated nodes.
Plug-in methodology configuration based on YAML files.
Includes simulation service to generate sample interviews with YAML-parameterized synthetic personas

---

## Code Design Principles

Any codebase change should follow these principles:

### Core Principles
- **No hardcoded keywords** — All configurable values live in YAML, not code
- **No implicit fallbacks** — No placeholders, defaults, or heuristics without explicit consent
- **Scope discipline** — No code outside the scope of the task at hand
- **Fail-fast for visibility** — Errors raise immediately rather than degrading silently

### Architectural Principles
- **Separation of mechanism and domain** — Core pipeline stays agnostic to specific methodologies, concepts, or personas; domain content lives in YAML modules, not embedded in code
- **Type-safe contracts** — Pydantic BaseModel defines stage boundaries, not markdown docs
- **Freshness guarantees** — State computed after extraction is validated as fresh before use
- **Methodology-centric organization** — Each methodology self-contained with signals/strategies
- **Direct signal→strategy scoring** — Simplicity preferred over multi-tier complexity
- **Traceability** — Every data point links back to its source utterance

### Data Principles
- **Dual-graph architecture** — Surface preserves fidelity, canonical provides stable signals
- **Feature flags for graceful skip** — Use `enable_*` flags, not try/except for optional features
- **Lazy-loading for resources** — Expensive resources (spaCy) load on first use via property pattern
- **Extended properties escape hatch** — New metrics added without breaking changes 

---

## Essential Documentation

| Document | Purpose |
|----------|---------|
| `docs/SYSTEM_DESIGN.md` | System architecture overview |
| `docs/interview_ai_simulation.md` | AI-to-AI simulation system for testing with synthetic personas |
| `.claude/context/simulation-export-schema.md` | Stable JSON/CSV export contract and signal taxonomy |
| `.claude/context/` | Subsystem specs — primary reference for implementation and debugging |
| `.claude/context/pipeline-contracts.md` | Stage input/output contracts |
| `.claude/context/signal-detection-graph.md` | Graph & node signal detection |
| `.claude/context/signal-detection-llm.md` | LLM signal detection |
| `.claude/context/strategy-scoring.md` | Joint strategy-node scoring |
| `.claude/context/node-state-tracker.md` | NodeStateTracker per-turn lifecycle |
| `.claude/context/turn-count.md` | Turn count evolution and phase detection |
| `.claude/context/phase-detection.md` | Phase boundary calculation (3-tier priority), --phase-turns flag |
| `.claude/context/extraction.md` | LLM concept/relationship extraction, prompt architecture |
| `.claude/context/chain-rules.md` | Chain construction rules (reporting-only), direction-based format |
| `.claude/context/graph-mutation.md` | Graph evolution, node/edge dedup, cross-turn resolution, permitted connections |
| `.claude/context/canonical-slots.md` | Canonical slot discovery |
| `.claude/context/docker-deployment.md` | Docker build decisions, Cloud Run config, update procedure |
| `.claude/context/ui-architecture.md` | Streamlit UI components, state management, styling, API integration |

---

## Code Structure

```
src/
├── services/turn_pipeline/stages/    # 16 pipeline stages
├── services/
│   ├── graph_service.py              # Surface graph + dedup
│   ├── canonical_slot_service.py     # Canonical graph
│   ├── extraction_service.py         # LLM extraction
│   ├── methodology_strategy_service.py  # Strategy selection
│   ├── global_signal_detection_service.py
│   └── node_signal_detection_service.py
├── signals/                          # Signal pools
│   ├── graph/                        # graph.* signals
│   ├── llm/                          # llm.* signals
│   ├── session/                      # temporal.* signals
│   ├── meta/                         # meta.* signals
│   └── signal_base.py                # Base classes
├── methodologies/
│   ├── registry.py                   # YAML loader
│   └── scoring.py                    # Strategy scoring
└── persistence/repositories/         # DB access
```

---

## Pipeline Stages

16 stages. Edge extraction (4.5B+4.6) uses the prefetch+bridge async pattern (fire task, overlap with next stage, await later). 4.5B fires before 4.5 so the edge extraction Haiku overlaps with SlotDiscovery.

| Stage | File | Purpose |
|-------|------|---------|
| 1 | `context_loading_stage.py` | Load session, conversation history |
| 2 | `utterance_saving_stage.py` | Save user input |
| 2.5 | `srl_preprocessing_stage.py` | Linguistic parsing |
| 3 | `extraction_stage.py` | Extract concepts (nodes only; edges → 4.5B) |
| 3.1 | `llm_prefetch_stage.py` | Fire async LLM signal detection (Haiku) |
| 4 | `graph_update_stage.py` | Update KG with dedup, write nodes |
| 4.5 | `slot_discovery_stage.py` | Canonical slot mapping |
| 4.5B | `edge_extraction_prefetch_stage.py` | Fire async edge extraction (Haiku) |
| 4.6 | `edge_extraction_bridge_stage.py` | Await edges, persist, update tracker, record yield |
| 4.7 | `llm_signal_bridge_stage.py` | Await signal prefetch, route ratings, seal tracker |
| 5 | `state_computation_stage.py` | Refresh graph metrics |
| 6 | `strategy_selection_stage.py` | Signal Pools → strategy |
| 7 | `continuation_stage.py` | Continue or stop |
| 8 | `question_generation_stage.py` | Generate next question |
| 9 | `response_saving_stage.py` | Save system response |
| 10 | `scoring_persistence_stage.py` | Save scoring, update state |

---

## Key Configuration

```python
# Deduplication
surface_similarity_threshold: float = 0.80
canonical_similarity_threshold: float = 0.60
canonical_min_support_nodes: int = 2

# Features
enable_srl: bool = True
enable_canonical_slots: bool = True
# Stage 4.5B edge extraction is mandatory (flag removed in B11)

# LLM Providers (config/interview_config.yaml → llm: section)
# Six call types: extraction, edge_extraction, slot_scoring, signal_scoring, question_generation, n
# anthropic: Claude models (Sonnet, Haiku) — default for extraction + question generation
# kimi: Moonshot AI models (K2)
# deepseek: DeepSeek models
# grok: xAI Grok models
# zhipu: Zhipu AI GLM models (GLM-5.1, GLM-4.7, etc.)

# Interview
# Phase boundaries are controlled by --phase-turns flag (explicit) or
# interview_config.yaml phases.exploratory/focused/closing n_turns (proportional).
# See .claude/context/phase-detection.md for the 3-tier priority architecture.
# The methodology YAML phases.{early,mid,late}.signal_weights define strategy
# multipliers per phase but do NOT control phase boundaries themselves.

# Chain construction rules (config/chain_rules/):
# One YAML per methodology — REPORTING-ONLY, does NOT affect live engine.
# Live engine uses chain_relevant: true flag from methodology YAML instead.
# Direction-based format (April 2026): upward, upward_or_lateral, reverse, unconstrained.
# See .claude/context/chain-rules.md for full specification.

# Active methodology configs (config/methodologies/):
# means_end_chain_v2_strict  — 6 strategies, all with valid_when gates (reference)
# means_end_chain_v2_flex    — same as strict, no permitted_connections on edges
# jobs_to_be_done_v2         — 7 strategies (elaborate, ascend, ground, probe_pain, anchor, revitalize, validate)
# critical_incident_v2       — 7 strategies (elicit_narrative, ascend, ground, bridge, anchor, revitalize, validate)
# customer_journey_mapping_v2 — 8 strategies, flat ontology (no chain topology signals)
# repertory_grid_v2          — 8 strategies, flat dimensional (no chain topology signals)
# Legacy configs moved to config/methodologies/legacy/

# Strategy valid_when gates (MEC + JTBD + CIT use chain topology)
# ascend:   convgraph.node.chain.gap.above
# ground:   convgraph.node.chain.gap.below
# bridge:   convgraph.node.chain.level.skip
# branch:   convgraph.node.chain.branching_deficit
# anchor:   convgraph.node.is_orphan
# revitalize: no gate (conversation-level fallback)
```

---

## Critical Data Flows

See `.claude/context/` for subsystem specs. Key flows:

1. **Turn Count Evolution**: Session.state → ContextLoading → turn_number → ... → ScoringPersistence → Session.state updated
2. **Strategy Selection**: graph_state + signals → MethodologyStrategyService → ranked strategies
3. **Graph State Mutation**: extraction → GraphUpdate (dedup) → DB → StateComputation → graph_state
4. **Traceability Chain**: user_input → UtteranceSaving → utterance.id → Extraction → GraphUpdate
5. **Canonical Slot Discovery**: surface_nodes → slot_service → canonical_slots + mappings

---

## Database Access

- **Path**: `data/interview.db` (SQLite, set via `DATABASE_PATH` in `.env`)
- **Driver**: `aiosqlite` — use directly, not SQLAlchemy sessions
- **Quick query pattern**:
  ```python
  import asyncio, json, aiosqlite
  async def main():
      async with aiosqlite.connect('data/interview.db') as db:
          db.row_factory = aiosqlite.Row
          async with db.execute('SELECT ...') as cursor:
              rows = await cursor.fetchall()
  asyncio.run(main())
  ```
- **Key tables**: `sessions`, `utterances`, `kg_nodes`, `kg_edges`, `canonical_slots`, `scoring_history`, `methodology_signals`
- **Token/cost data**: `json.loads(session['config'])['metadata']['llm_usage']`

---

## Documentation Routing

Run `uv run python scripts/check_doc_drift.py` any time to check for drift. The session-start and pre-commit hooks do this automatically.

### Before editing — read first
| Editing | Read first |
|---------|-----------|
| `src/methodologies/scoring.py`, `src/methodologies/registry.py`, `config/methodologies/*.yaml` | `.claude/context/strategy-scoring.md`, `.claude/context/methodology-parameter-flow.md` (includes Calibration Principles) |
| `src/domain/models/methodology_schema.py` | `.claude/context/extraction.md`, `.claude/context/chain-rules.md` |
| `src/services/turn_pipeline/stages/strategy_selection_stage.py`, `src/services/methodology_strategy_service.py` | `.claude/context/strategy-selection.md` |
| `src/signals/graph/*.py`, `src/services/*signal_detection_service.py` | `.claude/context/signal-detection-graph.md` |
| `src/signals/meta/*.py` | `.claude/context/phase-detection.md` |
| `src/signals/llm/signals/*.py` | `.claude/context/signal-detection-llm.md` |
| `src/services/graph_service.py` | `.claude/context/graph-mutation.md` |
| `src/services/canonical_slot_service.py` | `.claude/context/canonical-slots.md` |
| `src/services/extraction_service.py`, `src/llm/prompts/extraction.py` | `.claude/context/extraction.md` |
| `src/llm/prompts/edge_extraction.py`, `src/services/edge_extraction_service.py`, `src/domain/models/edge_extraction.py` | `.claude/context/extraction.md` |
| `src/llm/prompts/question.py`, `src/services/question_service.py`, `src/services/turn_pipeline/stages/question_generation_stage.py` | `.claude/context/pipeline-contracts.md` |
| Any pipeline stage (`stages/*.py`), `context.py`, `pipeline_contracts.py` | `.claude/context/pipeline-contracts.md` |
| `src/services/node_state_tracker.py`, `src/services/node_signal_detection_service.py` | `.claude/context/node-state-tracker.md` |
| `src/main.py`, `src/api/routes/*.py` | `docs/API.md` |
| `scripts/reporting/*.py`, `scripts/diagnostics/extract_simulation_data.py` | `.claude/context/simulation-export-schema.md` |
| `config/chain_rules/*.yaml` | `.claude/context/chain-rules.md` |
| `Dockerfile`, `entrypoint.sh`, `.dockerignore`, `scripts/deploy_cloud_run.sh` | `.claude/context/docker-deployment.md` |
| `ui/streamlit_app.py`, `ui/components/*.py`, `ui/api_client.py`, `.streamlit/config.toml` | `.claude/context/ui-architecture.md` |

### After editing — update the same doc
Same mappings apply symmetrically. Update the corresponding doc in the same commit or the commit immediately after.

### Freshness policy
One deferred update is acceptable — the drift detector allows it. Two commits without a doc update triggers a warning. When you see a warning, update the doc before continuing.

---

## Agent Routing

Specialist agents are invoked based on which files are being modified. Agents live in `.claude/agents/{id}/AGENT.md`.

| Modifying | Invoke agent |
|-----------|-------------|
| `src/signals/**`, `src/services/*signal_detection*.py`, `src/services/node_state_tracker.py`, `src/services/methodology_strategy_service.py`, `src/methodologies/scoring.py`, `src/methodologies/registry.py`, `src/services/turn_pipeline/stages/strategy_selection_stage.py`, `config/methodologies/*.yaml` (signal weights, strategy config, phases) | `signal-specialist` |
| `src/services/turn_pipeline/**`, `src/services/session_service.py`, `src/services/question_service.py`, `src/domain/models/pipeline_contracts.py`, `src/services/turn_pipeline/result.py` | `pipeline-specialist` |
| `src/services/extraction_service.py`, `src/llm/prompts/`, `src/services/turn_pipeline/stages/extraction_stage.py`, `src/domain/models/extraction.py`, `src/services/turn_pipeline/stages/srl_preprocessing_stage.py`, `config/methodologies/*.yaml` (ontology, extraction_guidelines, relationship_examples, concept_naming) | `extraction-specialist` |
| `config/methodologies/*.yaml` (methodology definitions, strategies, signal_weights, phases), `src/methodologies/registry.py`, `src/methodologies/scoring.py`, `src/services/methodology_strategy_service.py` | `methodology-specialist` |

Agents will be created iteratively as failure patterns are observed. See `.claude/codified-context-principles.md` for creation criteria.

**Intentionally uncovered directories** (stable infrastructure, no specialist needed):
- `src/api/` — FastAPI web layer; thin controllers, stable routes
- `src/core/` — config loaders, logging, exceptions; rarely modified
- `src/persistence/` — database + SQLite repos; stable schema

---

## Diagnostic Triage (ruff / pyright)

Before fixing any ruff or pyright diagnostic, **categorize first** using `/deep-code-quality`:

- **Safe auto-fix**: unused imports (F401), formatting, line length — apply immediately
- **Investigate first**: unused variables (F841), `Optional` type errors, complexity warnings (C901) — read surrounding context, fix the root cause not the symptom
- **Never suppress**: security warnings (S-series), type errors in error-handling code

**Red flags — stop and investigate:**
- Unused variable that looks like validation logic → likely a forgotten guard
- Type error suggesting `Optional` on a function that shouldn't fail → raise an exception instead
- Multiple related type errors in the same module → design issue, not isolated bug

Run `/deep-code-quality` for the full framework when a diagnostic doesn't obviously fit category 1.

---

## Known Failure Mode Index

Each entry routes to the authoritative source. Full diagnostics (root cause, reproduction steps, commit hashes) live in Tier 2 agent anti-patterns and Tier 3 context doc failure mode sections — not here.

| Symptom | Authoritative Source |
|---------|---------------------|
| Stage ordering, state reset invisible to detectors, record_yield gating | `pipeline-specialist`, `pipeline-contracts.md` |
| NodeNotTrackedError, tracker/slot-key schema drift | `node-state-tracker.md`, `canonical-slots.md` |
| Stale specs — agents trust outdated docs, silent failures | `codified-context-principles.md` §Drift Detection |
| Canonical slots inactive until support_count ≥ min_nodes | `canonical-slots.md`, `signal-specialist` |
| Joint scoring architecture, strategy-first→joint migration | `strategy-scoring.md` |
| MEC strategy set (6 chain-aware), valid_when gates, non-MEC isolation | `methodology-specialist`, `strategy-scoring.md` |
| LLM signal key absence, engagement/certainty stuck at 100% | `signal-detection-llm.md`, `signal-specialist` |
| Node binding mismatch silently stripping weights | `strategy-scoring.md`, `signal-specialist`, `methodology-parameter-flow.md` |
| Repetition weight feedback loops (escape valve, base score asymmetry) | `strategy-scoring.md`, `methodology-specialist` |
| chain_relevant flag, empty chain topology signals | `signal-detection-graph.md`, `methodology-specialist` |
| Strategy-scoped repetition signal (per-candidate resolution) | `strategy-scoring.md`, `signal-specialist` |
| chain_rules are reporting-only, do not affect live engine | `chain-rules.md`, `methodology-specialist` |
| Phase boundaries in methodology YAML are dead config | `phase-detection.md`, `methodology-specialist` |
| Extraction prompt — hardcoded content, methodology isolation | `extraction-specialist`, `extraction.md` |
| Level skipping, pair-count timeout, insufficient_evidence dominance | `extraction.md` |
| Directional inversion (negation in evidence quotes), Turn 0 orphans | `extraction.md` |
| level_guidance injected before strategy line is overridden | `methodology-parameter-flow.md` |
| Focus is always a surface UUID, slot identity via tracker | `node-state-tracker.md`, `pipeline-specialist` |
| Weight calibration drift — tuning for strategy distribution balance instead of missed conversational opportunities | `methodology-parameter-flow.md` §Calibration Principles |
| Signal threshold mismatch — global 0.25/0.75 discretization applied to signals with different semantics (e.g., orphan_ratio) | `methodology-parameter-flow.md` §Threshold Mismatches |

---

## Common Tasks

```bash
# Start API server locally
uv run uvicorn src.main:app --reload

# Run simulation (use --help for full concept/persona listings)
uv run python scripts/run_simulation.py --concept glp1_food_mec --persona baseline_cooperative --max-turns 10

# Run with explicit phase control (4 early, 4 mid, 2 late = 10 total)
uv run python scripts/run_simulation.py --concept glp1_food_mec --persona baseline_cooperative --phase-turns 4-4-2

# Run tests
uv run pytest

# Check doc drift
uv run python scripts/check_doc_drift.py
```

See `docs/DEVELOPMENT.md` for full scripts reference, configuration locations, and GCP deployment.

---

## When in Doubt

1. Check `.claude/context/` for the relevant subsystem spec
2. Check `.claude/context/pipeline-contracts.md` for stage contracts
3. Check `src/services/turn_pipeline/context.py` for PipelineContext
4. Check `.claude/context/debugging-protocol.md` for root cause analysis methodology
5. Check `.claude/context/debugging-subsystems.md` for subsystem-specific debug guides
6. Run `bd ready` for available work
