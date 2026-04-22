# Extraction

## Core Mechanics

`ExtractionService` (Stage 3 — `extraction_stage.py`) extracts concepts and relationships from user utterances using an LLM, guided by the active methodology's ontology.

**Pipeline per turn:**
1. **Fast extractability check** — heuristics filter out responses that are too short (< `min_word_count`, default 3), single words, or pure yes/no affirmatives. Returns `is_extractable=False` without calling LLM.
2. **LLM extraction** — calls `_extract_via_llm()` with a methodology-aware system prompt (node types, edge types, naming convention from `MethodologySchema`) and a user prompt containing the response text plus conversation context. Temperature 0.2, max tokens 4000, `response_format={"type": "json_object"}`.
3. **Concept parsing** (`_parse_concepts`) — validates each concept's `node_type` against the methodology schema. Enriches valid concepts with `is_terminal` and `level` from the schema. Sets `source_utterance_id` for traceability. Invalid node types are skipped with a warning log (`invalid_node_type`).
4. **Relationship parsing** (`_parse_relationships`) — validates `relationship_type` against the methodology schema. `permitted_connections` is validated via `schema.is_valid_connection()`: strict methodologies (with `permitted_connections` defined) reject invalid type pairs; flex methodologies (no `permitted_connections`) allow all connections. Validation only covers current-turn concepts — cross-turn edges referencing prior-turn nodes bypass this check (see known gap in ui0f). The prompt includes type-pair hints for strict methodologies via `get_edge_descriptions_with_connections()`.
5. **Element linking** — if `concept_id` is configured, concepts are linked to methodology elements via LLM-provided `linked_elements` field, with an alias-matching fallback.

Returns `ExtractionResult` with `concepts`, `relationships`, `is_extractable`, and `latency_ms`.

**Fail-fast:** `ExtractionError` is raised immediately on LLM failure — no silent degradation.

## Node Type Description Pipeline

The extraction prompt includes per-node-type descriptions built by `MethodologySchema.get_node_descriptions()`. Each entry combines the node's `description` and (when defined) up to 3 `non_attribute_examples` — counter-examples showing what does **not** belong in this node type.

**`node.examples` are NOT injected into the extraction prompt.** `get_node_descriptions()` only reads `description` and `non_attribute_examples`. Positive `examples` lists in the YAML are parsed by Pydantic but never forwarded to the LLM. Do not add domain examples expecting them to influence extraction — use the `description` field or `non_attribute_examples` instead. (Decision rationale: self-test heuristics in `description` generalise across domains better than domain-specific example lists.)

Counter-examples flow to the extraction LLM as: `"<description> NOT this type: counter1; counter2"`.

**Important:** `OntologySpec` uses `model_config = ConfigDict(extra="ignore")`. Unknown fields on a node spec are silently dropped by Pydantic. If you add a new field to `NodeTypeSpec` it must be declared as a class attribute — adding it only to the YAML will have no effect. The `non_attribute_examples` field was added to `NodeTypeSpec` after being silently dropped for multiple simulation iterations.

Use `non_attribute_examples` when a node type boundary is ambiguous — e.g., when a related concept (like `functional_consequence`) is systematically misclassified as this type. Positive examples alone are insufficient when LLMs generalise the category too broadly.

## Correctness Requirements

1. **`node_type` must match the methodology ontology** — validation in `_parse_concepts` skips invalid types. If the extraction prompt doesn't reflect the current ontology, nodes with stale types will be silently dropped.
2. **`source_utterance_id` must be set** — the traceability chain (utterance → concept → graph node) depends on this. If `source_utterance_id` is `None`, the fallback value `"unknown"` is used, breaking provenance.
3. **Empty extraction is valid** — `ExtractionResult(is_extractable=False)` with empty `concepts` and `relationships` is a normal outcome for short or ambiguous responses. Do not treat as error.
4. **`permitted_connections` is conditionally enforced** — `is_valid_edge_type()` always runs. `is_valid_connection()` runs only for edges where both source and target types are found in the current extraction batch. Strict methodologies enforce the whitelist; flex methodologies (no `permitted_connections` on the edge type) allow all. Cross-turn edges bypass validation (known gap — bead ui0f).
5. **Temperature 0.2** — lowered from 0.4 for more consistent classification and less hallucinated relationships. Intentionally not zero to allow some relationship inference across the conversation context.

## Symptom → Cause → Fix

| Symptom | Cause | Fix |
|---------|-------|-----|
| Nodes created with wrong `node_type` | Extraction prompt not reflecting current ontology (stale YAML or wrong methodology passed) | Update methodology YAML; verify `methodology` param passed to `extract()` matches active session config |
| Concepts silently dropped at extraction | `node_type` from LLM not in `schema.is_valid_node_type()` | Check `invalid_node_type` log entries; verify LLM prompt includes full node type list from YAML |
| Relationships rejected (missing from graph) | `relationship_type` not in `schema.is_valid_edge_type()` | Check `invalid_edge_type` log entries; verify edge type names match YAML exactly |
| Extraction always returns empty | Response too short or triggers yes/no filter | Check `extraction_skipped_heuristic` log; check `response.semantic.llm.elaboration` signal for shallow/surface values |
| `ExtractionError` raised | LLM call failed or returned invalid JSON | Check `extraction_llm_error` / `extraction_json_parse_failed` logs; verify LLM client config |
| Concepts lack element links | `concept_id` not configured, or alias match failed | Verify `concept_id` is set in service init; check `concept_linked_via_alias_fallback` debug logs |
| Strict mode edges violate `permitted_connections` | Cross-turn edge references prior-turn concept not in `concept_types` map — validation skipped | Known gap (bead ui0f); will be fixed at graph_service level after dedup resolution |

