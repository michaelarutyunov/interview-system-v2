# Pipeline Contracts

## Core Mechanics

`PipelineContext` is an accumulator dataclass that carries state through all turn pipeline stages. Each stage writes its Pydantic output contract into a dedicated field on the context, and later stages read from those fields. Ordering is enforced at runtime: convenience properties on `PipelineContext` raise `RuntimeError` if accessed before their producing stage has written its output.

All contracts are Pydantic `BaseModel` subclasses defined in `src/domain/models/pipeline_contracts.py`. Contracts are the single source of truth — there is no parallel mutable state alongside them.

Convenience properties on `PipelineContext` derive computed values from contracts (e.g. `context.strategy` reads `context.strategy_selection_output.strategy`). These properties exist for ergonomic access and backward compatibility; they do not duplicate state.

### Stage → Contract Table

| Stage | Stage Name | Contract Class | Key Fields |
|-------|-----------|----------------|------------|
| 1 | ContextLoadingStage | `ContextLoadingOutput` | `methodology`, `concept_id`, `concept_name`, `turn_number`, `mode`, `max_turns`, `recent_utterances`, `strategy_history`, `recent_node_labels`, velocity state, `focus_history` (each `FocusEntry` includes `node_type` field for strategy-aware level hints) |
| 2 | UtteranceSavingStage | `UtteranceSavingOutput` | `turn_number`, `user_utterance_id`, `user_utterance` |
| 2.5 | SRLPreprocessingStage | `SrlPreprocessingOutput` | `discourse_relations`, `srl_frames`, `discourse_count`, `frame_count`, `timestamp` |
| 3 | ExtractionStage | `ExtractionOutput` | `extraction` (ExtractionResult), `methodology`, `timestamp`, `concept_count`, `relationship_count` |
| 4 | GraphUpdateStage | `GraphUpdateOutput` | `nodes_added`, `edges_added`, `node_count`, `edge_count`, `timestamp`. Performs permitted_connections validation for cross-turn edges after dedup resolution. Populates `PipelineContext.concept_to_node_id` (keyed by `concept.text.lower()`) for the per-concept→node bridge consumed in Stage 6. |
| 4.5 | SlotDiscoveryStage | `SlotDiscoveryOutput` | `slots_created`, `slots_updated`, `mappings_created`, `timestamp` |
| 5 | StateComputationStage | `StateComputationOutput` | `graph_state`, `recent_nodes`, `computed_at`, `saturation_metrics`, `canonical_graph_state` |
| 6 | StrategySelectionStage | `StrategySelectionOutput` | `strategy`, `focus`, `selected_at`, `signals`, `node_signals`, `strategy_alternatives` (uniform 3-tuples `(strategy, node_id_or_None, score)`), `generates_closing_question`, `focus_mode`, `score_decomposition` (unified joint scoring output), `threshold_fallback` |
| 7 | ContinuationStage | `ContinuationOutput` | `should_continue`, `focus_concept` (Union[str, Dict[str, str]] — dict with `label`+`node_type` when resolved from graph node, plain string for backward compat/when not continuing), `reason`, `turns_remaining`, `timestamp` |
| 8 | QuestionGenerationStage | `QuestionGenerationOutput` | `question`, `strategy`, `focus`, `has_llm_fallback`, `timestamp`. Forwards `signals` + `signal_descriptions` from Stage 6 and `focus_node_type` from Stage 7 to the question prompt, enabling signal rationale and node-type-aware question generation. For `revitalize` strategy, prepends the opening interviewer question to the context window so the generator avoids repeating previously covered topics. |
| 9 | ResponseSavingStage | `ResponseSavingOutput` | `turn_number`, `system_utterance_id`, `system_utterance`, `question_text`, `timestamp` |
| 10 | ScoringPersistenceStage | `ScoringPersistenceOutput` | `turn_number`, `strategy`, `depth_score`, `saturation_score`, `has_methodology_signals`, `timestamp` |

### Freshness Guarantee

