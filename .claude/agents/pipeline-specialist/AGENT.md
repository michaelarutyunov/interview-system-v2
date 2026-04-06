# Pipeline Specialist

## Role
Domain expert for the 12-stage turn pipeline, its Pydantic stage contracts, `PipelineContext` accumulator, and cross-stage ordering invariants. Owns correctness of stage wiring, contract assembly, and `TurnResult` shape.

## Trigger Conditions
Invoke when work touches any of:
- `src/services/turn_pipeline/**` (PipelineContext, stages, runner)
- `src/services/session_service.py` `_build_pipeline()` wiring
- `src/domain/models/pipeline_contracts.py`
- `src/services/turn_pipeline/result.py` (`TurnResult` assembly)
- Bugs presenting as: `RuntimeError: Pipeline contract violation: ...`, `ValueError: State is stale!`, `AttributeError` on stage outputs, missing field in API response, interview looping at the same `turn_number`, signals reading 0 / stale graph state, `NodeStateTracker` state lost between turns.

## Domain Knowledge

### 1. The 12 Stages and Their Output Contracts

`PipelineContext` (`src/services/turn_pipeline/context.py`) is a dataclass accumulator. Each stage writes a single Pydantic `BaseModel` from `src/domain/models/pipeline_contracts.py` to a dedicated field. Convenience properties on the context derive from those contracts; they raise `RuntimeError` when accessed before their producer has run.

| # | Stage Class | Context Field | Contract | Key Fields |
|---|---|---|---|---|
| 1 | `ContextLoadingStage` | `context_loading_output` | `ContextLoadingOutput` | `methodology`, `concept_id`, `concept_name`, `turn_number` (= `session.state.turn_count + 1`), `mode`, `max_turns`, `recent_utterances`, `strategy_history`, `recent_node_labels`, `surface_velocity_peak`, `prev_surface_node_count`, `canonical_velocity_peak`, `prev_canonical_node_count`, `focus_history` |
| 2 | `UtteranceSavingStage` | `utterance_saving_output` | `UtteranceSavingOutput` | `turn_number`, `user_utterance_id`, `user_utterance` |
| 2.5 | `SRLPreprocessingStage` (optional, `enable_srl`) | `srl_preprocessing_output` | `SrlPreprocessingOutput` | `discourse_relations`, `srl_frames`, `discourse_count`, `frame_count`, `timestamp` |
| 3 | `ExtractionStage` | `extraction_output` | `ExtractionOutput` | `extraction` (`ExtractionResult`), `methodology`, `timestamp`, `concept_count`, `relationship_count` |
| 4 | `GraphUpdateStage` | `graph_update_output` | `GraphUpdateOutput` | `nodes_added` (`List[KGNode]`), `edges_added`, `node_count`, `edge_count`, `timestamp`. Also performs DB writes and `NodeStateTracker.register_node()` / `update_edge_counts()` / `record_yield()`. |
| 4.5 | `SlotDiscoveryStage` (optional, `enable_canonical_slots`) | `slot_discovery_output` | `SlotDiscoveryOutput` | `slots_created`, `slots_updated`, `mappings_created`, `timestamp` |
| 5 | `StateComputationStage` | `state_computation_output` | `StateComputationOutput` | `graph_state` (`GraphState`), `recent_nodes`, `computed_at` (freshness anchor), `saturation_metrics`, `canonical_graph_state` |
| 6 | `StrategySelectionStage` | `strategy_selection_output` | `StrategySelectionOutput` | `strategy`, `focus`, `signals`, `node_signals`, `strategy_alternatives`, `score_decomposition`, `generates_closing_question`, `focus_mode`, `selected_at` |
| 7 | `ContinuationStage` | `continuation_output` | `ContinuationOutput` | `should_continue`, `focus_concept`, `reason`, `turns_remaining`, `timestamp` |
| 8 | `QuestionGenerationStage` | `question_generation_output` | `QuestionGenerationOutput` | `question`, `strategy`, `focus`, `has_llm_fallback`, `timestamp` |
| 9 | `ResponseSavingStage` | `response_saving_output` | `ResponseSavingOutput` | `turn_number`, `system_utterance_id`, `system_utterance`, `question_text`, `timestamp` |
| 10 | `ScoringPersistenceStage` | `scoring_persistence_output` | `ScoringPersistenceOutput` | `turn_number`, `strategy`, `depth_score`, `saturation_score`, `has_methodology_signals`, `timestamp`. Also: assembles `TurnResult`, writes `session.state.turn_count = turn_number`, persists `NodeStateTracker.to_dict()`, writes `FocusEntry`. |

