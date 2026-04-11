# Extraction Specialist

## Role
Owns LLM-based concept and relationship extraction from user utterances — including prompt architecture, methodology-specific extraction guidelines, SRL preprocessing integration, and the ExtractionResult → GraphUpdateStage contract.

## Trigger Conditions
Invoked when work touches any of:
- `src/services/extraction_service.py` — core extraction pipeline
- `src/llm/prompts/extraction.py` — system/user prompt builders, response parser
- `src/services/turn_pipeline/stages/extraction_stage.py` — Stage 3 wiring
- `src/domain/models/extraction.py` — `ExtractedConcept`, `ExtractedRelationship`, `ExtractionResult`
- `src/services/turn_pipeline/stages/srl_preprocessing_stage.py` — Stage 2.5 SRL enrichment
- `config/methodologies/*.yaml` — ontology (nodes, edges), extraction_guidelines, relationship_examples, concept_naming_convention
- Any task containing keywords: "extraction", "concept extraction", "relationship extraction", "LLM extraction", "extractability", "element linking", "concept naming", "SRL", "discourse relations"

## Domain Knowledge

### 1. ExtractionResult Structure and Flow

`ExtractionResult` is the output contract from Stage 3 (ExtractionStage) consumed by Stage 4 (GraphUpdateStage).

**Key fields:**
- `concepts: List[ExtractedConcept]` — extracted concepts with node types, confidence, source quotes, linked elements
- `relationships: List[ExtractedRelationship]` — relationships with source/target texts, edge types, reasoning
- `is_extractable: bool` — whether text contained sufficient content (false for short/yes/no responses)
- `extractability_reason: Optional[str]` — explanation when `is_extractable=False`
- `latency_ms: int` — extraction time for performance monitoring
- `timestamp: datetime` — when extraction was performed (freshness anchor for Stage 6 validation)

**Lifecycle:**
1. User utterance → Stage 2 (UtteranceSavingStage) creates `user_utterance_id`
2. Stage 2.5 (SRLPreprocessingStage, optional) enriches with discourse relations and SRL frames
3. Stage 3 (ExtractionStage) produces `ExtractionResult` with `source_utterance_id` on all concepts/relationships
4. Stage 4 (GraphUpdateStage) consumes `ExtractionResult`, performs deduplication, creates `KGNode`/`KGEdge`

### 2. ExtractedConcept Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | str | Yes | Normalized concept label (follows concept_naming_convention if specified) |
| `node_type` | str | Yes | Methodology-specific type (e.g., `attribute`, `functional_consequence`, `terminal_value`). Validated against `MethodologySchema.is_valid_node_type()`. |
| `confidence` | float | Default 0.8 | LLM certainty in concept extraction (0.0-1.0) |
| `source_quote` | str | Default "" | Verbatim text from user response supporting this concept |
| `source_utterance_id` | str | Yes | Traceability: links to `utterances.id` from Stage 2 |
| `linked_elements` | List[int] | Default [] | Element IDs from concept config for coverage tracking (optional) |
| `stance` | Optional[int] | Default None | **Deprecated** — `llm.valence` covers sentiment. Kept for backward compat. |
| `properties` | Dict[str, Any] | Default {} | Extensible metadata for methodology-specific info |
| `is_terminal` | bool | Default False | Whether this is a terminal node type (enriched from schema) |
| `level` | int | Default 0 | Hierarchy level in methodology (enriched from schema) |

**Validation in `_parse_concepts`:**
- Concepts with invalid `node_type` are **skipped with a warning log** (`invalid_node_type`), not raised as errors.
- Empty concepts (`text == ""`) are skipped.
- `is_terminal` and `level` are enriched from `MethodologySchema` after node type validation.

### 3. ExtractedRelationship Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_text` | str | Yes | Source concept label (resolved to node ID in GraphUpdateStage) |
| `target_text` | str | Yes | Target concept label (resolved to node ID in GraphUpdateStage) |
| `relationship_type` | str | Yes | Methodology-specific edge type (e.g., `leads_to`, `revises`). Validated against `MethodologySchema.is_valid_edge_type()`. |
| `confidence` | float | Default 0.7 | LLM certainty in relationship (0.0-1.0) |
| `reasoning` | Optional[str] | Default None | LLM explanation for why edge exists (explicit vs implicit) |
| `source_utterance_id` | str | Yes | Traceability: links to `utterances.id` from Stage 2 |

