# Extraction
## Current Version: 1.0

## Core Mechanics

`ExtractionService` (Stage 3 — `extraction_stage.py`) extracts **concepts only** from user utterances using an LLM (Sonnet), guided by the active methodology's ontology. Edges are extracted separately by Stage 4.5B (Haiku) using `src/llm/prompts/edge_extraction.py`.

**Pipeline per turn (Stage 3):**
1. **Fast extractability check** — heuristics filter out responses that are too short (< `min_word_count`, default 3), single words, or pure yes/no affirmatives. Returns `is_extractable=False` without calling LLM.
2. **LLM extraction** — calls `_extract_via_llm()` with a methodology-aware system prompt (node types, naming convention from `MethodologySchema`). Temperature 0.2, max tokens 4000, `response_format={"type": "json_object"}`. System prompt is passed with `cache_control` for Anthropic prompt caching.
3. **Concept parsing** (`_parse_concepts`) — validates each concept's `node_type` against the methodology schema. Enriches valid concepts with `is_terminal` and `level`. Sets `source_utterance_id` for traceability.
4. **Element linking** — if `concept_id` is configured, concepts are linked to methodology elements via LLM-provided `linked_elements` field.

Returns `ExtractionResult` with `concepts`, `is_extractable`, and `latency_ms`.

### Stage 4.5B Edge Extraction

A separate Haiku prompt (`src/llm/prompts/edge_extraction.py`) handles all edge identification. Key differences from Stage 3:
- **Input**: post-dedup node IDs (from GraphUpdateStage), not raw concept texts
- **Candidate assembly**: FOCUS × CURRENT/NEIGHBOR/RECENT node pairs, filtered to pairs where at least one endpoint is CURRENT (novel-this-turn)
- **Candidate pair format**: compact single-line (`pair="id1,id2" (type1 -> type2)`); node labels omitted since they're listed in the Candidate Nodes section above
- **Methodology content**: rendered via `MethodologySchema` accessors (`get_edge_descriptions_with_connections()`, `get_chain_relevant_edge_types()`)
- **Output**: XML with structured reasoning (see below), confirmed edges with confidence (high/medium/low) + supporting spans, rejected candidates with 5-code taxonomy (no reasoning)
- **Model**: Haiku (was Sonnet; switched May 2026 after diff harness showed equivalent edge quality at 5x lower latency)

**Structured reasoning format (May 2026):** Reasoning was changed from free-form prose (2-5 sentences, ~75 tokens/pair) to structured XML attributes (~18 tokens/pair) to reduce output token consumption and eliminate Haiku timeouts on high-pair-count turns. For rejected candidates, reasoning is omitted entirely — the 5-code taxonomy captures the rationale.

Confirmed edges use `<reasoning assertion="explicit|implicit|inferred" direction="clear|uncertain" frame="respondent|minor_influence|contaminated"/>`. The three axes map to confidence:
- **high**: assertion=explicit, direction=clear, frame=respondent
- **medium**: any axis at the middle tier
- **low**: assertion=inferred, direction=uncertain, or frame=contaminated

The parser (`_parse_confirmed_candidate`) is backward-compatible: if reasoning has text content (old format), it's used as-is. The `ConfirmedEdge` model stores both the derived `reasoning_summary` string and the raw axis values (`assertion`, `direction`, `frame`).

**Output token budget (per candidate pair, after optimization):**
| Component | Rejected | Confirmed |
|-----------|----------|-----------|
| XML structural tags | ~60 chars | ~80 chars |
| `<evidence>` (verbatim) | ~80 chars | ~100 chars |
| `<reasoning>` | — | ~70 chars (structured) |
| Verdict + reason/type/confidence | ~40 chars | ~80 chars |
| Node IDs | ~70 chars | ~70 chars |
| **Total** | **~250 chars** | **~400 chars** |

Average ~75 tokens/pair, down from ~243 before optimization (69% reduction). 35 pairs → ~2,600 output tokens (was ~8,500).

**Rejected edge persistence (May 2026):** Rejected candidates are now persisted to `kg_rejected_edges` table (session_id, turn_number, source_node_id, target_node_id, rejection_reason, reasoning_summary). This enables per-turn diagnostic reports via `scripts/reporting/generate_turn_diagnostics.py` → `05_turn_diagnostics.md`.