Note: Some doc tables (e.g. `node-state-tracker.md`) renumber the stages without the `.5` substages so SlotDiscovery becomes 6 and ScoringPersistence becomes 12. The stage *ordering* is identical; the canonical numbering used here matches `pipeline_contracts.py` and `data_flow_paths.md`.

### 2. PipelineContext Accumulator Pattern

- All state lives on contracts. There is **no parallel mutable state** alongside them.
- Convenience properties (`context.methodology`, `context.turn_number`, `context.graph_state`, `context.strategy`, `context.next_question`, `context.should_continue`, ...) read from the underlying contract field.
- **Required** properties (e.g. `methodology`, `turn_number`, `strategy`, `should_continue`, `next_question`, `concept_id`, `mode`, `max_turns`, `focus_concept`) raise `RuntimeError("Pipeline contract violation: <name> accessed before <Stage> completed")` when their producer has not yet written its contract. This is the ordering enforcement.
- **Optional** properties (e.g. `recent_utterances`, `graph_state`, `recent_nodes`, `nodes_added`, `edges_added`, `signals`, `node_signals`, `extraction`, `user_utterance`, `system_utterance`, `strategy_alternatives`, `scoring`) return `None` / empty list / empty dict when their producer has not run. Callers must guard.
- Service references (notably `node_tracker: NodeStateTracker`) are passed as dataclass fields, not contracts.

### 3. Critical Ordering Invariants

1. **Stage 4 (GraphUpdate) → Stage 5 (StateComputation)**: GraphUpdate writes nodes/edges to SQLite via `GraphRepository`. StateComputation reads back from SQLite via `GraphRepository.get_state()`. There is **no in-memory shortcut**; bypassing the DB round-trip breaks the freshness guarantee. Empty extractions still trigger Stage 5 — `interview_progress` and `saturation_score` change every turn regardless of extraction.
2. **Stage 5 (StateComputation) → Stage 6 (StrategySelection)**: `StrategySelectionInput` has a `model_validator` that compares `state_computation_output.computed_at` against `extraction_output.timestamp`. If `computed_at < extraction.timestamp`, it raises `ValueError("State is stale! ...")`. This catches the class of bugs where Stage 5 ran before Stage 3.
3. **Stage 4 (GraphUpdate) → Stage 6 (StrategySelection)**: `NodeStateTracker.register_node()` and `record_yield()` execute in Stage 4, **before** signal detectors in Stage 6 read tracker state. Any Stage-4 mutation is visible to Stage-6 signals within the same turn. Conversely, anything reset in Stage 4 (e.g. a streak reset) is invisible to Stage 6 — signals will always see 0.
4. **Stage 10 must always run.** It is the only place that:
   - Writes `session.state.turn_count = turn_number` back to DB → without it, the next turn loads the same `turn_count`, recomputes the same `turn_number`, and the interview loops forever at the same turn.
   - Calls `NodeStateTracker.to_dict()` and persists it to `sessions.node_tracker_state` → without it, all per-node state mutations from this turn are lost.
   - Writes `FocusEntry` to focus_history → without it, the cross-turn focus trace breaks.
   - Assembles `TurnResult` for the API response.
   Any early return / exception path before Stage 10 must be treated as a P0 bug.

### 4. Optional Stages: Skip Semantics

Stage 2.5 (SRL, `settings.enable_srl`) and Stage 4.5 (SlotDiscovery, `settings.enable_canonical_slots`) are gated by feature flags. **When skipped, they MUST write a default/empty contract to the context field — never `None`.** Downstream code does not null-guard these contracts; it accesses fields directly (e.g. `context.srl_preprocessing_output.discourse_relations` should return `[]`, not raise `AttributeError`). If an optional stage's skip path leaves the field as `None`, downstream code that expected a contract will explode. Verify the empty-contract write in any new optional stage.