**Validation in `_parse_relationships`:**
- Relationships with invalid `relationship_type` are **skipped with a warning log** (`invalid_edge_type`).
- Incomplete relationships (missing `source_text` or `target_text`) are skipped.
- **`permitted_connections` validation is DISABLED** (commented out in `_parse_relationships`) — the LLM is methodology-aware from the system prompt and unrestricted edge extraction is intentional for experimentation.

### 4. Extraction Pipeline (ExtractionService.extract())

**Step 1: Fast extractability check** (`_fast_extractability_check`)
- Filters out responses too short for meaningful extraction:
  - Word count < `min_word_count` (default 3)
  - Yes/no minimal responses ("yes", "no", "yeah", "nope", "sure", "okay", etc.)
  - Single word responses
- Returns `ExtractionResult(is_extractable=False, extractability_reason=...)` without LLM call

**Step 2: LLM extraction** (`_extract_via_llm`)
- Builds methodology-aware system prompt via `get_extraction_system_prompt()`:
  - Node type descriptions from `schema.get_node_descriptions()`
  - Edge type descriptions from `schema.get_edge_descriptions()`
  - Methodology-specific `extraction_guidelines` from YAML
  - Methodology-specific `relationship_examples` from YAML
  - `concept_naming_convention` instruction if specified
  - Element list for linking if `concept_id` provided
- Builds user prompt via `get_extraction_user_prompt()`:
  - Current user utterance text
  - Optional context from previous turns (conversation history)
- LLM parameters: `temperature=0.4`, `max_tokens=4000`, `response_format={"type": "json_object"}`
- Parses JSON response via `parse_extraction_response()`

**Step 3: Concept parsing** (`_parse_concepts`)
- Validates `node_type` against methodology schema
- Enriches valid concepts with `is_terminal` and `level` from schema
- Sets `source_utterance_id` for traceability
- Links concepts to methodology elements via:
  1. LLM-provided `linked_elements` field (preferred)
  2. Alias-matching fallback if LLM doesn't provide links

**Step 4: Relationship parsing** (`_parse_relationships`)
- Validates `relationship_type` against methodology schema
- **Note:** `permitted_connections` validation is disabled (LLM is methodology-aware)
- Skips incomplete relationships (missing source or target)

**Step 5: Return ExtractionResult**
- Contains validated concepts, relationships, latency_ms, timestamp

### 5. LLM Prompt Architecture

**System prompt structure** (`get_extraction_system_prompt`):

1. **Universal principles** (hardcoded, apply to all methodologies):
   - Only extract concepts explicitly mentioned or clearly implied
   - Cross-turn relationship bridging (connect new concepts to existing ones)
   - Bridge Q→A pairs (interviewer question → respondent answer)
   - Do NOT re-extract existing concepts

2. **Methodology-specific content** (loaded from YAML):
   - Valid node types with descriptions
   - Valid edge types with descriptions
   - `extraction_guidelines`: methodology-specific extraction rules
   - `relationship_examples`: named examples with description, example text, extraction pattern
   - `concept_naming_convention`: instruction for how to phrase concept labels

3. **Element linking section** (if `concept_id` provided):
   - Lists predefined elements with aliases
   - Instructs LLM to link concepts to element IDs

4. **Output format specification:**
   - JSON structure with `concepts` and `relationships` arrays
   - Field definitions match `ExtractedConcept` and `ExtractedRelationship` schemas

**User prompt structure** (`get_extraction_user_prompt`):
- Previous context (conversation history from recent turns) if provided
- Current user utterance text to extract from

**Cross-turn relationship bridging (CRITICAL):**
- Prompt instructs LLM to reference existing graph concepts from previous turns
- Creates relationships from question topics → answer concepts
- Avoids re-extracting concepts that already exist in the graph

### 6. SRL Preprocessing Integration

Stage 2.5 (`SRLPreprocessingStage`) optionally enriches extraction with linguistic structure:

**Inputs:**
- `user_utterance` from Stage 2
- `interviewer_question` (last system utterance from recent_utterances)

**Outputs** (`SrlPreprocessingOutput`):
- `discourse_relations: List[Dict]` — discourse markers (e.g., "because", "so", "but")
- `srl_frames: List[Dict]` — semantic role labeling frames (agent, predicate, argument)

**Usage in extraction:**
- Currently **not directly passed** to extraction LLM prompts
- SRL data is available in `context.srl_preprocessing_output` for future enhancement
- Potential use: enrich extraction prompts with discourse relations as hints for relationship extraction

