# CodeGrapher Architectural Queries

This document contains semantic queries for use with CodeGrapher to identify architectural issues,
pattern violations, and code quality concerns in the Interview System v2 codebase.

## Usage

Run these queries using the MCP CodeGrapher tool:

```python
# Example
results = mcp__codegrapher__codegraph_query(
    query="pipeline stage that writes to context without BaseModel contract",
    token_budget=5000
)
```

Adjust `token_budget` if results are truncated (default 3500 tokens).

---

## Pipeline Stage Reference

The pipeline has **12 stages** (including fractional stages):

| Stage | Name | Output Contract | Key Responsibilities |
|-------|------|-----------------|---------------------|
| 1 | ContextLoadingStage | `ContextLoadingOutput` | Load session, history, turn metadata |
| 2 | UtteranceSavingStage | `UtteranceSavingOutput` | Persist user input |
| 2.5 | SRLPreprocessingStage | `SrlPreprocessingOutput` | Linguistic parsing (optional) |
| 3 | ExtractionStage | `ExtractionOutput` | Extract concepts/relationships |
| 4 | GraphUpdateStage | `GraphUpdateOutput` | Update KG with dedup |
| 4.5 | SlotDiscoveryStage | `SlotDiscoveryOutput` | Canonical slot mapping (dual-graph) |
| 5 | StateComputationStage | `StateComputationOutput` | Refresh graph metrics |
| 6 | StrategySelectionStage | `StrategySelectionOutput` | Two-stage selection: global signals → strategy → node signals → node |
| 7 | ContinuationStage | `ContinuationOutput` | Continue or stop |
| 8 | QuestionGenerationStage | `QuestionGenerationOutput` | Generate next question |
| 9 | ResponseSavingStage | `ResponseSavingOutput` | Save system response |
| 10 | ScoringPersistenceStage | `ScoringPersistenceOutput` | Save scoring, update state |

**Critical Timing Constraints:**
- Stage 4 (GraphUpdate) must complete before Stage 4.5 (SlotDiscovery)
- Stage 4.5 (SlotDiscovery) must complete before Stage 5 (StateComputation)
- Stage 2 (UtteranceSaving) must complete before Stage 2.5 (SRLPreprocessing)
- State mutations in early stages (4, 4.5) are invisible to Stage 6 signal detectors

---

## 1. Architecture & Pattern Compliance

Queries to verify adherence to established architectural patterns.

| Query | Purpose |
|-------|---------|
| `pipeline stage that writes to context without BaseModel contract` | Find stages violating Phase 6 contract pattern |
| `signal class not exported from signals init or registry` | Find unregistered signal implementations |
| `methodology configuration missing signal_weights or strategies` | Find incomplete methodology YAML configs |
| `imports between pipeline stages stage A imports stage B` | Detect potential circular dependencies |
| `code that modifies graph state outside GraphUpdateStage` | Find graph mutations bypassing the proper stage |
| `context field accessed before being set by previous stage` | Find pipeline contract violations |
| `stage that reads from database directly instead of context` | Find stages not using pipeline data flow |
| `service that instantiates dependencies instead of receiving them` | Find dependency injection violations |
| `SRL preprocessing stage that doesn't check enable_srl flag` | Find SRL stages not respecting feature flag |
| `slot discovery stage without graph_update_output validation` | Find Stage 4.5 contract violations |
| `dual-graph code that only uses surface graph ignoring canonical` | Find missing canonical graph usage |
| `signal not registered via SignalRegistry or __init_subclass__` | Find unregistered signal detectors |
| `LLM signal detection outside LLMBatchDetector` | Find LLM signals not batched properly |
| `pipeline stage without proper contract output class` | Find stages not using Pydantic contracts |
| `context property that doesn't raise RuntimeError on premature access` | Find weak contract enforcement |

---

## 2. Error Handling & Robustness

Queries to identify weak error handling patterns.