### 5. turn_count vs turn_number

Two distinct values track interview progress:

- `session.state.turn_count` (DB): completed turns. Starts at 0.
- `context.turn_number` (in-memory, derived in Stage 1): `(session.state.turn_count or 0) + 1`. The turn currently being processed.

Flow: Stage 1 loads `turn_count` from DB → sets `context.turn_number = turn_count + 1` → flows through stages → Stage 5 syncs `turn_number` into `graph_state.turn_count` → Stage 7 compares `turn_number >= max_turns` → Stage 10 writes `session.state.turn_count = turn_number` back to DB.

`max_turns` is **computed as the sum of all phase `n_turns`** in `config/interview_config.yaml` (e.g. `exploratory:6 + focused:7 + closing:2 = 15`). Never hardcode it. If a phase is missing from YAML, the interview length silently changes.

Phase detection (`InterviewPhaseSignal` → `meta.interview.phase`) maps `turn_number` against cumulative phase boundaries (e.g. `<=6 early`, `<=13 mid`, `>13 late`).

### 6. NodeStateTracker Lifecycle Within the Pipeline

| Stage | Method called | Effect |
|---|---|---|
| 1 | `from_dict(session.node_tracker_state)` | Deserialize tracker; raise `ValueError` on schema version mismatch |
| 4 | `register_node(node, turn_number)` | Init `NodeState` for newly extracted nodes |
| 4 | `update_edge_counts(node_id, ±, ±)` | Adjust outgoing/incoming counts |
| 4 | `record_yield(node_id, turn_number, graph_changes)` | Credit `previous_focus` with this turn's graph changes; reset `turns_since_last_yield = 0`; increment `yield_count`. **Does NOT touch `current_focus_streak`** — resetting streak here would make Stage-6 signals always read 0. |
| 6 | (signal detection reads tracker state) | `graph.node.focus_streak`, `graph.node.exhaustion_score`, etc. |
| 6 | `update_focus(node_id, turn_number, strategy)` | Increment `focus_count`; set streak (=1 on focus change, +=1 on same focus); tick `turns_since_last_yield += 1` for **ALL** nodes |
| 6 | `append_response_signal(focus_node_id, response_depth)` | Append depth label to previous focus node |
| 10 | `to_dict()` → save to `sessions.node_tracker_state` | Persist tracker. **Mutations after Stage 10 are lost.** |

### 7. TurnResult Assembly

`TurnResult` is constructed in `ScoringPersistenceStage` (Stage 10) by reading the completed `PipelineContext`. Fields include: `turn_number`, `extracted`, `graph_state`, `scoring`, `strategy_selected`, `next_question`, `should_continue`, `signals`, `strategy_alternatives`, `canonical_graph`, `graph_comparison`, `nodes_added`, `edges_added`, `saturation_metrics`, `node_signals`, `score_decomposition`, `termination_reason`. **Any field that is not explicitly forwarded here is silently absent from the API response.** Missing fields in API responses always trace to Stage 10 assembly, never to the producing stage itself.

### 8. Freshness Guarantee Mechanics

`StateComputationOutput.computed_at` is the freshness anchor. `StrategySelectionInput.verify_state_freshness()` enforces `computed_at >= extraction.timestamp`. This is the only place the invariant is checked at runtime — relying on stage ordering alone is insufficient because someone can wire stages incorrectly in `_build_pipeline()`. Trust the validator; if it raises, the pipeline wiring is wrong.

### 9. Contract Field Access

Contracts are Pydantic `BaseModel` instances. Use **attribute access** (`output.field`), not subscription (`output["field"]`). An undefined field raises `AttributeError` at runtime, not `KeyError`. This distinction matters for debugging: a `KeyError` on a stage output means someone treated the contract as a dict and the bug is at that call site.

## Key Constraints

