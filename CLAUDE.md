# Claude Code Quick Reference - Interview System v2

A graph-led conversational interview system with adaptive strategy selection via Signal Pools.
Features a dual graph architecture with conversaion (surface) and canonical graphs with semantically deduplicated nodes.
Plug-in methodology configuration based on YAML files.
Includes simulation service to generate sample interviews with YAML-paramterized synthetic personas

---

## Code Design Principles

Any codebase change should follow these principles
- no hardcoded keywords
- no fallbacks, no placeholders, no defaults, no heuristics without explicit concent
- no code outside of the scope of the task at hand

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
# Run simulation
uv run python scripts/run_simulation.py coffee_jtbd_v2 skeptical_analyst 10

# Analyze similarity distribution
uv run python scripts/analyze_similarity_distribution.py <session_id>

# Run CodeGrapher architectural queries and generate report:
# 1. Read queries from arch_queries.md (in backticks within tables)
# 2. Run each query via MCP: mcp__codegrapher__codegraph_query with query="..."
# 3. Aggregate results and sort by PageRank (descending)
# 4. Generate markdown report with format: YYYYMMDD_HHMMSS_codegrapher_report.md
# 5. Report sections: Summary table, Detailed findings by category, PageRank guide
# Note: Prioritize issues with PageRank >= 0.10 (core components) for fixes

```

---

## Debugging Patterns

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

## Methodology YAML Location

```bash
config/methodologies/
├── jobs_to_be_done.yaml
├── means_end_chain.yaml
└── critical_incident.yaml
```

## Synthetic Personas YAML Location

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

## Concept YAML Location

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