| Query | Purpose |
|-------|---------|
| `bare except clause pass or ellipsis` | Find overly broad exception handling |
| `LLM client call without try except or error handling` | Find unprotected external API calls |
| `database session commit without rollback on error` | Find transaction handling issues |
| `logs exception but does not raise` | Find swallowed exceptions |
| `function returns None on error without documented return type` | Find inconsistent error returns |
| `async function without await inside try block` | Find missing await in error paths |
| `raise Exception instead of specific exception type` | Find generic exception raising |
| `except Exception as e but e is never used` | Find unused exception variables |
| `SRL service call without graceful skip when disabled` | Find SRL failures when feature off |
| `slot discovery without handling empty nodes_added` | Find missing graceful skip patterns |

---

## 3. Testing & Coverage Gaps

Queries to identify untested or under-tested code.

| Query | Purpose |
|-------|---------|
| `signal class in src/signals without corresponding test file` | Find signals without tests |
| `methodology YAML config without validation test` | Find untested methodology configs |
| `pipeline stage without test in tests directory` | Find stages without tests |
| `scoring function rank_strategies without unit test` | Find untested scoring logic |
| `public function without test function calling it` | Find untested public functions |
| `class with complex logic but no test class` | Find untested complex classes |
| `edge case handling not covered by tests` | Find missing edge case coverage |
| `mock patch that does not assert call count` | Find weak test assertions |
| `SRL preprocessing stage without feature flag test` | Find untested SRL enable/disable |
| `slot discovery stage without dual-graph test` | Find untested canonical mapping |

---

## 4. Configuration & Consistency

Queries to find hardcoded values and inconsistencies.

| Query | Purpose |
|-------|---------|
| `magic number in pipeline or service code` | Find values that should be config |
| `signal with wrong namespace not graph llm temporal meta` | Find namespacing violations |
| `methodology YAML with different signal names than others` | Find inconsistent configs |
| `settings default value that differs from config YAML` | Find config drift |
| `hardcoded string used in multiple files` | Find duplicated string literals |
| `timeout value not from settings` | Find hardcoded timeouts |
| `batch size limit not configurable` | Find hardcoded limits |
| `feature flag check with boolean instead of settings` | Find hardcoded feature flags |
| `SRL threshold not from settings` | Find hardcoded SRL thresholds |
| `canonical similarity threshold not from config` | Find hardcoded dedup thresholds |

---

## 5. Performance & Scalability

Queries to identify potential performance issues.

| Query | Purpose |
|-------|---------|
| `nested loop over graph nodes or edges` | Find O(n²) graph operations |
| `sync database call in async function without run_in_executor` | Find blocking calls in async code |
| `list append in loop without size limit or clearing` | Find potential memory leaks |
| `compute same value multiple times in pipeline` | Find missing memoization |
| `repeated database query inside loop` | Find N+1 query patterns |
| `large list comprehension without generator` | Find memory inefficiency |
| `json serialization in hot path` | Find serialization bottlenecks |
| `recursive function without depth limit` | Find potential stack overflow |
| `LLM call per signal instead of batch detection` | Find unbatched LLM signals |
| `embedding computation without caching` | Find redundant embedding calculations |

---

## 6. Documentation & Maintainability

Queries to find documentation gaps.

| Query | Purpose |
|-------|---------|
| `public function def without docstring triple quotes` | Find undocumented public functions |
| `class inheriting from multiple mixins or deep hierarchy` | Find complex inheritance |
| `TODO FIXME XXX comment in code` | Find tech debt markers |
| `function parameter without type annotation in src directory` | Find missing type hints |
| `complex logic without inline comment` | Find uncommented complex code |
| `module without module level docstring` | Find undocumented modules |
| `dataclass field without description` | Find undocumented fields |
| `enum value without documentation` | Find undocumented enum variants |
| `pipeline stage without contract documentation` | Find stages missing ADR-010 compliance docs |
| `dual-graph code without architecture comment` | Find missing dual-graph explanations |

---

## 7. Domain-Specific (Interview System)

Queries specific to this codebase's domain.

