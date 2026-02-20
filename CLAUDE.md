# Claude Code Quick Reference - Interview System v2

A graph-led conversational interview system with adaptive strategy selection via Signal Pools.
Features a dual graph architecture with conversaion (surface) and canonical graphs with semantically deduplicated nodes.
Plug-in methodology configuration based on YAML files.
Includes simulation service to generate sample interviews with YAML-paramterized synthetic personas

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
| `docs/SYSTEM_DESIGN.md` | System architecture |
| `docs/data_flow_paths.md` | 15 critical data flow diagrams |
| `docs/pipeline_contracts.md` | Stage input/output contracts |
| `docs/extraction_and_graphs.md` | Extraction and Graphs configuration |
| `docs/signals_and_strategies.md` | Signal Pools configuration |

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

# Interview
phase_boundaries:
  early_max_turns: 4
  mid_max_turns: 12
```

---

## Critical Data Flows

See `docs/data_flow_paths.md` for full diagrams. Key paths:

1. **Turn Count Evolution** (Path 1): Session.state → ContextLoading → turn_number → ... → ScoringPersistence → Session.state updated
2. **Strategy Selection** (Path 2): graph_state + signals → MethodologyStrategyService → ranked strategies
3. **Graph State Mutation** (Path 3): extraction → GraphUpdate (dedup) → DB → StateComputation → graph_state
4. **Traceability Chain** (Path 5): user_input → UtteranceSaving → utterance.id → Extraction → GraphUpdate
5. **Canonical Slot Discovery** (Path 10): surface_nodes → slot_service → canonical_slots + mappings

---

## Common Tasks

```bash
# Start API server locally
uv run uvicorn src.main:app --reload

# Run simulation
uv run python scripts/run_simulation.py coffee_jtbd_v2 skeptical_analyst 10
# Outputs: synthetic_interviews/TIMESTAMP_concept_persona.json
#          synthetic_interviews/TIMESTAMP_concept_persona_scoring.csv (per-turn signal decomposition)
# JSON turn fields: signals (global), node_signals (per-node: exhaustion, focus, etc.)

# Generate scoring CSV from existing simulation JSON
uv run python scripts/generate_scoring_csv.py synthetic_interviews/<file>.json

# Analyze similarity distribution
uv run python scripts/analyze_similarity_distribution.py <session_id>

# Run CodeGrapher architectural queries and generate report:
1. Read queries from arch_queries.md (in backticks within tables)
2. Check CodeGrapher index status via MCP: mcp__codegrapher__codegraph_status; refresh if stale (full mode)
3. Run each query via MCP: mcp__codegrapher__codegraph_query with query="..."
4. Aggregate results and sort by PageRank (descending)
5. Generate markdown report with format: YYYYMMDD_HHMMSS_codegrapher_report.md
6. Report sections: Summary table, Detailed findings by category, PageRank guide

Note: Prioritize issues with PageRank >= 0.10 (core components) for fixes

# Fix diagnostics with categorization
/skill deep-code-quality  # Use before applying ruff/pyright fixes

# Create a new node signal (per-node analysis from NodeStateTracker)
1. Create detector class in `src/signals/graph/node_signals.py`:
   - Inherit from `NodeSignalDetector` (not `SignalDetector`)
   - Set `signal_name = "graph.node.your_signal"` (namespaced)
   - Set `description` for YAML documentation
   - Implement `async def detect(self, context, graph_state, response_text)`
   - Return `dict[node_id, value]` for all tracked nodes
   - Use `self._get_all_node_states()` to access NodeState data
2. Add class to `__all__` export list in `src/signals/graph/__init__.py`
3. (Optional) Add to methodology YAML under `signals:` section
4. (Optional) Add signal_weights in strategy configs
5. Run tests: `uv run pytest tests/signals/`

# Create a new LLM signal (response quality analysis via Kimi K2.5)
1. Add rubric to `src/signals/llm/prompts/signals.md`:
   - Format: `your_signal: How would you phrase the question?`
   - Define 1-5 scale with clear anchors
2. Create detector class in `src/signals/llm/signals/your_signal.py`:
   - Use `@llm_signal()` decorator with metadata
   - Set `rubric_key` matching signals.md key
   - Class body: `pass` (decorator handles everything)
3. Add import to `src/signals/llm/signals/__init__.py`
4. Add class to `__all__` export list in `src/signals/llm/signals/__init__.py`
5. Add to methodology YAML under `signals: llm:` section
6. Add signal_weights in strategy configs (e.g., `llm.your_signal.high: 0.5`)
7. Run tests: `uv run pytest tests/signals/`

