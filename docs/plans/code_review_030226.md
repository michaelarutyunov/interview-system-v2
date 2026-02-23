# Code Review: Graph-Led Interviewing System POC

**Date**: 2026-02-03
**Reviewer**: Claude Opus 4.5
**Scope**: Full codebase review post-refactoring

---

## 1. Architecture & Pipeline Assessment

### Overall Coherence Rating: **Strong (8/10)**

The architecture demonstrates clear separation of concerns with a well-designed 10-stage pipeline pattern. The refactoring has produced a coherent system with explicit contract-based data flow.

### Key Architectural Strengths

1. **Contract-Based Pipeline Design** (`src/domain/models/pipeline_contracts.py`)
   - Each stage produces a formal Pydantic contract output
   - Contracts provide runtime validation and type safety
   - The `PipelineContext` derives all state from contracts via properties, preventing state duplication

2. **Clean Stage Boundaries** (`src/services/turn_pipeline/pipeline.py`)
   - Sequential execution with clear timing instrumentation
   - Errors propagate properly (re-raised after logging)
   - Each stage has single responsibility

3. **Signal Pools Architecture** (`src/methodologies/signals/registry.py`)
   - Namespaced signals (graph.*, llm.*, temporal.*, meta.*)
   - Composable signal detection from YAML configs
   - Clear separation of global vs node-level signals

4. **ADR-010 Freshness Validation** (`src/services/turn_pipeline/stages/strategy_selection_stage.py:68-95`)
   - `StrategySelectionInput` validates that graph_state isn't stale
   - Prevents the documented "stale state bug"

### Areas Where Flow Could Be Clearer

1. **Placeholder GraphState in ContextLoadingStage** (`src/services/turn_pipeline/stages/context_loading_stage.py:119-140`)
   - Stage 1 creates a placeholder `GraphState` that Stage 5 later replaces
   - This is documented but creates conceptual confusion about when `graph_state` is valid

2. **Temporal Coupling in Focus Selection** (`src/services/turn_pipeline/stages/continuation_stage.py:87-109`)
   - Focus concept resolution involves checking `focus_node_id`, then falling back to `focus_description`, then falling back to heuristic selection
   - Multiple fallback levels obscure the intended behavior

3. **Service Dependencies Not Explicit** (`src/services/turn_pipeline/stages/question_generation_stage.py:37-82`)
   - Stages receive services via constructor injection but dependencies aren't type-annotated in constructors
   - Makes it harder to understand service requirements at a glance

### Files Exemplifying Good Structure

| File | What It Does Well |
|------|-------------------|
| `src/methodologies/scoring.py` | Pure functions with clear inputs/outputs, no hidden state |
| `src/domain/models/pipeline_contracts.py` | Strong type validation with model_validators |
| `src/domain/models/knowledge_graph.py` | Domain model with consistency validation |

### Files With Unclear Structure

| File | Issue |
|------|-------|
| `src/services/turn_pipeline/context.py` | 30+ properties that derive from Optional contracts with silent default returns |
| `src/services/methodology_strategy_service.py` | Single method does detection + scoring + ranking - would benefit from decomposition |

---

## 2. Domain Logic Review

### How Well Domain Concepts Are Expressed

**Rating: Good (7/10)**

The domain model is well-typed with clear entity boundaries. Key domain concepts are properly encapsulated:

1. **GraphState** (`src/domain/models/knowledge_graph.py:88-180`)
   - Structured metrics (DepthMetrics, SaturationMetrics) instead of generic dicts
   - Validation ensures counts match type breakdowns
   - `strategy_history` uses deque for automatic trimming

2. **Extraction Domain** (`src/domain/models/extraction.py`)
   - Clean separation between `ExtractedConcept`, `ExtractedRelationship`, and `ExtractionResult`
   - Traceability via `source_utterance_id` (ADR-010 Phase 2)

3. **Signal Architecture** (`src/methodologies/signals/common.py`)
   - `BaseSignal` abstract class enforces `signal_name` and async `detect()` contract
   - Node-level signals properly require `NodeStateTracker` dependency

### Domain Logic That Could Be Better Encapsulated

1. **Focus Selection Logic Is Scattered**
   - Logic exists in: `continuation_stage.py:87-109`, `question_service.py:223-265`, and `methodology_strategy_service.py`
   - **Recommendation**: Create a dedicated `FocusSelectionService` that owns all focus-related decisions

2. **Phase Detection in Multiple Places**
   - Phase boundaries are checked in `interview_phase.py` (signal) and `continuation_stage.py` (saturation)
   - Both use different logic for "what phase is this interview in?"
   - **Recommendation**: Unify phase detection into the signal, have continuation stage consume it

3. **Saturation Tracking Is Stage-Specific**
   - `_SessionSaturationState` in `continuation_stage.py:31-38` is internal state
   - Yet `SaturationMetrics` exists as a proper domain model in `knowledge_graph.py:70-85`
   - **Recommendation**: Move saturation computation to StateComputationStage (as the TODO comment suggests)

4. **LLM Client Construction Spread Across Services**
   - Each service optionally accepts an `llm_client` and calls `get_xxx_llm_client()` if None
   - **Recommendation**: Use dependency injection container to centralize LLM client lifecycle

---

## 3. Fail-Fast & Hygiene Issues

### Fallback Mechanisms (Silent Failures)