| Query | Purpose |
|-------|---------|
| `select strategy without using MethodologyStrategyService` | Find strategy selection bypasses |
| `two-stage selection without node_tracker for node signals` | Find missing node-level context |
| `global signal detection outside GlobalSignalDetectionService` | Find signal detection bypasses |
| `node signal detection outside NodeSignalDetectionService` | Find node signal bypasses |
| `graph traversal ignoring exhausted nodes` | Find exhaustion logic violations |
| `decide interview end outside ContinuationStage` | Find continuation logic bypasses |
| `access session state directly instead of through context` | Find context access violations |
| `update graph without creating provenance record` | Find missing provenance |
| `strategy scoring without phase weights` | Find missing phase weight application |
| `utterance processing without source tracking` | Find traceability violations |
| `canonical slot mapping without provenance record` | Find missing provenance in deduplication |
| `SRL frame extraction without discourse relation handling` | Find incomplete SRL processing |
| `node exhaustion check without NodeStateTracker` | Find direct exhaustion checks bypassing tracker |
| `strategy configuration without phase_weights` | Find incomplete methodology YAMLs |
| `surface node update without canonical sync` | Find surface/canonical graph sync issues |
| `extraction without cross-turn resolution` | Find missing cross-turn edge resolution |
| `dual-graph architecture bypassing SlotDiscoveryStage` | Find missing canonical slot discovery |
| `signal detection without node_tracker for node signals` | Find missing node-level signal context |
| `LLM signal without @llm_signal decorator` | Find unregistered LLM signals |
| `batch detector without LLM client configuration` | Find incomplete LLM batch setup |

---

## 8. Security & Safety

Queries to identify potential security issues.

| Query | Purpose |
|-------|---------|
| `user input used without validation` | Find unvalidated inputs |
| `f-string or format with user input` | Find potential injection points |
| `file path construction without sanitization` | Find path traversal risks |
| `subprocess call with variable arguments` | Find command injection risks |
| `pickle load or loads usage` | Find unsafe deserialization |
| `eval or exec usage` | Find code injection risks |
| `hardcoded secret password token key` | Find hardcoded secrets |
| `debug mode enabled in production code` | Find debug exposure |
| `LLM prompt without input sanitization` | Find prompt injection risks |
| `graph query with unsanitized node labels` | Find graph injection risks |

---

## 9. Cross-Stage State Mutation Analysis

Queries to analyze pipeline stage ordering and state mutation timing patterns.
These queries help identify timing bugs where state is mutated before being read by signals.

| Query | Purpose |
|-------|---------|
| `which pipeline stages call NodeStateTracker methods with stage numbers` | Map stage → method call ordering |
| `show writes to NodeState field current_focus_streak across all stages` | Find all mutation sites for a field |
| `which signals read NodeState field and at which stage` | Signal → field read dependency |
| `pipeline stage that mutates state before signal detection reads it` | Timing violation detector |
| `trace NodeState field mutations across pipeline stages in order` | Per-field state evolution |
| `which stage resets current_focus_streak field to zero` | Find field reset operations |
| `show all NodeStateTracker method calls with calling stage context` | Stage → tracker method mapping |
| `signal that reads NodeState field written in earlier stage` | Identify fresh vs stale signal reads |
| `record_yield called before or after signal detection stage` | Verify critical stage ordering |
| `which stage last modified NodeState field before signal detection` | Provenance for signal inputs |
| `SRL preprocessing reads utterance before Stage 2 completes` | Stage 2.5 timing violation |
| `slot discovery reads graph update before Stage 4 completes` | Stage 4.5 timing violation |
| `state computation reads slots before Stage 4.5 completes` | Stage 5 timing violation |
| `strategy selection reads state before Stage 5 completes` | Stage 6 timing violation |

### Use Case: The 119q Bug