```

---

## Root Cause Analysis Protocol

**Before fixing any bug, trace the complete data flow back to the domain model. Never fix at the symptom site without understanding where the data was originally produced.**

### Type Mismatch Issues (e.g., `'dict' object has no attribute 'x'`)

1. **Identify the consumption site** — Where the error surfaces
2. **Check the type annotation** — Look at the variable's declared type in function signature or class
3. **Trace upstream to the domain model** — Don't stop at the first producer; keep going until you reach the Pydantic model or dataclass that defines the canonical shape:
   ```bash
   grep -rn "variable_name" --include="*.py" | grep -v "test_"
   ```
4. **Audit every transformation in the chain**:
   - What fields does the domain model have?
   - What fields does each serialization step actually include?
   - Where is information silently dropped?
5. **Fix at the information loss point** — The bug lives where fields are dropped or types are narrowed, not where the absence is noticed:
   - Consumption code is wrong → fix access pattern
   - A transformation silently drops fields → fix the transformation
   - Contract annotation is wrong → fix the annotation

### The `.get()` / fallback test
If a fix uses `.get("key", default)` or `getattr(obj, "attr", default)` to paper over a missing field, **it is not the root cause fix** — it is masking data loss upstream. Ask: why is the field absent? Trace back to find where it was dropped.

### Data Flow Tracing Template

```
┌──────────────┐   ┌──────────────────┐   ┌──────────────┐   ┌─────────────┐
│ Domain Model │──▶│ Serialization(s) │──▶│ Contract     │──▶│ Consumption │
│ (Pydantic)   │   │ (intermediate)   │   │ (TurnResult) │   │ (error site)│
└──────────────┘   └──────────────────┘   └──────────────┘   └─────────────┘
       │                   │                     │                   │
  All fields?        Which fields          Which fields         Which fields
                     included?             documented?          accessed?
                   ← root cause likely here if mismatch
```

### Red Flags (always investigate deeper)
- [ ] Type annotation says `Dict` but code uses `.attr` access
- [ ] Type annotation says `List[Class]` but code uses `["key"]` access
- [ ] `Any` types in the chain — trace through these carefully
- [ ] Multiple assignments with same variable name across files
- [ ] `hasattr()` checks or `isinstance()` guards masking type confusion
- [ ] `.get(key, default)` used as a fix — default value was fabricated, not derived

---

## Debugging Patterns

### Logging
logs are saved to `./logs/`

### Strategy Selection Issues
When investigating why a strategy was selected:
1. Check logs for `strategy_selected` or `strategies_ranked` entries
2. Look for phase weight and bonus application in logs
3. Verify signals detected match YAML config expectations
4. Check `src/methodologies/scoring.py` for scoring logic
5. Use synthetic interviews to reproduce patterns

### Joint Strategy-Node Scoring Debugging (D1 Architecture)
When debugging joint scoring:
- Check `rank_strategy_node_pairs()` output for score breakdown
- Look at `strategy_alternatives` list in logs: `[(strategy, node_id, score), ...]`
- Verify global and node signals are merged correctly (node signals take precedence)
- Check for negative weights from `graph.node.exhausted.true` signals
- Verify phase weights (multiplicative) and bonuses (additive) are applied

### Signal Detection Debugging
- Enable debug logging: Check `signals_detected` log entries
- Verify signal namespacing: `graph.*`, `llm.*`, `temporal.*`, `meta.*`, `graph.node.*`, `technique.node.*`
- Check YAML config for signal_weights definitions
- Look for phase weight and bonus application in scoring logs

### Phase Weights and Bonuses Debugging
- Phase detection happens in `InterviewPhaseSignal` → `meta.interview.phase`
- Phase weights retrieved from `config.phases[phase].signal_weights` (multiplicative)
- Phase bonuses retrieved from `config.phases[phase].phase_bonuses` (additive)
- Applied in `rank_strategies()` and `rank_strategy_node_pairs()` as:
  ```python
  multiplier = phase_weights.get(strategy.name, 1.0)
  bonus = phase_bonuses.get(strategy.name, 0.0)
  final_score = (base_score * multiplier) + bonus
  ```
- Check logs for `interview_phase_detected`, `phase_weights_loaded`, `phase_bonuses_loaded`

### Node Exhaustion Debugging
- Check `graph.node.exhausted` signal for exhausted nodes
- Check `meta.node.opportunity` for node opportunity status (exhausted/probe_deeper/fresh)
- Look at `graph.node.exhaustion_score` for continuous exhaustion score (0.0-1.0)
- Check `graph.node.focus_streak` for persistent focus patterns
- Verify NodeStateTracker state for focus_count, turns_since_last_yield, current_focus_streak

### Uvicorn Logging
For debugging API/pipeline issues:
```bash
# Enable uvicorn debug logging
uvicorn src.main:app --reload --log-level debug

# Check specific log files
tail -f /tmp/uvicorn_debug.log
tail -f /tmp/uvicorn_phase_test.log
```

---

## YAML configuration locations

### Methodology Schemas

```bash
config/methodologies/
├── jobs_to_be_done.yaml
├── means_end_chain.yaml
└── critical_incident.yaml
```

### Synthetic Personas

```bash
config/personas/
├── convenience_seeker.yaml
├── health_conscious.yaml
├── minimalist.yaml
├── price_sensitive.yaml
├── quality_focused.yaml
├── skeptical_analyst.yaml
├── social_conscious.yaml
└── sustainability_minded.yaml
```

### Concepts

```bash
config/concepts/
├── coffee_jtbd_v2.yaml
└── oat_milk_v2.yaml
```

---

## When in Doubt

1. Check `docs/data_flow_paths.md` for the relevant path number
2. Check `docs/pipeline_contracts.md` for stage contracts
3. Check `src/services/turn_pipeline/context.py` for PipelineContext
4. Run `bd ready` for available work