**Feature flag:**
- Gated by `settings.enable_srl`
- If disabled, stage writes empty `SrlPreprocessingOutput()` and skips gracefully

### 7. Methodology-Specific Extraction Control

Extraction behavior is controlled by YAML fields in `config/methodologies/*.yaml`:

**Ontology control:**
- `ontology.nodes:` — defines valid node types with descriptions, examples, level, terminal
- `ontology.edges:` — defines valid edge types with descriptions, permitted_connections

**Extraction guidelines:**
- `ontology.extraction_guidelines:` — methodology-specific extraction rules
  - Example MEC guideline: "For Means-End Chain interviews, extract BOTH explicit AND implicit relationships"
  - Example MEC guideline: "Target 2-3x more edges than nodes for a well-structured MEC graph"

**Relationship examples:**
- `ontology.relationship_examples:` — named examples with:
  - `description`: what this example demonstrates
  - `example`: sample text
  - `extraction`: expected extraction pattern

**Concept naming:**
- `ontology.concept_naming_convention:` — instruction for how to phrase concept labels
  - Example: "Name concepts as concise noun phrases. Use present tense. Prefer respondent's language when clear."
  - If not specified, defaults to: "Name concepts concisely according to their node type. Use the node type descriptions and examples above as naming models."

**Extractability criteria:**
- `ontology.extractability_criteria.extractable_contains:` — content that indicates extractable text
- `ontology.extractability_criteria.non_extractable_contains:` — content that indicates non-extractable text
- Currently used for LLM-based extractability check (optional, not used in MVP)

### 8. Element Linking (Canonical Slot Integration)

Concepts can be linked to methodology-defined elements for coverage tracking:

**When `concept_id` is provided to ExtractionService:**
1. Concept elements loaded via `load_concept(concept_id)`
2. Element alias map built from `element.label` + `element.aliases`
3. System prompt includes element list with IDs and aliases
4. LLM instructed to link concepts to element IDs via `linked_elements` field

**Fallback alias matching:**
- If LLM doesn't provide `linked_elements`, substring matching is used
- Checks if concept text contains any element alias (or vice versa)
- Logs `concept_linked_via_alias_fallback` on match

**Traceability:**
- `linked_elements` stored on `ExtractedConcept`
- Flows into `KGNode.linked_elements` after deduplication
- Used for canonical slot coverage tracking in Stage 4.5

### 9. Extraction → GraphUpdateStage Contract

**What GraphUpdateStage expects from ExtractionResult:**

1. **Concepts** with valid `node_type` (validated against methodology schema)
2. **Relationships** with valid `relationship_type` and resolved source/target texts
3. **`source_utterance_id`** on all concepts and relationships for provenance
4. **Empty extraction is valid** — `ExtractionResult(is_extractable=False)` with empty lists is normal for short responses

**Deduplication in GraphUpdateStage:**
- Concepts are deduplicated against existing nodes via:
  1. Exact label + node_type match (case-insensitive)
  2. Semantic similarity match (if embedding_service configured, threshold 0.80)
- Relationships are resolved to deduplicated node IDs
- Duplicate edges (same source, target, edge_type) are merged

### 10. Key Constraints

1. **Always validate node_type and relationship_type against the methodology schema.** Invalid types are silently skipped with warning logs — if extraction is producing zero concepts/relationships, check for `invalid_node_type` / `invalid_edge_type` log entries.
2. **Always set source_utterance_id for traceability.** The traceability chain (utterance → concept → graph node) depends on this field. The fallback value `"unknown"` breaks provenance.
3. **Never treat empty extraction as an error.** `ExtractionResult(is_extractable=False)` with empty concepts/relationships is a normal outcome for short or ambiguous responses.
4. **Always include methodology-specific content in the system prompt.** The extraction prompt must reflect the current ontology — stale prompts produce nodes with invalid types that are silently dropped.
5. **Never bypass the extractability check unless testing.** The fast heuristic filter prevents wasted LLM calls on low-information responses. Only skip via `skip_extractability_check=True` for testing.
6. **Always use temperature 0.4 for extraction.** This balances consistency with relationship inference across conversation context. Lower temperatures (0.0-0.2) miss implicit relationships; higher temperatures (0.7+) produce hallucinations.
7. **Never modify extraction output after timestamp is set.** The timestamp is the freshness anchor for Stage 6 staleness detection. Post-hoc modification breaks freshness guarantees.
8. **Always pass the correct methodology parameter to extract().** The methodology determines which ontology is used for validation. Passing the wrong methodology produces schema mismatches and silent drops.
9. **Never rely on permitted_connections validation.** It is intentionally disabled to allow unrestricted edge extraction. The LLM is methodology-aware from the system prompt.
10. **Always verify concept_naming_convention is followed.** If concepts are inconsistently named, deduplication fails and the graph fragments. Check the methodology YAML for naming instructions.

