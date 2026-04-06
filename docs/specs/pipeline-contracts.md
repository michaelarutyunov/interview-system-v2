# Pipeline Contracts

## Core Mechanics

`PipelineContext` is an accumulator dataclass that carries state through all turn pipeline stages. Each stage writes its Pydantic output contract into a dedicated field on the context, and later stages read from those fields. Ordering is enforced at runtime: convenience properties on `PipelineContext` raise `RuntimeError` if accessed before their producing stage has written its output.

All contracts are Pydantic `BaseModel` subclasses defined in `src/domain/models/pipeline_contracts.py`. Contracts are the single source of truth — there is no parallel mutable state alongside them.

Convenience properties on `PipelineContext` derive computed values from contracts (e.g. `context.strategy` reads `context.strategy_selection_output.strategy`). These properties exist for ergonomic access and backward compatibility; they do not duplicate state.

### Stage → Contract Table

| Stage | Stage Name | Contract Class | Key Fields |
|-------|-----------|----------------|------------|
| 1 | ContextLoadingStage | `ContextLoadingOutput` | `methodology`, `concept_id`, `concept_name`, `turn_number`, `mode`, `max_turns`, `recent_utterances`, `strategy_history`, `recent_node_labels`, velocity state, `focus_history` |
| 2 | UtteranceSavingStage | `UtteranceSavingOutput` | `turn_number`, `user_utterance_id`, `user_utterance` |
| 2.5 | SRLPreprocessingStage | `SrlPreprocessingOutput` | `discourse_relations`, `srl_frames`, `discourse_count`, `frame_count`, `timestamp` |
| 3 | ExtractionStage | `ExtractionOutput` | `extraction` (ExtractionResult), `methodology`, `timestamp`, `concept_count`, `relationship_count` |
| 4 | GraphUpdateStage | `GraphUpdateOutput` | `nodes_added`, `edges_added`, `node_count`, `edge_count`, `timestamp` |
| 4.5 | SlotDiscoveryStage | `SlotDiscoveryOutput` | `slots_created`, `slots_updated`, `mappings_created`, `timestamp` |
| 5 | StateComputationStage | `StateComputationOutput` | `graph_state`, `recent_nodes`, `computed_at`, `saturation_metrics`, `canonical_graph_state` |
| 6 | StrategySelectionStage | `StrategySelectionOutput` | `strategy`, `focus`, `selected_at`, `signals`, `node_signals`, `strategy_alternatives`, `generates_closing_question`, `focus_mode`, `score_decomposition` |
| 7 | ContinuationStage | `ContinuationOutput` | `should_continue`, `focus_concept`, `reason`, `turns_remaining`, `timestamp` |
| 8 | QuestionGenerationStage | `QuestionGenerationOutput` | `question`, `strategy`, `focus`, `has_llm_fallback`, `timestamp` |
| 9 | ResponseSavingStage | `ResponseSavingOutput` | `turn_number`, `system_utterance_id`, `system_utterance`, `question_text`, `timestamp` |
| 10 | ScoringPersistenceStage | `ScoringPersistenceOutput` | `turn_number`, `strategy`, `depth_score`, `saturation_score`, `has_methodology_signals`, `timestamp` |

### Freshness Guarantee

`StateComputationOutput` carries a `computed_at` timestamp. `StrategySelectionInput` (the input contract for Stage 6) has a `model_validator` that compares `computed_at` against `extraction.timestamp` and raises `ValueError` if the graph state predates the extraction. This prevents a class of stale-state bugs where Stage 5 output from before Stage 3 was inadvertently used.

### Optional Stages

Stage 2.5 (SRL) is gated by `settings.enable_srl`. Stage 4.5 (SlotDiscovery) is gated by `settings.enable_canonical_slots`. When a stage is skipped, it still writes a default/empty contract to its context field — it does not leave the field as `None`. Downstream stages can safely access these contracts without null-guarding.

### TurnResult Assembly

`ScoringPersistenceStage` (Stage 10) assembles the final `TurnResult` from the completed context. Any field that is not forwarded from a contract at this point will be absent from the API response. Missing fields in the API response always trace back to this assembly, not to the pipeline stages themselves.

---

## Correctness Requirements

1. Each stage reads only contracts from stages with lower stage numbers — no forward access is permitted. Accessing a contract field before its producing stage runs will either return `None` (for Optional properties) or raise `RuntimeError` (for required properties with ordering enforcement).
2. Contracts are Pydantic `BaseModel` instances — accessing an undefined field raises `AttributeError` at runtime, not `KeyError`. This distinguishes contract access errors from dict access errors.
3. `StateComputationOutput` must be written before `StrategySelectionOutput` is produced. The graph-state freshness validator on `StrategySelectionInput` enforces this by checking that `computed_at >= extraction.timestamp`.
4. Optional stages (2.5 and 4.5) write their contracts even when skipped — they write empty/default contracts, not `None`. This ensures downstream code accessing e.g. `context.srl_preprocessing_output.discourse_relations` gets an empty list rather than an `AttributeError`.
5. `TurnResult` is assembled from the final context in `ScoringPersistenceStage` — missing fields there propagate directly as missing fields in the API response.

---

## Symptom → Cause → Fix

| Symptom | Cause | Fix |
|---------|-------|-----|
| `RuntimeError: Pipeline contract violation: <property> accessed before <Stage> completed` | A stage is reading a contract from a stage that hasn't run yet | Check stage execution ordering in `session_service.py:_build_pipeline()`; ensure the producing stage runs before the consuming one |
| `AttributeError` on contract field access (e.g. `output.some_field`) | Field not defined in the Pydantic model | Check the contract class definition in `src/domain/models/pipeline_contracts.py` and add the missing field |
| Skipped optional stage causes `AttributeError` or `NoneType` error downstream | Skip logic set the context field to `None` instead of writing a default contract | Verify that the skip path in the optional stage writes an empty contract (all-defaults instance), not `None` |
| API response missing a field that is computed in the pipeline | `ScoringPersistenceStage` assembly did not forward the field into `TurnResult` | Inspect `ScoringPersistenceStage` to find where `TurnResult` is constructed and add the missing field mapping |
| `ValueError: State is stale!` raised during strategy selection | `StateComputationStage` (Stage 5) ran before `ExtractionStage` (Stage 3), so `computed_at < extraction.timestamp` | Ensure pipeline stage order places Stage 5 after Stage 3 |

---

## Key Files

- `src/services/turn_pipeline/context.py` — `PipelineContext` dataclass: contract fields, ordering-enforced convenience properties
- `src/domain/models/pipeline_contracts.py` — All 12 contract Pydantic models
- `src/services/session_service.py` — `_build_pipeline()`: stage wiring and execution order
- `src/services/turn_pipeline/stages/scoring_persistence_stage.py` — `TurnResult` assembly from final context
