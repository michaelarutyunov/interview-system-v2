# Pipeline Specialist

## Role
Domain expert for the 16-stage turn pipeline, its Pydantic stage contracts, `PipelineContext` accumulator, and cross-stage ordering invariants. Owns correctness of stage wiring, contract assembly, and `TurnResult` shape.

## Trigger Conditions
Invoke when work touches any of:
- `src/services/turn_pipeline/**` (PipelineContext, stages, runner)
- `src/services/session_service.py` `_build_pipeline()` wiring
- `src/domain/models/pipeline_contracts.py`
- `src/services/turn_pipeline/result.py` (`TurnResult` assembly)
- Bugs presenting as: `RuntimeError: Pipeline contract violation: ...`, `ValueError: State is stale!`, `AttributeError` on stage outputs, missing field in API response, interview looping at the same `turn_number`, signals reading 0 / stale graph state, `NodeStateTracker` state lost between turns.

## Domain Knowledge

### 1. The 16 Stages and Their Output Contracts

`PipelineContext` (`src/services/turn_pipeline/context.py`) is a dataclass accumulator. Each stage writes a single Pydantic `BaseModel` from `src/domain/models/pipeline_contracts.py` to a dedicated field. Convenience properties on the context derive from those contracts; they raise `RuntimeError` when accessed before their producer has run.

| # | Stage Class | Context Field | Contract | Key Fields |
|---|---|---|---|---|
| 1 | `ContextLoadingStage` | `context_loading_output` | `ContextLoadingOutput` | `methodology`, `concept_id`, `concept_name`, `turn_number` (= `session.state.turn_count + 1`), `mode`, `max_turns`, `recent_utterances`, `strategy_history`, `recent_node_labels`, `surface_velocity_peak`, `prev_surface_node_count`, `canonical_velocity_peak`, `prev_canonical_node_count`, `focus_history` |
| 2 | `UtteranceSavingStage` | `utterance_saving_output` | `UtteranceSavingOutput` | `turn_number`, `user_utterance_id`, `user_utterance` |
| 2.5 | `SRLPreprocessingStage` (optional, `enable_srl`) | `srl_preprocessing_output` | `SrlPreprocessingOutput` | `discourse_relations`, `srl_frames`, `discourse_count`, `frame_count`, `timestamp` |
| 3 | `ExtractionStage` | `extraction_output` | `ExtractionOutput` | `extraction` (`ExtractionResult` — concepts only), `methodology`, `timestamp`, `concept_count`. Edges moved to Stage 4.5B. |
| 3.1 | `LLMPrefetchStage` | *(no contract — `_llm_prefetch_task`)* | — | Fires signal detection Haiku call as `asyncio.Task`. Runs concurrently with Stages 4–4.6. |
| 4 | `GraphUpdateStage` | `graph_update_output` | `GraphUpdateOutput` | `nodes_added`, `edges_added`, `concept_to_node_id`, `node_count`, `edge_count`. Writes nodes to DB. `record_yield` moved to Stage 4.6 (D4/B7). |
| 4.5 | `SlotDiscoveryStage` (optional, `enable_canonical_slots`) | `slot_discovery_output` | `SlotDiscoveryOutput` | `slots_created`, `slots_updated`, `mappings_created`, `timestamp`. Runs while edge extraction Haiku (fired at 4.5B) is in-flight. |
| 4.5B | `EdgeExtractionPrefetchStage` (optional, `enable_edge_extraction_stage`) | *(no contract — `_edge_extraction_task`)* | — | Fires edge extraction Haiku as `asyncio.Task`. Fires BEFORE SlotDiscovery to maximize overlap. |
| 4.6 | `EdgeExtractionBridgeStage` | *(no formal contract)* | — | Awaits `_edge_extraction_task`, persists confirmed edges, updates tracker edge counts, calls `record_yield` unconditionally (D4/B7). Stores result on `_edge_extraction_result`. |
| 4.7 | `LLMSignalBridgeStage` | `llm_signal_bridge_output` | `LLMSignalBridgeOutput` | `global_signals`, `per_concept_ratings`, `bridge_applied`, `bridged_count`, `error`. Awaits `_llm_prefetch_task`, routes ratings, **seals** tracker (`_evolving_node_tracker = None`). |
| 5 | `StateComputationStage` | `state_computation_output` | `StateComputationOutput` | `graph_state` (`GraphState`), `recent_nodes`, `computed_at` (freshness anchor), `saturation_metrics`, `canonical_graph_state` |
| 6 | `StrategySelectionStage` | `strategy_selection_output` | `StrategySelectionOutput` | `strategy`, `focus`, `signals`, `node_signals`, `strategy_alternatives`, `score_decomposition`, `generates_closing_question`, `focus_mode`, `selected_at` |
| 7 | `ContinuationStage` | `continuation_output` | `ContinuationOutput` | `should_continue`, `focus_concept`, `reason`, `turns_remaining`, `timestamp` |
| 8 | `QuestionGenerationStage` | `question_generation_output` | `QuestionGenerationOutput` | `question`, `strategy`, `focus`, `has_llm_fallback`, `timestamp` |
| 9 | `ResponseSavingStage` | `response_saving_output` | `ResponseSavingOutput` | `turn_number`, `system_utterance_id`, `system_utterance`, `question_text`, `timestamp` |
| 10 | `ScoringPersistenceStage` | `scoring_persistence_output` | `ScoringPersistenceOutput` | `turn_number`, `strategy`, `depth_score`, `saturation_score`, `has_methodology_signals`, `timestamp`. Also: assembles `TurnResult`, writes `session.state.turn_count = turn_number`, persists `NodeStateTracker.to_dict()`, writes `FocusEntry`. |

