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

## Signal Pools

**Location**: `src/signals/`

### `graph/` — Knowledge graph structure and node-level signals

**Graph-level (`graph.*`):**
- `max_depth` - Longest causal chain depth (normalized 0-1)
- `avg_depth` - Average depth across all chains
- `depth_by_element` - Depth of each specific element/node
- `node_count` - Total number of concepts extracted
- `edge_count` - Total number of relationships
- `orphan_count` - Isolated concepts with no connections
- `chain_completion` - Produces `chain_completion.ratio` and `chain_completion.has_complete`
- `canonical_concept_count` - Number of deduplicated canonical concepts
- `canonical_edge_density` - Edge-to-concept ratio in canonical graph
- `canonical_exhaustion_score` - Average exhaustion across canonical slots

**Node-level (`graph.node.*`):**
- `exhausted` - Binary exhaustion flag
- `exhaustion_score` - Continuous exhaustion (0-1)
- `yield_stagnation` - No yield for 3+ consecutive turns
- `focus_streak` - Current focus streak: none/low/medium/high
- `is_current_focus` - Whether this node is the active focus
- `recency_score` - Time-decay score (0-1, higher = more recent)
- `is_orphan` - Node has no connections
- `edge_count` - Total edges (incoming + outgoing)
- `has_outgoing` - Node has outgoing relationships

### `llm/` — Response quality analysis via Kimi K2.5

**Signals (`llm.*`):**
- `response_depth` - Elaboration quantity (1-5 scale)
- `specificity` - Concreteness of language (1-5 scale)
- `certainty` - Epistemic confidence (1-5 scale)
- `valence` - Emotional tone (1-5 scale)
- `engagement` - Willingness to engage (1-5 scale)

### `meta/` — Composite signals (depend on multiple sources)

**Signals (`meta.*`):**
- `interview_progress` - Overall interview completion (0-1)
- `interview.phase` - Current phase: early/mid/late (+ phase_reason, is_late_stage)
- `node.opportunity` - Node category: exhausted/probe_deeper/fresh

### `session/` — Conversation history and strategy patterns

**Signals (mixed namespaces):**
- `llm.global_response_trend` - Session trend: deepening/stable/shallowing/fatigued
- `temporal.strategy_repetition_count` - Times current strategy used in last 5 turns (normalized 0-1)
- `temporal.turns_since_strategy_change` - Consecutive turns using current strategy (normalized 0-1)
- `technique.node.strategy_repetition` - Consecutive same strategy on node: none/low/medium/high

**Scoring**: `final_score = (base_score × phase_multiplier) + phase_bonus`

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