### 11. Anti-patterns

Each entry below records a real failure observed in this codebase or a design constraint enforced by the architecture. If you are tempted to do any of these, stop and re-read the relevant Domain Knowledge section.

- **Extracting without SRL context when it's available.** Stage 2.5 produces discourse relations and SRL frames that could hint at implicit relationships. Currently not passed to extraction LLM, but the data exists for future enhancement.
- **Ignoring concept_naming_convention from YAML.** Concepts phrased inconsistently (e.g., some as noun phrases, some as full sentences) fail semantic deduplication and fragment the graph. Always check the methodology YAML for naming instructions.
- **Creating relationships without permitted_connections check.** While the validation is intentionally disabled in `_parse_relationships`, the LLM prompt includes permitted_connections in edge descriptions. If the LLM produces invalid connections, fix the prompt, not the validation.
- **Treating empty extraction as an error.** `ExtractionResult(is_extractable=False)` is normal for short responses ("sure", "okay", "I don't know"). Raising an error breaks the pipeline on valid input.
- **Forgetting to set source_utterance_id.** The traceability chain breaks without this field. Concepts without provenance cannot be audited or debugged. The fallback `"unknown"` masks the real problem.
- **Using the wrong methodology parameter.** ExtractionService.extract() requires the methodology name (e.g., `"means_end_chain"`). Passing the wrong methodology loads the wrong ontology and causes schema validation failures.
- **Modifying extraction output after timestamp is set.** The timestamp anchors freshness detection in Stage 6. Post-hoc modification (e.g., adding concepts after the fact) produces stale data that fails staleness checks.
- **Assuming permitted_connections is enforced.** The validation is commented out in `_parse_relationships`. The LLM is expected to produce valid connections from the methodology prompt alone. If invalid connections appear, fix the prompt, not the code.
- **Skipping the extractability check in production.** The fast heuristic filter prevents wasted LLM calls. Only skip via `skip_extractability_check=True` for testing.
- **Using temperature outside 0.3-0.5 range.** Temperatures below 0.3 miss implicit relationships; temperatures above 0.5 produce hallucinations. 0.4 is the balanced default.
- **Forgetting to link elements when concept_id is provided.** If `concept_id` is set but `linked_elements` is always empty, check: (1) element list is included in system prompt, (2) LLM is instructed to link, (3) alias matching fallback is enabled.
- **Treating invalid_node_type logs as warnings.** Concepts with invalid node types are **silently dropped**, not just warned. If extraction produces zero concepts, check for `invalid_node_type` log entries — the ontology is out of sync with the prompt.

## Context Documents

Consult these Tier 3 docs for full specifications and edge cases:

- `.claude/context/extraction.md` — full extraction pipeline spec, correctness requirements, symptom→cause→fix table
- `.claude/context/graph-dedup.md` — how extracted concepts flow into GraphUpdateStage, deduplication logic, cross-turn edge resolution
- `src/services/extraction_service.py` — ExtractionService implementation with all pipeline stages
- `src/llm/prompts/extraction.py` — system/user prompt builders, response parser, prompt architecture
- `src/domain/models/extraction.py` — ExtractedConcept, ExtractedRelationship, ExtractionResult schemas
- `src/domain/models/methodology_schema.py` — MethodologySchema, ontology loading, validation methods
- `src/services/turn_pipeline/stages/extraction_stage.py` — Stage 3 wiring
- `src/services/turn_pipeline/stages/srl_preprocessing_stage.py` — Stage 2.5 SRL enrichment
- `src/services/turn_pipeline/stages/graph_update_stage.py` — Stage 4 consumption of ExtractionResult
- `config/methodologies/*.yaml` — methodology-specific extraction control (ontology, guidelines, examples, naming)

## Diagnostic Triage

When fixing ruff or pyright diagnostics, invoke `/deep-code-quality` to categorize before fixing. Never suppress security warnings or add `Optional` to mask missing error handling — fix the root cause.