**Turn diagnostics report:** `scripts/reporting/generate_turn_diagnostics.py` queries kg_nodes, kg_edges, kg_rejected_edges, scoring_history, and utterances to produce a per-turn markdown report with node extraction tables, confirmed edge tables (including structured reasoning attributes), rejected candidate summaries with reason counts, and expandable per-pair detail sections.

**Fail-fast:** `ExtractionError` is raised immediately on LLM failure — no silent degradation.

## Prompt Caching

Extraction uses Anthropic prompt caching to reduce input token cost on turns 2+. The system prompt (methodology instructions, node types, edge types, edge-case rules) is stable across turns within a session — no timestamps, session IDs, or non-deterministic serialization.

**Architecture**: `_extract_via_llm()` builds the system prompt as a block-list with a `cache_control` marker:
```python
system_blocks = [
    {"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}
]
```
The user prompt (response text + context) varies per turn and sits in `messages`, after the cached system prefix.

**Client-layer handling**: `AnthropicClient.complete()` accepts `system` as either `str` (legacy, no caching) or `list[dict]` (block-list with cache_control). Non-Anthropic providers (OpenAI-compatible) flatten block-lists to a plain string, stripping `cache_control` — no provider leakage.

**Token threshold**: Anthropic caching requires a minimum cacheable prefix. Empirically confirmed (2026-04): `claude-sonnet-4-6` minimum is exactly 2048 tokens (NOT 1024 as Anthropic docs claim). All 5 methodology extraction prompts exceed this threshold after the edge-case additions (~320 tokens of contradiction/reformulation/partial-info rules, disambiguation rule, and worked example).

**Verification**: Cache hits visible in `llm_call_complete` logs:
- `cache_creation_input_tokens`: tokens written to cache (1.25× write premium)
- `cache_read_input_tokens`: tokens served from cache (0.1× base input price)
- Both fields extracted from Anthropic response `usage` object

**Cost impact**: ~2658 tokens cached per extraction call. After the initial write, subsequent calls pay 0.1× instead of 1× for the cached portion — ~90% cost reduction on that prefix. Latency impact is minimal (output token generation dominates).

**Design principle**: "capability at the client layer, policy at the call site." Future stages (signal scoring, question generation) can enable caching by switching from `system=str` to `system=[{block with cache_control}]` — no further client-layer work needed.

## Node Type Description Pipeline

The extraction prompt includes per-node-type descriptions built by `MethodologySchema.get_node_descriptions()`. Each entry combines the node's `description` and (when defined) up to 3 `non_attribute_examples` — counter-examples showing what does **not** belong in this node type.

**`node.examples` are NOT injected into the extraction prompt.** `get_node_descriptions()` only reads `description` and `non_attribute_examples`. Positive `examples` lists in the YAML are parsed by Pydantic but never forwarded to the LLM. Do not add domain examples expecting them to influence extraction — use the `description` field or `non_attribute_examples` instead. (Decision rationale: self-test heuristics in `description` generalise across domains better than domain-specific example lists.)

Counter-examples flow to the extraction LLM as: `"<description> NOT this type: counter1; counter2"`.

**Important:** `OntologySpec` uses `model_config = ConfigDict(extra="ignore")`. Unknown fields on a node spec are silently dropped by Pydantic. If you add a new field to `NodeTypeSpec` it must be declared as a class attribute — adding it only to the YAML will have no effect. The `non_attribute_examples` field was added to `NodeTypeSpec` after being silently dropped for multiple simulation iterations.

Use `non_attribute_examples` when a node type boundary is ambiguous — e.g., when a related concept (like `functional_consequence`) is systematically misclassified as this type. Positive examples alone are insufficient when LLMs generalise the category too broadly.

## Edge-Case Handling Rules

The extraction prompt includes explicit rules for three failure modes observed in simulation testing:

1. **Contradictions**: Both concepts extracted (graph captures thinking evolution). No overwriting.
2. **Reformulations**: Only one concept extracted (most precise phrasing). Source quote from clearest formulation.
3. **Partial information**: Implied concepts extracted only with confidence 0.6–0.75. Ambiguous hints omitted.

Additionally, a **disambiguation rule** handles same-word-different-meaning across turns (e.g., "routine" as exercise vs. coffee ritual) — extracted as separate concepts with disambiguating labels.

These rules add ~320 tokens to the system prompt, pushing all 5 methodologies above the 2048-token caching threshold.

## Prompt Architecture Boundaries

