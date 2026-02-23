# Methodology Schema Field Tracing

Where each YAML field is consumed downstream.

## `method` section

| Field | Used? | Consumer | Purpose |
|---|---|---|---|
| `method.name` | YES | `src/llm/prompts/question.py:346` | Methodology label in opening question prompt |
| `method.goal` | YES | `src/llm/prompts/question.py:347` | Methodology description in opening question prompt |
| `method.opening_bias` | YES | `src/llm/prompts/question.py:348-361` | Injected as "Method-specific opening guidance" in opening question prompt |
| `method.description` | NO | — | Dead field, not referenced in code |
| `method.version` | NO | — | Dead field, not referenced in code |

## `ontology.nodes` fields

| Field | Used? | Consumer | Purpose |
|---|---|---|---|
| `nodes[].name` | YES | `src/services/extraction_service.py:396` | Validates extracted concept node_type against schema |
| `nodes[].description` | YES | `src/domain/models/methodology_schema.py:199-214` → `src/llm/prompts/extraction.py:76-78` | Injected into extraction prompt as "Valid Node Types" |
| `nodes[].examples` | YES | `src/domain/models/methodology_schema.py:208` → `src/llm/prompts/extraction.py:76-78` | Appended to node descriptions in extraction prompt |
| `nodes[].level` | YES | `src/services/extraction_service.py:407`, `src/signals/graph/graph_signals.py:200-204` | Sets concept level; ChainCompletionSignal uses level=1 as chain start |
| `nodes[].terminal` | YES | `src/services/extraction_service.py:406`, `src/signals/graph/graph_signals.py:197`, `src/services/node_state_tracker.py:140` | Sets `is_terminal` on concepts; ChainCompletionSignal uses terminal types as chain endpoints |

### `terminal` field dependency chain

```
YAML terminal: true
  → schema.is_terminal_node_type()           # methodology_schema.py:152
  → schema.get_terminal_node_types()          # methodology_schema.py:125
  → ChainCompletionSignal.detect()            # graph_signals.py:197 (BFS to terminal nodes)
  → extraction_service: concept.is_terminal   # extraction_service.py:406
  → node_state_tracker: is_terminal           # node_state_tracker.py:140
```

**NOTE**: `graph.chain_completion` signal is only referenced in `means_end_chain.yaml`, NOT in `jobs_to_be_done.yaml`. Removing `terminal: true` from JTBD nodes is safe (ChainCompletionSignal returns zeros, but JTBD never reads that signal). Would break MEC.

## `ontology.edges` fields

| Field | Used? | Consumer | Purpose |
|---|---|---|---|
| `edges[].name` | YES | `src/services/extraction_service.py:464` | Validates extracted relationship edge_type against schema |
| `edges[].description` | YES | `src/domain/models/methodology_schema.py:227-248` → `src/llm/prompts/extraction.py:80` | Injected into extraction prompt as "Valid Edge Types" (with permitted connections) |
| `edges[].permitted_connections` | YES | `src/domain/models/methodology_schema.py:167-197` → `src/services/extraction_service.py:476` | Validates source/target node type pairs; also now included in extraction prompt |

## `ontology` guidance sections

| Field | Used? | Consumer | Purpose |
|---|---|---|---|
| `extraction_guidelines` | YES | `src/llm/prompts/extraction.py:93→98-103` | Injected into extraction system prompt as "Methodology-Specific Extraction Guidelines" |
| `relationship_examples` | YES | `src/llm/prompts/extraction.py:94→105-117` | Injected into extraction prompt as "Relationship Extraction Examples" |
| `extractability_criteria` | YES | `src/llm/prompts/extraction.py:228` | Used in extractability pre-filter prompt (fast gate before full extraction) |

## `signals`, `strategies`, `phases` sections

| Field | Used? | Consumer | Purpose |
|---|---|---|---|
| `signals` | YES | Methodology registry → signal pool configuration | Determines which signals are computed per turn |
| `strategies` | YES | Strategy scoring engine (`src/methodologies/scoring.py`) | Strategy definitions with signal_weights for scoring |
| `phases` | YES | Phase detection + strategy weighting | Phase boundaries, multiplicative weights, additive bonuses |
