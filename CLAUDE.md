# Claude Code Quick Reference - Interview System v2

Knowledge-graph-based conversational interview system with adaptive strategy selection via Signal Pools.

---

## Beads Workflow

```bash
bd ready              # Available work (no blockers)
bd show <id>          # Issue details
bd update <id> --status in_progress  # Claim
bd close <id>         # Complete
bd sync               # Sync with remote
```

### Session Close Protocol (MANDATORY)

```bash
git status && git add <files> && bd sync
git commit -m "..." && bd sync && git push
git status  # MUST show "up to date"
```

---

## Essential Documentation

| Document | Purpose |
|----------|---------|
| `docs/data_flow_paths.md` | 15 critical data flow diagrams |
| `docs/pipeline_contracts.md` | Stage input/output contracts |
| `docs/SYSTEM_DESIGN.md` | System architecture |
| `docs/DEVELOPMENT.md` | Setup, testing, standards |
| `docs/canonical_extraction.md` | Dual-graph deduplication |
| `docs/signals_and_strategies.md` | Signal Pools configuration |
| `docs/adr/` | Architecture Decision Records |

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
| 1 | `context_loading_stage.py` | Load session, graph state |
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

## Signal Pools

| Pool | Namespace | Signals |
|------|-----------|---------|
| Graph | `graph.*` | max_depth, chain_completion, node_count, orphan_count |
| LLM | `llm.*` | response_depth, specificity, certainty, valence, engagement |
| Temporal | `temporal.*` | strategy_repetition_count, turns_since_strategy_change |
| Meta | `meta.*` | interview_progress, interview.phase, node.opportunity |
| Node | `graph.node.*` | exhaustion_score, focus_streak, is_orphan |
| Technique | `technique.node.*` | strategy_repetition |

**Scoring**: `final_score = (base_score × phase_multiplier) + phase_bonus`

---

## Key Configuration

```python
# Deduplication
surface_similarity_threshold: float = 0.80
canonical_similarity_threshold: float = 0.83
canonical_min_support_nodes: int = 1

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
# Run simulation
uv run python scripts/run_simulation.py coffee_jtbd_v2 skeptical_analyst 10

# Analyze similarity distribution
uv run python scripts/analyze_similarity_distribution.py <session_id>

# Lint and format
ruff check . --fix && ruff format .

# Check type diagnostics (via LSP)
# Use: LSP(operation: "getDiagnostics", filePath: "src/...")
```

---

## Debugging Quick Reference

| Issue | Check |
|-------|-------|
| Wrong strategy selected | `strategies_ranked` in logs, signal values, phase weights |
| Node signals ignored | Verify D1 scoring in `rank_strategy_node_pairs()` |
| Duplicate nodes | Surface dedup threshold, canonical threshold |
| Edges not connecting | Cross-turn resolution, label_to_node population |
| Phase detection | `meta.interview.phase` signal, `phase_boundaries` config |

---

## Methodology YAML Location

```bash
config/methodologies/
├── jobs_to_be_done.yaml
├── means_end_chain.yaml
└── critical_incident.yaml
```

---

## When in Doubt

1. Check `docs/data_flow_paths.md` for the relevant path number
2. Check `docs/pipeline_contracts.md` for stage contracts
3. Check `src/services/turn_pipeline/context.py` for PipelineContext
4. Run `bd ready` for available work