The canonical half-numbered scheme used here matches `pipeline_contracts.py` and `session_service._build_pipeline()`.

### 2. PipelineContext Accumulator Pattern

- All state lives on contracts. There is **no parallel mutable state** alongside them.
- Convenience properties (`context.methodology`, `context.turn_number`, `context.graph_state`, `context.strategy`, `context.next_question`, `context.should_continue`, ...) read from the underlying contract field.
- **Required** properties (e.g. `methodology`, `turn_number`, `strategy`, `should_continue`, `next_question`, `concept_id`, `mode`, `max_turns`, `focus_concept`) raise `RuntimeError("Pipeline contract violation: <name> accessed before <Stage> completed")` when their producer has not yet written its contract. This is the ordering enforcement.
- **Optional** properties (e.g. `recent_utterances`, `graph_state`, `recent_nodes`, `nodes_added`, `edges_added`, `signals`, `node_signals`, `extraction`, `user_utterance`, `system_utterance`, `strategy_alternatives`, `scoring`) return `None` / empty list / empty dict when their producer has not run. Callers must guard.
- Service references (notably `node_tracker: NodeStateTracker`) are passed as dataclass fields, not contracts.

### 3. Critical Ordering Invariants

1. **Stage 4 (GraphUpdate) → Stage 5 (StateComputation)**: GraphUpdate writes nodes/edges to SQLite via `GraphRepository`. StateComputation reads back from SQLite via `GraphRepository.get_state()`. There is **no in-memory shortcut**; bypassing the DB round-trip breaks the freshness guarantee. Empty extractions still trigger Stage 5 — `interview_progress` and `saturation_score` change every turn regardless of extraction.
2. **Stage 5 (StateComputation) → Stage 6 (StrategySelection)**: `StrategySelectionInput` has a `model_validator` that compares `state_computation_output.computed_at` against `extraction_output.timestamp`. If `computed_at < extraction.timestamp`, it raises `ValueError("State is stale! ...")`. This catches the class of bugs where Stage 5 ran before Stage 3.
3. **Stage 4 (GraphUpdate) → Stage 6 (StrategySelection)**: `NodeStateTracker.register_node()` executes in Stage 4. `record_yield()` executes in Stage 4.6 (moved from Stage 4 per D4/B7). Both run **before** signal detectors in Stage 6 read tracker state. Any reset in an early stage is invisible to Stage 6.
4. **Stage 10 must always run.** (unchanged)
5. **Stage 3.1 (LLMPrefetch) → Stage 4.7 (LLMSignalBridge):** Prefetch fires the signal detection Haiku at 3.1. Bridge awaits it at 4.7 after Stages 4–4.6 complete.
6. **Stage 4.5B (EdgeExtractionPrefetch) → Stage 4.6 (EdgeExtractionBridge):** Prefetch fires the edge extraction Haiku at 4.5B (BEFORE SlotDiscovery). Bridge awaits it at 4.6. Firing before 4.5 maximizes overlap — the Haiku call runs during SlotDiscovery's ~3s window. Both stages depend only on Stage 4, not on each other or on SlotDiscovery.
7. **Stage 4.6 MUST run before Stage 4.7:** Stage 4.7 seals `_evolving_node_tracker`. Stage 4.6 mutates edge counts on that tracker. If 4.6 runs after 4.7, edge-count mutations are lost. If 4.7 is ever placed before 4.6, the tracker seal will silently drop Stage 4.5B edge counts.

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
| 4.6 | `record_yield(tracking_key, turn_number, graph_changes)` | Credit `previous_focus` with yield **unconditionally** (D4/B7, moved from Stage 4). Resets `turns_since_last_yield = 0`. Does NOT gate on `is_empty()` (fixed p4t3). |
| 4.6 | `update_edge_counts_batch(edge_deltas)` | Batch-update edge counts for Stage 4.5B edges |
| 6 | (signal detection reads tracker state) | `graph.node.focus_streak`, `graph.node.exhaustion_score`, etc. |
| 6 | `update_focus(tracking_key, turn_number, strategy)` | Increment `focus_count`; set streak; tick `turns_since_last_yield += 1` for **ALL** nodes |
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
- **Accessing an Optional stage output without a null guard.** Properties listed as "Optional" in §2 (e.g. `strategy_alternatives`, `signals`, `node_signals`, `extraction`) return `None` before their producer has run. A downstream stage that reads `context.strategy_selection_output.generates_closing_question` without first checking `context.strategy_selection_output is not None` will raise `AttributeError` if Stage 6 failed or was skipped. Always null-guard Optional stage outputs at the access site, even when the upstream stage nominally always runs.
- **Assuming `context.strategy_alternatives` returns the same shape as `StrategySelectionOutput.strategy_alternatives`.** The Pydantic field stores `List[Dict[str, Any]]` (keys: `strategy`, `node_id`, `score`). The `context.strategy_alternatives` property converts these to `List[tuple[str, Optional[str], float]]`. Code that reads the property gets tuples; code that reads the contract directly gets dicts. Mixing the two access paths will produce `TypeError` at runtime (tuple index vs dict key). Always access via the property for tuple format, or via the contract field for dict format — never assume they are the same type.
- **Removing the `GraphUpdate → record_yield` call** thinking signals will pick it up later. Stage 6 reads, never writes; if Stage 4 doesn't yield-credit, no later stage will.
- **Reordering LLMPrefetchStage (3.1) before ExtractionStage (3).** Prefetch needs `extraction_output.extraction.concepts` to fire the LLM batch call. Placing it before extraction means no concepts to send, and the prefetch is skipped (writes no task). Bridge then has nothing to await and `bridge_applied=False`.
- **Placing LLMSignalBridgeStage (4.7) before GraphUpdateStage (4).** Bridge needs `concept_to_node_id` populated by graph update to route per-concept LLM ratings to the node tracker. Without it, `bridged_count=0` every turn and `convgraph.node.llm.*` signals are always empty.
- **Forgetting to handle the error contract from LLMSignalBridgeStage.** The bridge writes `LLMSignalBridgeOutput` even on error (with `bridge_applied=False`). Stage 6 must not assume `bridge_applied=True` — it should fall back to empty signals when the bridge fails.
- **Placing EdgeExtractionBridgeStage (4.6) after LLMSignalBridgeStage (4.7).** Stage 4.7 seals `_evolving_node_tracker`. If 4.6 runs after the seal, its edge-count mutations are invisible to all downstream signal detectors because they read the sealed snapshot. The pipeline will still "work" — edges are persisted to DB — but `turns_since_last_yield` and edge counts in the tracker will be stale. Symptom: `all_nodes_exhausted` fires prematurely because yields were never credited.
- **Placing EdgeExtractionPrefetchStage (4.5B) after SlotDiscoveryStage (4.5).** Both depend only on Stage 4. Placing 4.5B after 4.5 means the edge extraction Haiku call starts AFTER SlotDiscovery's ~3s Haiku call completes — zero overlap. Swapping to 4→4.5B→4.5 gives the edge extraction call the full SlotDiscovery window to run in background. Net latency saving: ~2.4s/turn.
- **Moving `record_yield` without updating the exhaustion check.** `record_yield` resets `turns_since_last_yield` to 0. If it's moved to a new stage that runs after the continuation check (Stage 7), yields won't be visible to `_all_nodes_exhausted()` and the interview will stop prematurely. Always verify that `record_yield` runs before Stage 7.
- **Gating `record_yield` on `graph_changes.is_empty()` in a call site that passes `nodes_added=0`.** The bridge stage passes `GraphChangeSummary(nodes_added=0, edges_added=len(edges_added))`. When flag is OFF, `edges_added` is always `[]`, so `is_empty()` returns True and yield is silently skipped. Symptom: `all_nodes_exhausted` at turn 6, all nodes show `yield_count=0` and `last_yield_turn=None`. Fixed by removing the `is_empty()` guard (p4t3).