The bug where `focus_streak` always appeared as 0 would have been found by:
1. `which stage resets current_focus_streak field to zero` → Found Stage 4 `record_yield`
2. `which signals read NodeState field current_focus_streak` → Found `NodeFocusStreakSignal`
3. `trace NodeState field mutations across pipeline stages in order` → Shows Stage 4 < Stage 6 ordering

**Key Insight**: Stage 4 (record_yield) runs BEFORE Stage 6 (signal detection), so any reset in Stage 4 makes signals read stale/zero values.

### Use Case: SRL Preprocessing Timing

Stage 2.5 (SRLPreprocessingStage) requires Stage 2 (UtteranceSavingStage) to complete first:
- Query: `SRL preprocessing reads utterance before Stage 2 completes`
- This detects contract violations where SRL tries to access `utterance_saving_output` before it's set.

### Use Case: Dual-Graph Timing

Stage 4.5 (SlotDiscoveryStage) must run between Stage 4 and Stage 5:
- Query: `slot discovery reads graph update before Stage 4 completes`
- Query: `state computation reads slots before Stage 4.5 completes`
- These ensure proper dual-graph pipeline ordering.

---

## 10. SRL & Linguistic Processing

Queries specific to the SRL (Semantic Role Labeling) preprocessing stage.

| Query | Purpose |
|-------|---------|
| `SRL service instantiated without lazy loading pattern` | Find eager SRL loading |
| `SRL analysis without discourse relation extraction` | Find incomplete linguistic parsing |
| `discourse relation without antecedent or consequent` | Find incomplete discourse relations |
| `SRL frame without predicate or arguments` | Find incomplete frame extraction |
| `SRL preprocessing without interviewer question context` | Find missing question context |
| `spaCy model loaded outside SRLService property` | Find improper spaCy loading |
| `SRL frame extraction without argument role labels` | Find incomplete argument extraction |
| `discourse relation extraction without marker detection` | Find missing discourse markers |
| `SRL output not wrapped in SrlPreprocessingOutput contract` | Find contract violations |
| `SRL service called when enable_srl is False` | Find feature flag bypasses |

---

## 11. Dual-Graph Architecture

Queries specific to the dual-graph architecture (surface + canonical graphs).

| Query | Purpose |
|-------|---------|
| `surface node without canonical slot mapping` | Find unmapped surface nodes |
| `canonical slot without surface node support` | Find orphaned canonical slots |
| `edge aggregation bypassing graph_service` | Find direct edge aggregation |
| `slot discovery without LLM client for proposal` | Find missing LLM slot proposal |
| `canonical slot without embedding similarity check` | Find missing dedup verification |
| `surface graph update without triggering slot discovery` | Find missing slot discovery calls |
| `canonical graph state not exposed in StateComputationOutput` | Find missing canonical state |
| `slot mapping without provenance tracking` | Find missing mapping provenance |
| `canonical edge without aggregated surface edges` | Find incomplete edge aggregation |
| `dual-graph code using wrong similarity threshold` | Find threshold config issues |
| `canonical slot status not transitioning to active` | Find missing slot activation |
| `surface node mapped to multiple canonical slots` | Find mapping integrity issues |

---

## Batch Execution Template

```python
# Run multiple queries and aggregate results
queries = [
    # Architecture
    "pipeline stage that writes to context without BaseModel contract",
    "SRL preprocessing stage that doesn't check enable_srl flag",
    "slot discovery stage without graph_update_output validation",

    # Testing
    "signal class in src/signals without corresponding test file",
    "pipeline stage without test in tests directory",
    "SRL preprocessing stage without feature flag test",

    # Domain-specific
    "canonical slot mapping without provenance record",
    "surface node update without canonical sync",
    "SRL frame extraction without discourse relation handling",

    # Documentation
    "public function def without docstring triple quotes",
    "pipeline stage without contract documentation",

    # Performance
    "LLM call per signal instead of batch detection",
    "nested loop over graph nodes or edges",
]

all_results = []
for query in queries:
    result = mcp__codegrapher__codegraph_query(
        query=query,
        token_budget=3000
    )
    if result.get('status') == 'success':
        all_results.extend(result.get('files', []))

# Sort by PageRank centrality to find most impactful issues
from collections import OrderedDict
unique_files = OrderedDict()
for f in sorted(all_results, key=lambda x: x.get('pagerank', 0), reverse=True):
    path = f['path']
    if path not in unique_files:
        unique_files[path] = f

# Print top 10 most central issues
for path, info in list(unique_files.items())[:10]:
    print(f"{path}:{info['line_start']} (centrality: {info['pagerank']:.3f})")
```

