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

---

## 4. Configuration & Consistency

Queries to find hardcoded values and inconsistencies.

| Query | Purpose |
|-------|---------|
| `magic number in pipeline or service code` | Find values that should be config |
| `signal with wrong namespace not graph llm temporal meta technique` | Find namespacing violations |
| `methodology YAML with different signal names than others` | Find inconsistent configs |
| `settings default value that differs from config YAML` | Find config drift |
| `hardcoded string used in multiple files` | Find duplicated string literals |
| `timeout value not from settings` | Find hardcoded timeouts |
| `batch size limit not configurable` | Find hardcoded limits |
| `feature flag check with boolean instead of settings` | Find hardcoded feature flags |

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

---

## 7. Domain-Specific (Interview System)

Queries specific to this codebase's domain.

| Query | Purpose |
|-------|---------|
| `select strategy without using MethodologyStrategyService` | Find strategy selection bypasses |
| `detect signals without SignalPool class` | Find signal detection outside pools |
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

---

## Batch Execution Template

```python
# Run multiple queries and aggregate results
queries = [
    "public function def without docstring triple quotes",
    "signal class in src/signals without corresponding test file",
    "pipeline stage without test in tests directory",
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