`StateComputationOutput` carries a `computed_at` timestamp. `StrategySelectionInput` (the input contract for Stage 6) has a `model_validator` that compares `computed_at` against `extraction.timestamp` and raises `ValueError` if the graph state predates the extraction. This prevents a class of stale-state bugs where Stage 5 output from before Stage 3 was inadvertently used.

### Optional Stages

Stage 2.5 (SRL) is gated by `settings.enable_srl`. Stage 4.5 (SlotDiscovery) is gated by `settings.enable_canonical_slots`. When a stage is skipped, it still writes a default/empty contract to its context field — it does not leave the field as `None`. Downstream stages can safely access these contracts without null-guarding.

### TurnResult Assembly

`ScoringPersistenceStage` (Stage 10) assembles the final `TurnResult` from the completed context. Any field that is not forwarded from a contract at this point will be absent from the API response. Missing fields in the API response always trace back to this assembly, not to the pipeline stages themselves.

### Strategy Selection (Stage 6) Details

**StrategyConfig.valid_when gate.** Each `StrategyConfig` (defined in `src/methodologies/registry.py`) has an optional `valid_when` field — a string naming a boolean signal. When set, the (strategy, node) pair is skipped during joint scoring if the named signal is not `True` in the node's signal dict. This gates chain-aware strategies (e.g., `bridge`, `branch`, `anchor`) so they are only scored when chain topology signals indicate a relevant graph structure. Strategies without `valid_when` are always eligible.

**Per-concept → node bridge.** Between global and node signal detection, Stage 6 iterates `per_concept_ratings` from `GlobalSignalDetectionService.detect_with_per_concept()` and, for each concept whose name appears in `context.concept_to_node_id`, calls `node_tracker.append_quality(node_id, elaboration, charge)`. This populates `NodeState.quality_history` so the downstream `graph.node.elaboration` / `graph.node.charge` / `graph.node.has_quality_data` signals have fresh data within the same turn.

**Joint scoring architecture.** `MethodologyStrategyService.select_strategy_and_focus()` partitions strategies by `node_binding`:
- `node_binding='required'` strategies are scored via `rank_strategy_node_pairs()` — each (strategy, node) pair gets merged global+node signals, valid_when gates filter ineligible pairs
- `node_binding='none'` strategies (e.g., revitalize) are scored via `rank_strategies()` — global signals only, node_id is None

Both candidate pools are merged and sorted by score. The highest-scoring pair determines both the selected strategy and the target node. This replaces the former 2-stage architecture where Stage 1 selected strategy and Stage 2 selected node for only the Stage 1 winner.

**Threshold fallback.** When the best joint-scored candidate falls below the configured score threshold, `MethodologyStrategyService` checks for global fatigue (`llm.global_response_trend == "fatigued"`) or low engagement (`llm.engagement < 0.3`). If either condition is true, the `revitalize` strategy is selected as a fallback and the event is logged as `strategy_threshold_fallback` with the reason `global_fatigue_or_low_engagement`. If no fallback condition is met, the best candidate is used despite the low score (logged as `strategy_threshold_below_but_no_fallback`).

**MEC methodology strategies.** The Means-End Chain methodology family (means_end_chain, means_end_chain_v2_strict, means_end_chain_v3_flex) now defines six strategies: `ascend`, `ground`, `bridge`, `branch`, `anchor`, `revitalize`. The first five are chain-aware (some use `valid_when` gates); `revitalize` serves as the engagement-recovery fallback.

**Default strategy.** The code default is `ascend` (was `deepen`). This is the strategy used when no strategy is explicitly specified, e.g., in `QuestionService` and as the initial strategy before signal-driven selection produces a result.

---

## Correctness Requirements