The extraction system prompt (`src/llm/prompts/extraction.py:get_extraction_system_prompt()`) has a strict boundary between hardcoded and methodology-driven content:

| Section | Source | Applies to |
|---------|--------|------------|
| Valid Node Types | `methodology_schema.py:get_node_descriptions()` → YAML ontology | All, rendered with `[L0]`–`[L4]` prefixes |
| Valid Edge Types | `methodology_schema.py:get_edge_descriptions_with_connections()` → YAML ontology | All |
| Universal Extraction Principles | Hardcoded in `extraction.py` | All |
| Edge-Case Handling | Hardcoded in `extraction.py` | All |
| Cross-Turn Bridging | Hardcoded in `extraction.py` (uses `{primary_edge_type}` from schema) | All |
| Methodology Guidelines | YAML `extraction_guidelines` | Methodology-specific |
| Relationship Examples | YAML `relationship_examples` | Methodology-specific |
| Level-Aware Relationship Creation | Hardcoded, gated on ≥2 ontology levels | Chain methodologies only |
| Output Format | Hardcoded in `extraction.py` | All |

**Contamination rule:** Methodology-specific content (node types, edge types, guidelines, examples) lives in YAML files. The hardcoded sections must remain methodology-agnostic. A worked example hardcoding MEC types was removed April 2026 — it contaminated non-MEC extraction prompts. The YAML `relationship_examples` already provide methodology-specific examples.

## Level-Aware Extraction

Node type descriptions now include ontology level prefixes rendered by `methodology_schema.py:get_node_descriptions()`:

```
[L0] Event or stimulus that initiates the job (e.g., 'feeling tired...')
[L4] What the customer currently hires to make progress [TERMINAL — end of chain]
```

The `[TERMINAL]` suffix marks types where `terminal: true` in the ontology. Flat methodologies (CJM, RG with `level: None`) get no prefixes.

A **Level-Aware Relationship Creation** section is appended to the prompt when the methodology has ≥2 distinct ontology levels:

- Prefer adjacent levels (L_n → L_n+1) for strongest chains
- Skip connections (L0→L3) are valid but use lower confidence (0.6–0.75)
- Lateral connections within same level are valid for elaboration
- Downward connections should use `addresses`/`achieves` edge types

This section is gated — CJM and RG (flat ontologies) do not receive it.

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

The bridge instruction is assembled dynamically from three strategy config fields (see Strategy-Driven Bridge Parameters above). `_get_bridge_config()` looks up the previous turn's strategy by name in the methodology registry and reads `bridge_direction`, `bridge_target`, and `extraction_mode`.

**When `focus_history` is non-empty and strategy is NOT `revitalize`** (turn 2+):

The instruction has three parts composed from config:
1. **Extraction mode clause** — `extract_new` adds "If the response introduces concepts at multiple levels below the focus, create relationships for each." `prefer_existing` adds "Focus on extracting relationships to existing graph nodes rather than new concepts."
2. **Bridge clause** — `forward` produces `source_text="{focus}" → {target_desc}`. `backward` produces `{target_desc} → target_text="{focus}"`.
3. **Target description** — resolved from `bridge_target` via `_BRIDGE_TARGET_DESCRIPTIONS` (e.g., `most_abstract` → "the most abstract new concept you extracted...").

The `focus_label` is `focus_history[-1].label` from `ContextLoadingOutput` — the node the previous turn's question was built around. This makes the bridge source deterministic: the LLM receives the exact node label rather than inferring "the question's topic" from the raw question text.

**When the previous strategy was `revitalize`**:

The bridge is suppressed entirely — "This is a new topic — extract fresh concepts without forcing a relationship to previous graph nodes." Revitalize represents an abandoned focus, so forcing a connection is semantically wrong regardless of methodology. This is the only hardcoded strategy-name reference in the extraction stage.

**When `focus_history` is empty** (turn 1):

> *"Extract concepts ONLY from the Respondent's answer above. Do NOT extract new concepts from the interviewer's question text."*

No bridge relationship is requested on turn 1 because there is no prior focus node.

### Strategy-Driven Bridge Parameters

When the bridge task instruction is emitted, `ExtractionStage` reads the previous turn's strategy config via `_get_bridge_config()` to construct the bridge clause dynamically. Three YAML fields on each strategy control the behavior:

