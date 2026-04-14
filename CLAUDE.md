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
| `.claude/context/` | Subsystem specs — primary reference for implementation and debugging |
| `.claude/context/pipeline-contracts.md` | Stage input/output contracts |
| `.claude/context/signal-detection-graph.md` | Graph & node signal detection |
| `.claude/context/signal-detection-llm.md` | LLM signal detection |
| `.claude/context/strategy-scoring.md` | Joint strategy-node scoring |
| `.claude/context/node-state-tracker.md` | NodeStateTracker per-turn lifecycle |
| `.claude/context/turn-count.md` | Turn count evolution and phase detection |
| `.claude/context/extraction.md` | LLM concept/relationship extraction |
| `.claude/context/graph-dedup.md` | Surface graph deduplication |
| `.claude/context/canonical-slots.md` | Canonical slot discovery |

---

## Code Structure

```
src/
├── services/turn_pipeline/stages/    # 12 pipeline stages
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

| Stage | File | Purpose |
|-------|------|---------|
| 1 | `context_loading_stage.py` | Load session, conversation history |
| 2 | `utterance_saving_stage.py` | Save user input |
| 2.5 | `srl_preprocessing_stage.py` | Linguistic parsing |
| 3 | `extraction_stage.py` | Extract concepts/relationships |
| 4 | `graph_update_stage.py` | Update KG with dedup |
| 4.5 | `slot_discovery_stage.py` | Canonical slot mapping |
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

# LLM Providers (config/interview_config.yaml → llm: section)
# anthropic: Claude models (Sonnet, Haiku) — default for extraction + question generation
# kimi: Moonshot AI models (K2)
# deepseek: DeepSeek models
# grok: xAI Grok models
# zhipu: Zhipu AI GLM models (GLM-5.1, GLM-4.7, etc.)

# Interview
phase_boundaries:
  early_max_turns: 4
  mid_max_turns: 12

# Chain-aware strategies (MEC only)
chain_completion:
  expected_branching: {attribute: 3, functional_consequence: 2, ...}
  score_threshold: 0.15  # Below this, conversation-level strategies activate

# Strategy valid_when gates (MEC)
# ascend:   graph.node.gap_above
# ground:   graph.node.gap_below
# bridge:   graph.node.level_skip
# branch:   graph.node.branching_deficit
# anchor:   graph.node.is_orphan
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
| `src/methodologies/scoring.py`, `src/methodologies/registry.py`, `config/methodologies/*.yaml` | `.claude/context/strategy-scoring.md` |
| `src/services/turn_pipeline/stages/strategy_selection_stage.py`, `src/services/methodology_strategy_service.py` | `.claude/context/strategy-selection.md` |
| `src/signals/graph/*.py`, `src/services/*signal_detection_service.py` | `.claude/context/signal-detection-graph.md` |
| `src/signals/llm/signals/*.py` | `.claude/context/signal-detection-llm.md` |
| `src/services/graph_service.py` | `.claude/context/graph-dedup.md` |
| `src/services/canonical_slot_service.py` | `.claude/context/canonical-slots.md` |
| `src/services/extraction_service.py` | `.claude/context/extraction.md` |
| Any pipeline stage (`stages/*.py`), `context.py`, `pipeline_contracts.py` | `.claude/context/pipeline-contracts.md` |
| `src/services/node_state_tracker.py`, `src/services/node_signal_detection_service.py` | `.claude/context/node-state-tracker.md` |
| `src/main.py`, `src/routers/*.py` | `docs/API.md` |

### After editing — update the same doc
Same mappings apply symmetrically. Update the corresponding doc in the same commit or the commit immediately after.

### Freshness policy
One deferred update is acceptable — the drift detector allows it. Two commits without a doc update triggers a warning. When you see a warning, update the doc before continuing.

---

## Agent Routing

Specialist agents are invoked based on which files are being modified. Agents live in `.claude/agents/{id}/AGENT.md`.

| Modifying | Invoke agent |
|-----------|-------------|
| `src/signals/**`, `config/methodologies/*.yaml` (signal weights, signal detection) | `signal-specialist` |
| `src/services/turn_pipeline/**`, `src/domain/models/pipeline_contracts.py` | `pipeline-specialist` |
| `src/services/extraction_service.py`, `src/llm/prompts/` | `extraction-specialist` |
| `src/methodologies/**` (registry, scoring), `config/methodologies/*.yaml` (YAML structure, validation) | `methodology-specialist` |

Agents will be created iteratively as failure patterns are observed. See `.claude/codified-context-principles.md` for creation criteria.

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

## Known Failure Modes

- **Stage ordering (Stage 4 < Stage 6):** Any state reset in Stage 4 (GraphUpdateStage) is invisible to Stage 6 signal detectors. Do not reset signal-relevant state in early stages. See `.claude/context/node-state-tracker.md`.
- **Stale specs:** Agents trust docs absolutely. An outdated doc produces silent failures — correct-looking code based on wrong assumptions. The drift detector warns but does not prevent this. When in doubt, verify the doc against source.
- **Canonical slot timing:** Canonical slots are only `active` after `support_count >= canonical_min_support_nodes` (default 2). Signals depending on canonical data return empty/zero on first occurrence.
- **`select_strategy_and_focus()` uses joint scoring:** All eligible (strategy, node) pairs are scored simultaneously via `rank_strategy_node_pairs()`. The old 2-stage (strategy-first, then node) architecture has been removed.
- **MEC uses chain-aware strategies:** MEC methodologies use 6 strategies (ascend, ground, bridge, branch, anchor, revitalize) with `valid_when` gates. Legacy strategies (deepen, explore, clarify, reflect) have been removed. Other methodologies (JTBD, CJM, CIT, Repertory Grid) use their own strategy names — do NOT apply MEC strategy changes to those.
- **valid_when hard gate:** Chain-aware strategies are only scored for nodes where the gate signal is True. A strategy with `valid_when: graph.node.gap_above` will never be scored for terminal nodes.
- **LLM signal key absence:** If the LLM omits a signal key from its JSON response (e.g. `engagement`), the corresponding suppressor disappears for that turn, potentially unblocking a strategy that should have been suppressed. Fixed in `batch_detector.py` with a neutral score=3 fallback (normalises to 0.5). Symptom: strategy fires spuriously at a specific turn with no obvious explanation — check logs for "not found in LLM response" warnings. See `.claude/context/signal-detection-llm.md`.

---

## Common Tasks

```bash
# Start API server locally
uv run uvicorn src.main:app --reload

# Run simulation (valid concept IDs: glp1_food_mec, glp1_food_mec_strict, glp1_food_mec_flex, glp1_food_jtbd, coffee_jtbd_v2, meal_planning_jtbd_v2)
# Personas: baseline_cooperative, skeptical_analyst, glp1_user, health_conscious, price_sensitive, convenience_seeker, quality_focused, sustainability_minded, social_conscious, minimalist
uv run python scripts/run_simulation.py glp1_food_mec baseline_cooperative 10

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
