# Extraction

## Core Mechanics

`ExtractionService` (Stage 3 — `extraction_stage.py`) extracts concepts and relationships from user utterances using an LLM, guided by the active methodology's ontology.

**Pipeline per turn:**
1. **Fast extractability check** — heuristics filter out responses that are too short (< `min_word_count`, default 3), single words, or pure yes/no affirmatives. Returns `is_extractable=False` without calling LLM.
2. **LLM extraction** — calls `_extract_via_llm()` with a methodology-aware system prompt (node types, edge types, naming convention from `MethodologySchema`) and a user prompt containing the response text plus conversation context. Temperature 0.4, max tokens 4000, `response_format={"type": "json_object"}`.
3. **Concept parsing** (`_parse_concepts`) — validates each concept's `node_type` against the methodology schema. Enriches valid concepts with `is_terminal` and `level` from the schema. Sets `source_utterance_id` for traceability. Invalid node types are skipped with a warning log (`invalid_node_type`).
4. **Relationship parsing** (`_parse_relationships`) — validates `relationship_type` against the methodology schema. Note: `permitted_connections` validation is **disabled** (commented out) to allow unrestricted edge extraction; the LLM is already methodology-aware from the system prompt.
5. **Element linking** — if `concept_id` is configured, concepts are linked to methodology elements via LLM-provided `linked_elements` field, with an alias-matching fallback.

Returns `ExtractionResult` with `concepts`, `relationships`, `is_extractable`, and `latency_ms`.

**Fail-fast:** `ExtractionError` is raised immediately on LLM failure — no silent degradation.

## Correctness Requirements

1. **`node_type` must match the methodology ontology** — validation in `_parse_concepts` skips invalid types. If the extraction prompt doesn't reflect the current ontology, nodes with stale types will be silently dropped.
2. **`source_utterance_id` must be set** — the traceability chain (utterance → concept → graph node) depends on this. If `source_utterance_id` is `None`, the fallback value `"unknown"` is used, breaking provenance.
3. **Empty extraction is valid** — `ExtractionResult(is_extractable=False)` with empty `concepts` and `relationships` is a normal outcome for short or ambiguous responses. Do not treat as error.
4. **`edge_type` is validated; `permitted_connections` is not** — only `is_valid_edge_type()` runs. The LLM is expected to produce valid connections from the methodology prompt alone.
5. **Temperature 0.4** — intentionally higher than pure retrieval tasks to allow relationship inference across the conversation context.

## Symptom → Cause → Fix

| Symptom | Cause | Fix |
|---------|-------|-----|
| Nodes created with wrong `node_type` | Extraction prompt not reflecting current ontology (stale YAML or wrong methodology passed) | Update methodology YAML; verify `methodology` param passed to `extract()` matches active session config |
| Concepts silently dropped at extraction | `node_type` from LLM not in `schema.is_valid_node_type()` | Check `invalid_node_type` log entries; verify LLM prompt includes full node type list from YAML |
| Relationships rejected (missing from graph) | `relationship_type` not in `schema.is_valid_edge_type()` | Check `invalid_edge_type` log entries; verify edge type names match YAML exactly |
| Extraction always returns empty | Response too short or triggers yes/no filter | Check `extraction_skipped_heuristic` log; check `llm.response_depth` signal for shallow/surface values |
| `ExtractionError` raised | LLM call failed or returned invalid JSON | Check `extraction_llm_error` / `extraction_json_parse_failed` logs; verify LLM client config |
| Concepts lack element links | `concept_id` not configured, or alias match failed | Verify `concept_id` is set in service init; check `concept_linked_via_alias_fallback` debug logs |

## Key Files

- `src/services/extraction_service.py` — `ExtractionService` class
- `src/services/turn_pipeline/stages/extraction_stage.py` — Stage 3 wiring
- `src/llm/prompts/extraction.py` — prompt builders and response parser
- `src/domain/models/extraction.py` — `ExtractedConcept`, `ExtractedRelationship`, `ExtractionResult`
- `src/domain/models/methodology_schema.py` — `MethodologySchema` (ontology validation)
- `config/methodologies/*.yaml` — node types, edge types, naming conventions