---

## Filtering by PageRank

PageRank scores indicate how central a symbol is in the codebase:

- **0.10+**: Core/central - used by many components (fix first)
- **0.05-0.10**: Important utility or service
- **0.01-0.05**: Supporting function or helper
- **<0.01**: Leaf node or rarely referenced

Always prioritize fixes in high PageRank files as they have broader impact.

---

## 12. Two-Stage Scoring Architecture

Queries specific to the D1 two-stage strategy selection architecture.

| Query | Purpose |
|-------|---------|
| `rank_strategies without phase weights application` | Find missing phase adaptation |
| `rank_nodes_for_strategy without node_binding check` | Find unconditional node ranking |
| `two-stage selection mixing global and node signals incorrectly` | Find signal category violations |
| `strategy selection without score decomposition` | Find missing observability |
| `phase weights not loaded from methodology config` | Find hardcoded phase behavior |
| `node selection without exhaustion penalty` | Find missing node exhaustion |
| `strategy with node_binding required but no node selected` | Find selection failures |
| `joint scoring without rank_strategies and rank_nodes_for_strategy` | Find bypassing scoring functions |

### Two-Stage Selection Flow

```
Stage 1 (Global):
  GlobalSignalDetectionService → global_signals
  ↓
  rank_strategies(strategy_configs, global_signals, phase_weights, phase_bonuses)
  ↓
  best_strategy_config (StrategyConfig with node_binding)

Stage 2 (Node - conditional):
  If node_binding == "required":
    NodeSignalDetectionService → node_signals
    ↓
    rank_nodes_for_strategy(best_strategy_config, node_signals, phase_weights, phase_bonuses)
    ↓
    focus_node_id
```

**Key Checks:**
- `node_tracker` is REQUIRED for two-stage selection
- Phase weights/bonuses loaded from `config.phases[phase]`
- Node selection only occurs when `node_binding == "required"`

---

## Signal Registry Quick Reference

Signals are auto-registered via `__init_subclass__` in the following pools:

| Pool | Namespace | Location | Registration Method |
|------|-----------|----------|---------------------|
| Graph | `graph.*` | `src/signals/graph/` | `SignalDetector` base class |
| LLM | `llm.*` | `src/signals/llm/signals/` | `@llm_signal` decorator |
| Session | `temporal.*` | `src/signals/session/` | `SignalDetector` base class |
| Meta | `meta.*` | `src/signals/meta/` | `SignalDetector` base class |

**LLM Signal Batching**: All LLM signals are batched into a single API call via `LLMBatchDetector` to minimize latency.

**Signal Dependencies**: Declare dependencies via `dependencies = ['signal.name']` class attribute for topological ordering.

---

## Deprecated Patterns (Do Not Use)

These patterns have been removed or replaced and should not appear in new code:

| Old Pattern | Replacement | Reason |
|-------------|-------------|--------|
| `SignalPool` class | `SignalRegistry` + `ComposedSignalDetector` | Better separation of concerns |
| `select_strategy` (single-stage) | `select_strategy_and_focus` (two-stage) | Joint strategy-node scoring (D1) |
| `FirstStageScorer` / `SecondStageScorer` | `rank_strategies` / `rank_nodes_for_strategy` | Simpler functional API |
| Legacy two-tier scoring | Methodology-based signal scoring | YAML-configurable strategies |
| Direct signal instantiation | `ComposedSignalDetector` with batching | LLM batching support |

If you find these patterns in code, they should be refactored to use current architecture.