1. Each stage reads only contracts from stages with lower stage numbers — no forward access is permitted. Accessing a contract field before its producing stage runs will either return `None` (for Optional properties) or raise `RuntimeError` (for required properties with ordering enforcement).
2. Contracts are Pydantic `BaseModel` instances — accessing an undefined field raises `AttributeError` at runtime, not `KeyError`. This distinguishes contract access errors from dict access errors.
3. `StateComputationOutput` must be written before `StrategySelectionOutput` is produced. The graph-state freshness validator on `StrategySelectionInput` enforces this by checking that `computed_at >= extraction.timestamp`.
4. Optional stages (2.5 and 4.5) write their contracts even when skipped — they write empty/default contracts, not `None`. This ensures downstream code accessing e.g. `context.srl_preprocessing_output.discourse_relations` gets an empty list rather than an `AttributeError`.
5. `TurnResult` is assembled from the final context in `ScoringPersistenceStage` — missing fields there propagate directly as missing fields in the API response.
6. GraphUpdateStage performs permitted_connections validation for cross-turn edges after dedup resolution. Edges violating the methodology schema are rejected with `invalid_connection_post_dedup` log. This validation uses the resolved KGNode types (post-dedup), not the LLM-assigned types from extraction.

---

## Symptom → Cause → Fix

| Symptom | Cause | Fix |
|---------|-------|-----|
| `RuntimeError: Pipeline contract violation: <property> accessed before <Stage> completed` | A stage is reading a contract from a stage that hasn't run yet | Check stage execution ordering in `session_service.py:_build_pipeline()`; ensure the producing stage runs before the consuming one |
| `AttributeError` on contract field access (e.g. `output.some_field`) | Field not defined in the Pydantic model | Check the contract class definition in `src/domain/models/pipeline_contracts.py` and add the missing field |
| Skipped optional stage causes `AttributeError` or `NoneType` error downstream | Skip logic set the context field to `None` instead of writing a default contract | Verify that the skip path in the optional stage writes an empty contract (all-defaults instance), not `None` |
| API response missing a field that is computed in the pipeline | `ScoringPersistenceStage` assembly did not forward the field into `TurnResult` | Inspect `ScoringPersistenceStage` to find where `TurnResult` is constructed and add the missing field mapping |
| `ValueError: State is stale!` raised during strategy selection | `StateComputationStage` (Stage 5) ran before `ExtractionStage` (Stage 3), so `computed_at < extraction.timestamp` | Ensure pipeline stage order places Stage 5 after Stage 3 |
| Cross-turn edges accepted despite violating permitted_connections | ExtractionService only validates current-turn concepts; cross-turn edges bypass validation | GraphUpdateStage now validates post-dedup; check for `invalid_connection_post_dedup` log if edges are unexpectedly rejected |
| Strategy never appears in scored candidates despite being in YAML | Strategy has `valid_when` gate and the named signal is `False`/`None`/missing for all nodes | Check `strategy_node_pair_gated` log entries; verify the gate signal is being produced by the relevant signal detector |
| `revitalize` selected unexpectedly (score was adequate for another strategy) | Global fatigue or low engagement triggered threshold fallback, overriding the best-scored candidate | Check `strategy_threshold_fallback` log for `global_fatigue_or_low_engagement` reason; inspect `graph.global_fatigue` and `llm.engagement` signal values |

---

## Key Files

- `src/services/turn_pipeline/context.py` — `PipelineContext` dataclass: contract fields, ordering-enforced convenience properties, `current_turn_global_signals` for current-turn LLM signal access
- `src/domain/models/pipeline_contracts.py` — All 12 contract Pydantic models
- `src/services/session_service.py` — `_build_pipeline()`: stage wiring and execution order
- `src/services/turn_pipeline/stages/scoring_persistence_stage.py` — `TurnResult` assembly from final context
- `src/services/graph_service.py` — Cross-turn edge validation in `_add_edge_from_relationship()` (see `graph-dedup.md`)
- `src/methodologies/registry.py` — `StrategyConfig` with `valid_when` gate; `MethodologyConfig` with strategy list
- `src/methodologies/scoring.py` — Joint strategy-node scoring with `valid_when` gate filtering; `ScoredCandidate` decomposition