| Field | Values | Default | Effect |
|-------|--------|---------|--------|
| `bridge_direction` | `forward`, `backward` | `forward` | `forward`: `source_text="{focus}" → {new concept}`. `backward`: `{new concept} → target_text="{focus}"`. |
| `bridge_target` | `most_concrete`, `most_abstract`, `either` | `most_concrete` | Which new concept to bridge to. `most_abstract` for ascend (laddering up), `most_concrete` for ground (tracing antecedents), `either` for anchor (flexible connection). |
| `extraction_mode` | `extract_new`, `prefer_existing` | `extract_new` | `extract_new`: normal behavior — extract new concepts at multiple levels. `prefer_existing`: suppress new node creation, focus on connecting to already-extracted graph nodes (used by `anchor`). |

These fields replaced the hardcoded `_LEVEL_HINTS` dict in April 2026 (beads 4hvs/k2ps/as75/9syp). The bridge clause and extraction instruction are now assembled from these three config values at extraction time, with no strategy-name-keyed code remaining.

**Revitalize is the sole exception**: its bridge is suppressed entirely in code (previous focus was abandoned). This is a universal pipeline guard, not methodology-specific behavior.

**Default safety**: all three fields are optional with safe defaults (`forward`, `most_concrete`, `extract_new`). Existing methodologies without these fields get the previous hardcoded behavior — no YAML migration is required for non-chain-aware methodologies (CJM, RG).

**Per-methodology assignments** (chain-aware methodologies only):

| Strategy | bridge_direction | bridge_target | extraction_mode |
|----------|-----------------|---------------|-----------------|
| ascend | forward | most_abstract | extract_new |
| ground | backward | most_concrete | extract_new |
| bridge | forward | most_abstract | extract_new |
| branch | forward | most_concrete | extract_new |
| anchor | forward | either | prefer_existing |
| elaborate (JTBD) | forward | most_concrete | extract_new |
| elicit_narrative (CIT) | forward | most_concrete | extract_new |
| revitalize | — | — | — (bridge suppressed in code) |
| validate | — | — | — (no extraction expected) |

The key indirection: bridge parameters are read from the **previous** turn's strategy, not the current turn's. When strategy A is selected on turn N, its bridge parameters affect the extraction prompt on turn N+1 (the respondent's answer to the question that strategy A generated).

### Bridge Target Selection

The bridge target is no longer hardcoded to "most concrete." It is now driven by the previous turn's `bridge_target` strategy config field (see Strategy-Driven Bridge Parameters above). Each strategy specifies whether to bridge to the most concrete, most abstract, or either new concept. This prevents both the "always bridges to abstract" bias (which would skip intermediate levels) and the reverse "always bridges to concrete" bias (which would prevent ascend from laddering upward).

### Why "extract from respondent only"

The graph represents the respondent's mental model, not the interviewer's framing. Without the explicit prohibition, the LLM may extract concepts from the interviewer's question text (e.g., follow-up framing language that was not in the respondent's prior answers), creating interviewer-authored nodes indistinguishable from respondent-generated ones.

### Known gap: `source_quote` on bridge relationships

Bridge relationships have an inherent `source_quote` problem: the source node was mentioned in a prior turn, so there is no verbatim text in the current utterance to quote. The LLM may hallucinate a `source_quote` for bridge edges. This is a secondary issue — `source_quote` is not validated or used for graph construction — but may affect traceability audits.

### Diagnostic logs

| Log key | Meaning |
|---------|---------|
| `cross_turn_node_context_injected` | Node label list included; shows `node_label_count` and `context_length` |
| `cross_turn_node_context_skipped` | No existing nodes yet (turn 1 or empty graph) |

## Known Failure Modes

_No entries yet. Add failure patterns as they are discovered in this subsystem — each entry should describe the incorrect behavior, its consequence, and the correct approach._


## Key Files

- `src/services/extraction_service.py` — `ExtractionService` class
- `src/services/turn_pipeline/stages/extraction_stage.py` — Stage 3 wiring
- `src/llm/prompts/extraction.py` — prompt builders and response parser
- `src/llm/client.py` — LLM client with prompt caching infrastructure (block-list system prompts)
- `src/domain/models/extraction.py` — `ExtractedConcept`, `ExtractionResult`
- `src/domain/models/methodology_schema.py` — `MethodologySchema` (ontology validation)
- `config/methodologies/*.yaml` — node types, edge types, naming conventions