## Cross-Turn Bridging

The extraction context (built by `ExtractionStage._format_context_for_extraction`) includes prior conversation to enable cross-turn relationship edges — connecting a concept from the respondent's current answer to a concept they mentioned in a previous turn.

### Context assembly order (correctness requirement)

Sections are assembled in this exact order. Order matters: the task instruction references the node label list, so the list **must appear before the instruction** or the LLM will infer the source concept from raw question text rather than from the validated label.

```
1. Conversation turns (last 5, both speakers)
2. SRL hints (if SRL stage produced output)
3. [Existing graph concepts from previous turns]   ← label list first
4. [Most recent question] + bridge task instruction ← instruction after list
```

### Bridge task instruction

Only emitted when the most recent utterance is an interviewer question (`speaker == "system"`).

**When `focus_history` is non-empty** (turn 2+):

> *"Extract concepts ONLY from the Respondent's answer above. Then create one cross-turn relationship using `source_text="{focus_label}"` (the concept the question probed) → the primary new concept you extracted. Do NOT extract new concepts from the interviewer's question text."*

The `focus_label` is `focus_history[-1].label` from `ContextLoadingOutput` — the node the previous turn's question was built around. This makes the bridge source deterministic: the LLM receives the exact node label rather than inferring "the question's topic" from the raw question text.

**When `focus_history` is empty** (turn 1):

> *"Extract concepts ONLY from the Respondent's answer above. Do NOT extract new concepts from the interviewer's question text."*

No bridge relationship is requested on turn 1 because there is no prior focus node.

### Strategy-Aware Level Hints

When the bridge task instruction is emitted, `ExtractionStage` also injects a `[Level hint]` line that tells the extraction LLM what ontology level to expect based on the previous turn's strategy. This improves classification accuracy by priming the LLM with the strategy's intended direction.

Hints are keyed by strategy name in `_LEVEL_HINTS` dict:

| Strategy | Hint content |
|----------|-------------|
| `ascend` | "The response likely contains a concept at a HIGHER ontology level than {focus_type}." |
| `ground` | "The response likely contains a concept at a LOWER ontology level — possibly an attribute." |
| `branch` | "The response likely contains attribute-level concepts." |
| `bridge` | "The response likely contains an intermediate-level concept." |
| `anchor` | "Focus on extracting relationships to existing graph nodes rather than new concepts." |
| `revitalize` | No hint — bridge task is suppressed entirely (previous focus was abandoned). |

The hint is injected as `[Level hint] {hint_text}` immediately before the `[Task]` instruction. When no strategy-specific hint exists (e.g., custom methodologies), the hint line is omitted entirely.

### Reasoning Field on Relationships

The extraction prompt requests a `reasoning` field on each relationship: `"reasoning": "one sentence explaining why this relationship exists"`. This is parsed by `_parse_relationships()` and stored on `ExtractedRelationship.reasoning` for audit/debugging purposes. The field is not used in graph construction but provides traceability for why an edge was created.

### Bridge Target Selection

The bridge task instructs the LLM to connect to "the most concrete new concept you extracted (the one closest to the question's level, not the most abstract one the respondent mentioned)." This prevents the common failure mode where the LLM always bridges to the highest-level (most abstract) concept, which would bias the graph toward terminal values and skip intermediate levels.

### Why "extract from respondent only"

The graph represents the respondent's mental model, not the interviewer's framing. Without the explicit prohibition, the LLM may extract concepts from the interviewer's question text (e.g., follow-up framing language that was not in the respondent's prior answers), creating interviewer-authored nodes indistinguishable from respondent-generated ones.

### Known gap: `source_quote` on bridge relationships

Bridge relationships have an inherent `source_quote` problem: the source node was mentioned in a prior turn, so there is no verbatim text in the current utterance to quote. The LLM may hallucinate a `source_quote` for bridge edges. This is a secondary issue — `source_quote` is not validated or used for graph construction — but may affect traceability audits.

### Diagnostic logs

| Log key | Meaning |
|---------|---------|
| `cross_turn_node_context_injected` | Node label list included; shows `node_label_count` and `context_length` |
| `cross_turn_node_context_skipped` | No existing nodes yet (turn 1 or empty graph) |

## Key Files

- `src/services/extraction_service.py` — `ExtractionService` class
- `src/services/turn_pipeline/stages/extraction_stage.py` — Stage 3 wiring
- `src/llm/prompts/extraction.py` — prompt builders and response parser
- `src/domain/models/extraction.py` — `ExtractedConcept`, `ExtractedRelationship`, `ExtractionResult`
- `src/domain/models/methodology_schema.py` — `MethodologySchema` (ontology validation)
- `config/methodologies/*.yaml` — node types, edge types, naming conventions
