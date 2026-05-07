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
| `src/methodologies/scoring.py`, `src/methodologies/registry.py`, `config/methodologies/*.yaml` | `.claude/context/strategy-scoring.md`, `.claude/context/methodology-parameter-flow.md` |
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

## Known Failure Modes

- **Stage ordering (Stage 4 < Stage 6):** Any state reset in Stage 4 (GraphUpdateStage) is invisible to Stage 6 signal detectors. Do not reset signal-relevant state in early stages. See `.claude/context/node-state-tracker.md`.
- **Tracker/slot-key schema drift raises `NodeNotTrackedError`:** When slot discovery (Stage 4.5) emits tracking keys that don't match NodeStateTracker's internal schema, `append_quality`, `update_focus`, and `record_yield` now **raise `NodeNotTrackedError`** rather than warning silently (see `src/services/node_state_tracker.py`). Historically this was a silent warning that let MEC chains stall at `instrumental_value` with `structural_completeness` stuck at zero — that failure mode is now loud-fail. If you see `NodeNotTrackedError` during a run, the canonical slot resolver and tracker registration are out of sync. Original silent-failure regression fixed in commit `d4fd3b8`; raised to exception thereafter. See `.claude/context/node-state-tracker.md` and `.claude/context/canonical-slots.md`.
- **record_yield is_empty() guard silently skips yield credit after B7:** `record_yield` has a guard `if graph_changes.is_empty(): return self` that skips yield recording when nodes_added=0 AND edges_added=0. After B7 moved record_yield from GraphUpdateStage to EdgeExtractionBridgeStage, the bridge hardcodes `nodes_added=0` and passes `edges_added=len(edges_added)`. When the feature flag is OFF, `edges_added` is always `[]` (task is None), so `is_empty()` returns True every turn. Consequence: `turns_since_last_yield` never resets, all explored nodes reach exhaustion threshold (3) by turn 6, interview stops prematurely with `all_nodes_exhausted`. **Fixed by removing the is_empty() guard** — the focus node was actively used this turn regardless of graph change counts. See `.claude/context/node-state-tracker.md`.
- **Stale specs:** Agents trust docs absolutely. An outdated doc produces silent failures — correct-looking code based on wrong assumptions. The drift detector warns but does not prevent this. When in doubt, verify the doc against source.
- **Canonical slot timing:** Canonical slots are only `active` after `support_count >= canonical_min_support_nodes` (default 2). Signals depending on canonical data return empty/zero on first occurrence.
- **`select_strategy_and_focus()` uses joint scoring:** All eligible (strategy, node) pairs are scored simultaneously via `rank_strategy_node_pairs()`. The old 2-stage (strategy-first, then node) architecture has been removed.
- **MEC uses chain-aware strategies:** MEC methodologies use 6 strategies (ascend, ground, bridge, branch, anchor, revitalize) with `valid_when` gates. Legacy strategies (deepen, explore, clarify, reflect) have been removed. Other methodologies now use their own v2 strategy architectures — see `config/methodologies/` for each method's strategy set and `valid_when` gates. Do NOT apply MEC strategy changes to non-MEC methods.
- **valid_when hard gate:** Chain-aware strategies are only scored for nodes where the gate signal is True. A strategy with `valid_when: convgraph.node.chain.gap.above` will never be scored for terminal nodes.
- **LLM signal key absence:** If the LLM omits a signal key from its JSON response (e.g. `engagement`), the corresponding suppressor disappears for that turn, potentially unblocking a strategy that should have been suppressed. Haiku systematically dropped `engagement` and `certainty` from the `global` section because the `concepts` section (variable length) consumed its output attention before reaching the trailing `global` keys. **Fixed** by reordering the JSON template to put `global` before `concepts` (commit `c1e5a7b`). Fallback logic remains in `batch_detector.py` (neutral score=3 → normalises to 0.5) as safety net. Symptom: `engagement.mid` and `certainty.mid` fire at 100% across all turns; check logs for "LLM output missing global" warnings. See `.claude/context/signal-detection-llm.md`.
- **Node binding mismatch silently strips weights:** A strategy with `node_binding: none` that references `convgraph.node.*` weights loses ~70% of its positive mass because `partition_signal_weights()` strips all node-scoped weights before Stage 1 scoring. The strategy competes only on global signals and appears to "never fire." Fix: flip to `node_binding: required` so weights route to Stage 2 joint scoring. RG `triadic_elicit` and `explore_ideal` were fixed (Phase 4.3). When adding new strategies, verify that strategies with `convgraph.node.*` weights use `node_binding: required`. See `.claude/context/strategy-scoring.md`.
- **Escape valve repetition weights create runaway positive feedback:** Using a positive weight on `interview.strategy.self_count` (e.g., `revitalize: +0.15`) was intended to break fatigue loops but becomes self-reinforcing when structural strategies are suppressed. In CIT baseline, `revitalize` won 7/10 turns due to this loop. Fix: flip to a negative brake (e.g., `-0.5`) matching JTBD's already-calibrated value. See `.claude/context/strategy-scoring.md`.
- **Base score asymmetry overwhelms repetition brakes:** When a strategy's structural base score exceeds its repetition brake magnitude by >3×, monoculture is inevitable regardless of brake correctness. CJM `deepen_stage` base = 2.3 vs. brake = -0.6 — takes 4 consecutive uses to halve. Fix: either reduce structural positive mass, strengthen brake to ≥50% of base, or add `convgraph.node.focus.count.high` penalty. See `.claude/context/strategy-scoring.md`.
- **Chain topology signals use `chain_relevant` flag from methodology YAML:** `ChainTopologySignalDetector` filters edges using `schema.get_chain_relevant_edge_types()`, which reads the `chain_relevant: true/false` flag from methodology YAML edge definitions. Each methodology declares which edges represent chain progression (e.g., MEC: `leads_to`; JTBD: `triggers`/`addresses`/`enables`/`supports`). Methodologies with no `chain_relevant` edges or <2 ontology levels get empty chain topology signals (`{}`). **When adding a new methodology YAML**, ensure every edge definition has a `chain_relevant` flag — missing flags default to `None` (excluded from chain topology). See `.claude/context/signal-detection-graph.md`.
- **Strategy-scoped repetition signal must resolve per-candidate:** `interview.strategy.self_count` historically returned a single scalar (frequency of the *last-selected* strategy). The scorer applied this scalar to *every* candidate using each candidate's own weight, causing strategies to be penalized when *other* strategies repeated. Fix: signal returns `{strategy_name: normalized_count}`; scorer resolves to the candidate's own scalar via `_scoped_signal_names()` (cached helper that queries `SignalDetector.get_scoped_signal_names()`). As of Architecture #6 (Apr 2026), scoped signals are auto-discovered via the `scoped` ClassVar on SignalDetector subclasses; the manual `STRATEGY_SCOPED_SIGNALS` tuple has been removed. See `.claude/context/strategy-scoring.md`.
- **chain_rules are reporting-only — not used by the live engine:** `config/chain_rules/*.yaml` files only affect `scripts/reporting/generate_causal_chains.py`. The live interview engine filters chain edges using the `chain_relevant: true` flag from methodology YAML (`ChainTopologySignalDetector` at `src/signals/graph/chain_topology_signals.py:108`). Do NOT assume a chain_rules change will affect strategy selection. See `.claude/context/chain-rules.md`.
- **Phase boundaries in methodology YAML are dead config:** The `phase_boundaries: {early_max_turns, mid_max_turns}` key in methodology YAML is never read by any Python code. The live engine computes phase boundaries from `interview_config.yaml` (`phases.exploratory/focused/closing.n_turns`), scaled to `max_turns`. Override with `--phase-turns` CLI flag. See `.claude/context/phase-detection.md`.
- **Extraction prompt has hardcoded and methodology-driven sections:** The worked example was removed April 2026 (hardcoded MEC types contaminated non-MEC extraction). Methodology-specific content (node/edge descriptions, extraction guidelines, relationship examples) belongs in methodology YAML, not in `src/llm/prompts/extraction.py`. Node descriptions now include `[L0]`–`[L4]` level prefixes rendered by `methodology_schema.py:get_node_descriptions()`. See `.claude/context/extraction.md`.
- **Level skipping in edge extraction produces zero full chains:** Edge extraction (Stage 4.5B, Haiku) connects semantically related concepts regardless of ontology level adjacency — producing edges that jump L0→L3 or L1→L4 and bypassing intermediate levels. The chain builder classifies these as "advanced" (with gaps) rather than "full" chains. Confirmed systematic failure across 3 independent simulation runs (0-2 full chains per 15-turn interview). Fix: `edge_extraction_notes` in `method:` YAML block instructs Haiku to prefer level-adjacent edges. Stage 3 concept extraction uses a separate Level-Aware Relationship Creation section in the extraction prompt (hardcoded, gated on ≥2 ontology levels) — this is a different stage and a different calibration path. See `.claude/context/extraction.md`.
- **Edge extraction pair-count timeout causes silent bridge blackout:** Stage 4.5B fires an asyncio task for edge extraction. When candidate pairs exceed ~40 (e.g., 8 CURRENT nodes × 14 total candidates = 76 pairs), the 30s Haiku timeout fires, the task stores `LLMTimeoutError`, and Stage 4.6 (bridge) receives no result. In logs this appeared as a 60s gap between canonical_skip and the next turn's graph_updated, with no `bridge_complete` or `edge_extraction_task_failed` entry. Fix: `_build_candidate_pairs_section()` now caps at 40 pairs with priority ordering (FOCUS first, then NEIGHBOR, CURRENT, RECENT). Stage 4.6 now emits `edge_extraction_bridge_task_missing_despite_nodes` WARNING when nodes were added but task is None. See `.claude/context/extraction.md`.
- **`insufficient_evidence` dominating edge rejections means utterance context is missing, not over-rejection:** If `insufficient_evidence` accounts for >50% of all `edge_rejected_summary` entries across a session, the root cause is that Haiku cannot see the cross-turn utterance where the causal relationship was stated — not that Haiku is being too conservative. Confirmed failure mode: pre-fix, 86% of rejections were `insufficient_evidence` because utterance assembly was limited to 3–4 fragments from focus-node source utterances. Fix: pass full conversation history (`utterance_repo.get_recent(session_id, limit=30)`) so Haiku can find the L0→L1 connective tissue regardless of when each concept was introduced. After the fix, dominant rejection codes shifted to `type_constraint_violation` and `semantic_irrelevance` — correct behavior. See `.claude/context/extraction.md`.
- **Edge extraction confirms directionally inverted edges at medium confidence:** Haiku treats co-occurrence of two concept labels in an utterance as sufficient evidence, even when the utterance *negates* the relationship ("I don't think about health when at home" was cited for `at_home → triggers → health_mindset`). The negation check added to the prompt explicitly defines this as `insufficient_evidence`, not a low-confidence confirmation. When reviewing confirmed edges in turn diagnostics, flag edges where the evidence quote contains "don't", "not", "never" or similar negation — these are candidates for inversion. See `.claude/context/extraction.md`.
- **Turn 0 concepts become permanent orphans without the OPENING tag:** The opening turn extracts 5–9 rich concepts that appear as RECENT in Turn 1 but get cut by the 40-pair cap (RECENT is the lowest-priority bucket). From Turn 2 onward they are absent from the candidate set. The OPENING tag re-includes them for turns 2–5 as a new lowest-priority bucket. Without this, the opening extraction produces orphans that chain reports show as "stranded context" — e.g., `get a refreshing energy boost` (L2 job_statement) never connects to the L3 emotional_job nodes even when semantically central to the interview. See `.claude/context/extraction.md`.
- **`level_guidance` injected before the strategy description line is overridden:** `get_question_user_prompt()` historically injected `level_guidance` before the strategy description line. The LLM reads the strategy description last and uses it as the operative instruction — the level_guidance becomes a hint the LLM ignores. Symptom: JTBD `ascend` at L3 `emotional_job` nodes produced confirmation probes ("Does that feeling make you reach for ZeroFizz?") instead of solution-closure questions ("What do you hire to fulfill that need?"). Fix: inject level_guidance AFTER the strategy line with "⚠ Level-specific instruction (overrides strategy description above):" prefix. See `.claude/context/methodology-parameter-flow.md`.
- **Focus is always a surface UUID. Slot identity is a property of the surface state.** `NodeStateTracker.states` is keyed by `SurfaceNodeId`. `NodeState.slot_id: Optional[SlotId]` records slot membership for theme-level aggregation. The boundary contract `TurnResult.focus_node_id` is always a surface UUID and is always retrievable via `graph_repo.get_node()`. If a future signal needs a slot key, use `tracker.slot_id_for_surface(surface_id)` rather than reintroducing slot keys into the tracker keyspace. Violation of this invariant is asserted at `node_signal_detection_service.py` (signal merge guard) and would have raised before reaching production.

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
