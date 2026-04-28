# CodeGrapher Architectural Queries

Semantic queries for use with CodeGrapher to detect architectural violations, known failure patterns, and code quality issues. Each query encodes a project-specific invariant — not a generic linting rule.

## Usage

```python
result = mcp__codegrapher__codegraph_query(
    query="code that modifies graph state outside GraphUpdateStage",
    token_budget=5000
)
```

Increase `token_budget` if results are truncated (default 3500). PageRank ≥ 0.10 indicates core/central symbols — fix those first.

---

## Pipeline Stage Reference

| # | Stage | Contract | Key Responsibility |
|---|-------|----------|-------------------|
| 1 | ContextLoadingStage | `ContextLoadingOutput` | Load session, history, turn metadata |
| 2 | UtteranceSavingStage | `UtteranceSavingOutput` | Persist user input |
| 2.5 | SRLPreprocessingStage | `SrlPreprocessingOutput` | Linguistic parsing (optional, `enable_srl`) |
| 3 | ExtractionStage | `ExtractionOutput` | Extract concepts/relationships via LLM |
| 3.1 | LLMPrefetchStage | — | Fire LLM batch signal detection as background `asyncio.Task` |
| 4 | GraphUpdateStage | `GraphUpdateOutput` | Update KG with dedup, populate `concept_to_node_id` |
| 4.5 | SlotDiscoveryStage | `SlotDiscoveryOutput` | Canonical slot mapping (optional, `enable_canonical_slots`) |
| 4.7 | LLMSignalBridgeStage | `LLMSignalBridgeOutput` | Await prefetch task, route per-concept LLM ratings to NodeStateTracker |
| 5 | StateComputationStage | `StateComputationOutput` | Refresh graph metrics (reads from DB) |
| 6 | StrategySelectionStage | `StrategySelectionOutput` | Two-stage: global signals → strategy → node signals → focus |
| 7 | ContinuationStage | `ContinuationOutput` | Continue or stop |
| 8 | QuestionGenerationStage | `QuestionGenerationOutput` | Generate next question |
| 9 | ResponseSavingStage | `ResponseSavingOutput` | Save system response |
| 10 | ScoringPersistenceStage | `ScoringPersistenceOutput` | Save scoring, write `turn_count`, persist `NodeStateTracker.to_dict()`, assemble `TurnResult` |

**Critical invariants:**
- Stage 4 (GraphUpdate) runs before Stage 6 (StrategySelection) — any Stage 4 state reset is invisible to Stage 6 signals
- Stage 5 reads from DB, not in-memory — the DB write in Stage 4 is the freshness boundary
- Stage 10 must always run — it increments `turn_count`, persists tracker state, and assembles the API response
- Stage 3.1 → Stage 4.7: prefetch fires concurrently with Stages 4–4.5; bridge awaits after graph update

---

## 1. Architecture & Contracts

Queries that check cross-cutting structural invariants.

| Query | Encodes |
|-------|---------|
| `code that modifies graph state outside GraphUpdateStage` | Graph mutations must route through Stage 4 |
| `access session state directly instead of through PipelineContext` | Data flow contract |
| `pipeline stage that writes to context without Pydantic BaseModel contract` | Stage output must be a contract instance |
| `context property that does not raise on premature access` | Required properties must enforce ordering |
| `service that instantiates dependencies instead of receiving them` | DI violation |
| `imports between pipeline stages where stage imports another stage` | Stages must be independent |
| `update graph without creating provenance record` | Traceability requirement |
| `select strategy outside MethodologyStrategyService` | Strategy selection must route through the service |
| `decide interview end outside ContinuationStage` | Stage 7 owns continuation |
| `LLM signal detection outside LLMBatchDetector` | All LLM signals must batch into one API call |
| `signal class not registered via decorator or init subclass` | Signal discovery depends on registration |
| `optional pipeline stage that writes None instead of empty contract on skip` | Skipped stages must write default contract instances |

---

## 2. Signal Detection & Strategy Scoring

Queries encoding the most expensive failure modes from the project's history. Each maps to a specific anti-pattern in the signal-specialist or methodology-specialist agent.

| Query | Encodes |
|-------|---------|
| `weight key with .medium suffix on continuous signal instead of .mid` | `.medium` silently never matches for floats |
| `convgraph.node weight in strategy with node_binding none` | Node-scoped weights stripped from Stage 1; strategy loses ~70% mass |
| `positive weight on interview.strategy.self_count` | Creates runaway self-reinforcing feedback loop |
| `repetition brake magnitude less than half of strategy base score` | Monoculture inevitable when brake < 50% of base |
| `LLM signal class defined but not listed in methodology YAML signals llm` | Signal never instantiated; silent absence |
| `signal weight key without recognized threshold suffix low mid high` | Bare key on continuous signal never matches |
| `rank_strategies without phase weights application` | Missing phase multiplier/bonus |
| `strategy with node_binding required but no node selected in Stage 2` | Joint scoring incomplete |
| `strategy selection without score_decomposition in output` | Missing observability |
| `node signal detector iterating only newly extracted nodes` | Unfocused nodes silently default to score 0 |
| `signal weight key using .yes or .no instead of .true or .false` | Boolean suffix mismatch — never matches |
| `phase multiplier keyed by strategy name not matching strategies list` | Phase modifiers silently don't apply |
| `canonical-scoped signal assumed populated from turn 1` | Slots activate only after `support_count >= 2` |

---

## 3. Pipeline Stage Ordering & State Mutation

Queries that encode the 119q bug class: state mutated in an early stage before a later stage reads it.