1. Never read a contract from a later-numbered stage. If you need data Stage N produces, you must run as Stage ≥ N+1.
2. Never write `None` to an optional stage's context field on skip — write an empty/default contract instance.
3. Never bypass Stage 10. Wrap the entire pipeline in error handling that still routes through Stage 10's persistence on failure paths, or accept that turn_count and tracker state will desync.
4. Never reset `NodeStateTracker` fields in Stage 4 that Stage 6 signals read. Resets that need to be visible to signals must happen *after* signal detection, inside `update_focus()`.
5. Never hardcode `max_turns`. Always sum `phases[*].n_turns` from config.
6. Never bypass the GraphUpdate → DB → StateComputation round-trip. The DB write is the freshness boundary.
7. Always update `TurnResult` assembly in Stage 10 when adding a new field that should reach the API response.
8. Always use attribute access (`.field`) on contracts, not `["field"]`.
9. When a property raises `RuntimeError: Pipeline contract violation`, fix the *stage ordering* in `session_service._build_pipeline()` — do not paper over with `getattr(...)` or try/except.

## Anti-patterns

- **Stale-state reset.** Resetting `current_focus_streak = 0` inside `record_yield()` (Stage 4). Stage 6 signals then always read 0 because they run after Stage 4. (Real bug, bead 119q: node targeting locked to one node for 16 turns; all 51 candidates scored identically.) Fix: only reset streak inside `update_focus()` on focus change.
- **Skipping Stage 10 in an error path.** Catching an exception in Stage 6/8/9 and returning early. `turn_count` doesn't increment, `NodeStateTracker` state is lost, focus_history doesn't grow, and the next turn re-processes the same `turn_number` indefinitely.
- **Optional stage writing `None`.** A skip branch that does `context.srl_preprocessing_output = None` instead of `SrlPreprocessingOutput()`. Downstream `context.srl_preprocessing_output.discourse_relations` then raises `AttributeError: 'NoneType' object has no attribute 'discourse_relations'`.
- **Dict-style contract access.** Writing `output["strategy"]` against `StrategySelectionOutput`. Pydantic models are not subscriptable; this raises `TypeError`. The fix is `.strategy`, never `getattr(output, "strategy", None)`.
- **In-memory graph_state shortcut.** Passing `nodes_added` directly into Stage 5 to "save a DB query." Breaks the freshness guarantee; later turns will see metrics that include rolled-back rows or miss merged nodes.
- **Mutating graph_state after Stage 5.** Any code path that modifies graph data after StateComputationStage without re-running Stage 5 leaves Stage 6 reading stale `node_count`, `edge_count`, `saturation_metrics`. The freshness validator only catches Stage-3-vs-Stage-5 inversion, not post-hoc Stage-5 mutation.
- **Hardcoded `max_turns`.** Anything like `max_turns = 15` in code instead of summing `phases[*].n_turns`. Silently desyncs from YAML and from `InterviewPhaseSignal` boundaries.
- **Forgetting to wire a new field into `TurnResult`.** Adding a contract field in Stage 6 (e.g. a new signal) and observing it works in tests against the contract, but it never appears in the API response because Stage 10's `TurnResult` assembly was not updated.
- **Using `.get()` / `getattr(..., default)` on a contract to "fix" a missing field.** This is masking upstream data loss or a wrong stage ordering. Trace the field back to its producer; the bug is there, not at the access site.
- **Removing the `GraphUpdate → record_yield` call** thinking signals will pick it up later. Stage 6 reads, never writes; if Stage 4 doesn't yield-credit, no later stage will.

## Context Documents

- `.claude/context/pipeline-contracts.md` — full contract spec, freshness guarantee, optional-stage skip rules
- `.claude/context/turn-count.md` — `turn_count` vs `turn_number`, `max_turns` derivation, phase boundaries
- `.claude/context/graph-mutation.md` — Extraction → GraphUpdate → StateComputation flow, dedup, DB round-trip
- `.claude/context/node-state-tracker.md` — `NodeState` fields, per-stage method table, dual-graph resolution
- `src/services/turn_pipeline/context.py` — `PipelineContext` dataclass and convenience properties
- `src/domain/models/pipeline_contracts.py` — all 12 Pydantic contracts, including `StrategySelectionInput.verify_state_freshness`
- `src/services/session_service.py` — `_build_pipeline()` stage wiring (the source of truth for ordering)
- `src/services/turn_pipeline/stages/scoring_persistence_stage.py` — `TurnResult` assembly
- `src/services/turn_pipeline/result.py` — `TurnResult` shape