## Context Documents

- `.claude/context/pipeline-contracts.md` — full contract spec, freshness guarantee, optional-stage skip rules
- `.claude/context/turn-count.md` — `turn_count` vs `turn_number`, `max_turns` derivation, phase boundaries
- `.claude/context/graph-mutation.md` — Extraction → GraphUpdate → StateComputation flow, dedup, DB round-trip
- `.claude/context/node-state-tracker.md` — `NodeState` fields, per-stage method table, dual-graph resolution
- `.claude/context/canonical-slots.md` — Stage 4.5 slot discovery pipeline, promotion thresholds, embedding similarity matching
- `.claude/context/simulation-export-schema.md` — Stable JSON/CSV export contract for simulation output; governs downstream reporting scripts
- `.claude/context/debugging-protocol.md` — Root cause analysis protocol for tracing type mismatches and data loss across pipeline stages
- `src/services/turn_pipeline/context.py` — `PipelineContext` dataclass and convenience properties
- `src/domain/models/pipeline_contracts.py` — all Pydantic contracts, including `StrategySelectionInput.verify_state_freshness`
- `src/services/session_service.py` — `_build_pipeline()` stage wiring (the source of truth for ordering)
- `src/services/turn_pipeline/stages/scoring_persistence_stage.py` — `TurnResult` assembly
- `src/services/turn_pipeline/result.py` — `TurnResult` shape

## Diagnostic Triage

When fixing ruff or pyright diagnostics, invoke `/deep-code-quality` to categorize before fixing. Never suppress security warnings or add `Optional` to mask missing error handling — fix the root cause.