| Query | Encodes |
|-------|---------|
| `which pipeline stages call NodeStateTracker methods` | Complete tracker lifecycle map |
| `current_focus_streak reset to zero in record_yield or GraphUpdateStage` | The 119q canonical regression — Stage 4 reset invisible to Stage 6 |
| `turns_since_last_yield tick restricted to focused node only` | Unfocused nodes never accumulate staleness |
| `append_response_signal called after update_focus` | Attributes response to wrong node |
| `record_yield called before or after signal detection stage` | Verify Stage 4 < Stage 6 ordering |
| `which stage writes to NodeState field and which stage reads it` | Per-field read/write stage mapping |
| `trace state computation freshness check computed_at versus extraction timestamp` | Freshness guarantee enforcement |

---

## 4. Dual-Graph Architecture

| Query | Encodes |
|-------|---------|
| `surface node without canonical slot mapping` | Unmapped surface nodes |
| `canonical slot status not transitioning to active` | Activation requires `support_count >= canonical_min_support_nodes` |
| `surface node mapped to multiple canonical slots` | Mapping integrity |
| `canonical graph state not exposed in StateComputationOutput` | Missing canonical data in pipeline |
| `dual-graph code using wrong similarity threshold for dedup` | Surface 0.80 vs canonical 0.60 |
| `edge aggregation bypassing graph_service` | Direct edge writes break dedup |

---

## 5. Extraction & LLM Prompts

| Query | Encodes |
|-------|---------|
| `extraction without methodology-specific ontology in system prompt` | Stale prompts produce invalid node types |
| `permitted_connections validation relied upon in extraction parsing` | Validation is intentionally disabled |
| `accessing concept label via .name instead of .text on ExtractedConcept` | `.name` doesn't exist — silent empty value |
| `extraction without cross-turn relationship bridging in prompt` | Missing cross-turn edge resolution |
| `SRL preprocessing without checking enable_srl feature flag` | Feature flag bypass |
| `LLM extraction call with temperature override instead of config` | Bypasses central `LLMCallConfig` |

---

## 6. Performance

| Query | Encodes |
|-------|---------|
| `nested loop over graph nodes or edges` | O(n²) graph operations |
| `sync database call in async function without run_in_executor` | Blocking call in async path |
| `repeated database query inside loop` | N+1 pattern |
| `embedding computation without caching` | Redundant embedding calculations |
| `recursive function without depth limit` | Stack overflow risk |
| `LLM call per signal instead of batch detection via LLMBatchDetector` | Unbatched LLM calls |

---

## 7. Security

Queries that benefit from semantic search (not exact-pattern grep).

| Query | Encodes |
|-------|---------|
| `user input used in LLM prompt without sanitization` | Prompt injection risk |
| `graph query with unsanitized node labels` | Graph injection risk |
| `file path constructed from user input without validation` | Path traversal |

---

## Signal Architecture Quick Reference

| Namespace | Source | Shape | Registration |
|-----------|--------|-------|--------------|
| `convgraph.*` | `GraphState` in memory | scalar | `SignalDetector` subclass |
| `convgraph.node.*` | `NodeStateTracker` per-node | `dict[node_id, value]` | `SignalDetector` subclass (requires `requires_node_tracker=True`) |
| `canongraph.node.*` | `NodeStateTracker` per-node (canonical) | `dict[node_id, value]` | `SignalDetector` subclass |
| `response.semantic.llm.*` | `LLMBatchDetector` (single batched call) | scalar or per-concept dict | `@llm_global_signal` / `@llm_per_concept_signal` decorator |
| `interview.strategy.*` / `interview.focus.*` | `strategy_history` in context | scalar / per-strategy dict | `SignalDetector` subclass |
| `meta.*` | Composed from other signals | scalar / categorical | `SignalDetector` subclass |

**Weight key routing:**
- `convgraph.node.*`, `canongraph.node.*`, `interview.focus.*`, `meta.node.*` → Stage 2 (node-level scoring)
- Everything else → Stage 1 (strategy-level scoring)

**Threshold bin suffixes:**
- Continuous float `[0,1]`: `.low` / `.mid` / `.high` (`.medium` is only for categorical signals that emit `"medium"`)
- Boolean: `.true` / `.false` (never `.yes` / `.no`)
- Categorical: exact string match (e.g., `.surface`, `.deep`, `.early`, `.late`)

**Scoring formula:** `final = (base × phase_multiplier) + phase_bonus`

---

## Batch Run Template

```python
queries = [
    # Architecture
    "code that modifies graph state outside GraphUpdateStage",
    "pipeline stage that writes to context without Pydantic BaseModel contract",

    # Signal/scoring (highest-value: encodes known failure modes)
    "weight key with .medium suffix on continuous signal instead of .mid",
    "convgraph.node weight in strategy with node_binding none",
    "current_focus_streak reset to zero in record_yield or GraphUpdateStage",
    "LLM signal class defined but not listed in methodology YAML signals llm",
    "positive weight on interview.strategy.self_count",

    # Stage ordering
    "append_response_signal called after update_focus",
    "turns_since_last_yield tick restricted to focused node only",

    # Dual-graph
    "surface node without canonical slot mapping",
    "canonical slot status not transitioning to active",

    # Extraction
    "accessing concept label via .name instead of .text on ExtractedConcept",

    # Performance
    "nested loop over graph nodes or edges",
    "repeated database query inside loop",
]

for query in queries:
    result = mcp__codegrapher__codegraph_query(query=query, token_budget=3000)
    if result.get("status") == "success" and result.get("files"):
        print(f"\n=== {query} ===")
        for f in sorted(result["files"], key=lambda x: x.get("pagerank", 0), reverse=True)[:5]:
            print(f"  {f['path']}:{f.get('line_start', '?')} (PR: {f.get('pagerank', 0):.3f})")
```