| Location | Issue | Recommendation |
|----------|-------|----------------|
| `extraction_service.py:142-151` | Catches all exceptions from LLM and returns empty `ExtractionResult` with error message as `extractability_reason` | **Replace with exception**: In POC, LLM failures should halt the interview with clear error. Current behavior masks API/config issues. |
| `methodology_strategy_service.py:81-88` | Returns `("deepen", None, [], None)` when methodology not found | **Replace with exception**: Missing methodology is a configuration error that should fail loudly. |
| `methodology_strategy_service.py:176-208` | Multiple fallback returns when `no_strategies_defined` or `no_scored_pairs` | **Replace with exception**: These indicate malformed YAML configs and should fail. |
| `methodology_strategy_service.py:297-310` | Catches exceptions from node signal detection, logs warning, continues | **Should fail**: Per ADR-009, scorer failures should terminate the interview. |
| `signals/registry.py:222-227` | Catches exceptions from signal detectors, logs error, continues | **Should fail**: Signal detection failure produces incomplete state for strategy selection. |
| `signals/registry.py:245-255` | Same pattern for meta signal detection | **Should fail**: Same reasoning. |
| `question_service.py:118-121` | `except Exception: pass` when loading methodology schema | **Remove or rethrow**: Silent failure here masks config issues. |
| `chain_completion.py:51-59` | Returns zeros when schema can't be loaded | **Should fail**: A methodology-specific signal failing to load its schema is a config error. |
| `chain_completion.py:122-127` | Falls back to `recent_nodes` when graph repo access fails | **Should fail**: DB access failure should not be silently handled. |
| `chain_completion.py:147-156` | Same pattern for edges | **Should fail**: Same reasoning. |
| `interview_phase.py:96-98` | `except Exception: pass` with fallback to DEFAULT_BOUNDARIES | **Should fail**: Config loading errors should be explicit. |
| `extraction_stage.py:60-65` | Logs warning when concept load fails, continues without concept | **Should fail**: Element linking won't work, extraction quality degraded. |
| `PipelineContext properties` (context.py:94-262) | All 30+ properties return defaults when contract output is None | **Audit usage**: Some defaults (like `return "deepen"` for strategy) mask missing contract state. |

### Dead Code / Code That Should Be Removed

| Location | Issue | Recommendation |
|----------|-------|----------------|
| `services/__init__.py:2` | Commented import: `# from src.services.strategy_service import StrategyService  # DEPRECATED` | **Delete**: Dead commented code. |
| `question_service.py:267-282` | `generate_fallback_question()` - appears unused | **Verify and delete**: Search codebase for callers. If none, remove. |
| `question_service.py:223-265` | `select_focus_concept()` - has Phase 2/3 comments suggesting supersession | **Verify**: May be dead code if strategy service now handles focus selection. |

### Defensive Code That Should Fail-Fast

| Location | Issue | Recommendation |
|----------|-------|----------------|
| `graph_update_stage.py:54-62` | Returns early with warning if `context.extraction` or `context.user_utterance` is None | **Should fail**: These being None violates pipeline contract - earlier stages should have set them. |
| `graph_update_stage.py:73-90` | Complex fallback logic for edge serialization with multiple hasattr checks | **Should standardize**: Define a proper interface for edges instead of duck-typing. |
| `PipelineContext.strategy property` (context.py:206-210) | Returns `"deepen"` as default strategy | **Should raise or return None**: Missing strategy output indicates pipeline failure. |
| `PipelineContext.turn_number property` (context.py:114-119) | Returns `1` as default turn number | **Should raise**: Turn number of 1 when context_loading_output is None masks initialization failure. |

### TODOs That Should Be Addressed

| Location | TODO |
|----------|------|
| `question_generation_stage.py:66` | `# TODO: Track has_llm_fallback when QuestionService supports it` |
| `question_generation_stage.py:71` | `has_llm_fallback=False,  # TODO: Track actual LLM fallback usage` |
| `hedging_language.py:38` | `# TODO: Replace with LLM-based analysis in production` |
| `hedging_language.py:101` | `# TODO: Implement LLM call when infrastructure is wired` |

---

## Summary of Critical Recommendations

1. **Adopt Fail-Fast for Signal Detection** - Per ADR-009, signal failures should terminate the interview. The current catch-and-continue pattern in `registry.py` and `methodology_strategy_service.py` masks errors.

2. **Remove LLM Error Swallowing in Extraction** - `extraction_service.py:142-151` converts LLM failures to empty results. For a POC, this should raise.

3. **Replace Default Returns with Exceptions in PipelineContext** - Properties like `strategy`, `turn_number`, `methodology` returning defaults when contracts are None creates silent failures. Consider making these raise or return None explicitly.

4. **Consolidate Focus Selection Logic** - Currently spread across 3+ locations. Create a single service that owns this domain logic.

5. **Move Saturation Tracking to Domain Layer** - The `SaturationMetrics` model exists but isn't used. Move `_SessionSaturationState` logic into StateComputationStage.

---

## Implementation Plans

Detailed implementation plans have been created:

- `plan_1_fail_fast_hygiene.md` - Dead code removal, fail-fast enforcement, defensive code fixes
- `plan_2_domain_encapsulation.md` - Domain logic consolidation improvements
- `plan_3_flow_clarity.md` - Pipeline flow and clarity improvements
