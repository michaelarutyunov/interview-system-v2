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
- **Candidate assembly**: FOCUS × CURRENT/NEIGHBOR/RECENT node pairs, filtered to pairs where at least one endpoint is CURRENT (novel-this-turn). Utterance context: full conversation history (up to 30 utterances, covering a complete 15-turn interview) so Haiku can find cross-turn causal links (e.g. L0 trigger established in Turn 1 linked to L1 pain point introduced in Turn 3)
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

### Stage 4.5B — Methodology-Specific Calibration via `edge_extraction_notes`

The edge extraction system prompt accepts a `## Methodology-Specific Edge Extraction Notes:` section populated from `schema.method.get("edge_extraction_notes", "")` in `get_edge_extraction_system_prompt()`. This is the correct path for tuning Haiku's edge extraction behavior per methodology without hardcoding methodology names in Python.

**Two calibration problems addressed by `edge_extraction_notes`:**

1. **Frame contamination over-rejection in laddering methodologies (JTBD, MEC)**: The rejection taxonomy includes `question_frame_contamination` for when the interviewer's question supplies the causal frame and the respondent merely confirms a topic. In JTBD/MEC mid-phase, *every* ascend/ground question inherently frames upward movement ("Why does X matter?", "What leads to X?") — this is the methodology's mechanism, not contamination. Without calibration, Haiku systematically rejects these as `question_frame_contamination`, producing near-zero edge yield on emotional/abstract turns (confirmed across 3 simulation runs: 11/14 turns with 0 edges). The `edge_extraction_notes` instructs: treat inherent laddering framing as `frame=minor_influence` with `confidence=medium`; reserve `contaminated`/rejection for cases where the respondent's answer confirms a topic without asserting the causal direction at all.

2. **Level-skipping produces zero full chains**: Edge extraction naturally connects semantically related concepts regardless of ontology level adjacency (e.g., `job_trigger [L0]` → `emotional_job [L3]`, skipping L1 and L2). The chain builder correctly classifies these level-skipping edges as "advanced" chains rather than "full" chains. This was confirmed as a systematic failure across 3 independent runs (0-2 full chains per 15-turn interview). The `edge_extraction_notes` instructs: strongly prefer level-adjacent edges (L_n → L_n+1); only confirm level-skipping edges when the respondent's language explicitly connects the concepts with no intermediate step.

**Note on distinction with Stage 3**: Stage 3 (concept extraction) uses `extraction_guidelines` on the ontology spec — a list of strings guiding *what to extract*. Stage 4.5B uses `edge_extraction_notes` on the `method:` dict — calibrating *how to evaluate candidate pairs*. These are separate prompts, separate LLM calls (Sonnet vs. Haiku), and separate calibration paths. Do not conflate them.

### Stage 4.5B — Candidate Pair Selection and Timeout Budget

Candidate pairs are built by `_build_candidate_pairs_section()` in `edge_extraction_prefetch_stage.py`. Only pairs where at least one endpoint is CURRENT (extracted this turn) are evaluated — pre-existing node pairs (FOCUS×NEIGHBOR, FOCUS×RECENT) were evaluable in earlier turns and are excluded to avoid O(N²) growth.

Pairs are emitted in priority order within a hard cap of 40:
1. **CURRENT × FOCUS** — highest priority: focus node was actively discussed this turn
2. **CURRENT × NEIGHBOR** — direct graph neighbours of FOCUS
3. **CURRENT × CURRENT** — share the same current turn's utterances
4. **CURRENT × RECENT** — lower priority: previous-turn nodes
5. **CURRENT × OPENING** — lowest priority: Turn 0 nodes, re-included for turns 2–5 only

With full conversation history passed as utterance context, the priority ordering affects which pairs get evaluated when the cap is hit, not which utterances are visible to Haiku — Haiku can now see the full conversation for all pairs.

**Turn 0 orphan architecture**: The opening turn (Turn 0) extracts 5–9 rich L1/L2 concepts (job contexts, pain points, gain points, job statements) that become permanent orphans without the OPENING bucket because: (1) they appear as RECENT in Turn 1 but get cut by the 40-pair cap when higher-priority pairs fill it, and (2) from Turn 2 onward they are absent from the candidate set entirely. The OPENING tag gives them a second evaluation window during early turns before the conversation diverges. After Turn 5 the concepts are typically too contextually distant to form valid edges.

**Rejection code diagnostic**: When analyzing edge extraction failure, check the rejection code distribution in `edge_rejected_summary` logs:
- `insufficient_evidence` > 50% of rejections → the utterance context is the bottleneck, not Haiku's calibration. Haiku cannot find the cross-turn connective tissue because the assembled context doesn't contain it. Root cause: fragmented per-node utterance assembly. Fix: full conversation history.
- `type_constraint_violation` + `semantic_irrelevance` dominant → correct behavior. Haiku is rejecting genuinely invalid pairs.
- `question_frame_contamination` dominant in mid-phase for laddering methodologies → over-rejection due to inherent laddering framing. Fix: `edge_extraction_notes` in YAML.

**Negation check**: The prompt includes an explicit "Negation Check" principle: if the supporting span describes the *absence* or *opposite* of the proposed relationship (e.g. "I don't think about health when at home" cited for `at_home → triggers → health_mindset`), reject with `insufficient_evidence`. Co-occurrence is not evidence; negation is anti-evidence. This catches directional inversion: edges where the quote contradicts rather than supports the claimed direction, which previously passed as `medium` confidence.

**Why the cap matters**: At 30s timeout (edge_extraction client config), Haiku evaluates roughly 35-40 pairs reliably. Turns with many CURRENT nodes (e.g., 8 nodes × 6 existing = 76 uncapped pairs) previously caused silent timeouts — the bridge stage received no result and logged nothing because the asyncio task stored the `LLMTimeoutError` which the bridge caught but at a log level filtered in simulation exports. The 40-pair cap prevents this. The `pair_count` field in `edge_extraction_prefetch_fired` logs now reflects the actual capped count, not the theoretical maximum.

**Silent timeout detection**: Stage 4.6 (EdgeExtractionBridgeStage) now emits `edge_extraction_bridge_task_missing_despite_nodes` at WARNING level when `_edge_extraction_task` is None but nodes were added this turn. This surfaces the failure pattern in logs without requiring manual cross-referencing of prefetch and bridge events.

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

1. **Level skipping produces zero full chains** — Edge extraction (Stage 4.5B, Haiku) connects semantically related concepts regardless of ontology level adjacency, producing edges that jump L0→L3 or L1→L4. The chain builder classifies these as "advanced" (with gaps) rather than "full" chains. Confirmed across 3 independent simulation runs (0-2 full chains per 15-turn interview). Fix: `edge_extraction_notes` in `method:` YAML block instructs Haiku to prefer level-adjacent edges. Stage 3 concept extraction uses a separate Level-Aware Relationship Creation section (hardcoded, gated on ≥2 ontology levels).

2. **Pair-count timeout causes silent bridge blackout** — When candidate pairs exceed ~40, the 30s Haiku timeout fires, `LLMTimeoutError` is stored, and Stage 4.6 receives no result. Symptom: 60s log gap between `canonical_skip` and next `graph_updated`, with no `bridge_complete` or failure entry. Fix: `_build_candidate_pairs_section()` caps at 40 pairs with priority ordering (FOCUS → NEIGHBOR → CURRENT → RECENT → OPENING). Stage 4.6 emits `edge_extraction_bridge_task_missing_despite_nodes` WARNING.

3. **`insufficient_evidence` dominating rejections (≥50%) signals missing utterance context, not over-rejection** — Root cause: Haiku cannot see the cross-turn utterance where the causal relationship was stated. Pre-fix, 86% of rejections were `insufficient_evidence` because utterance assembly was limited to 3–4 fragments from focus-node source utterances. Fix: pass full conversation history (`utterance_repo.get_recent(session_id, limit=30)`). After fix, dominant rejection codes shifted to `type_constraint_violation` and `semantic_irrelevance`.

4. **Directionally inverted edges confirmed at medium confidence due to negation-blind co-occurrence** — Haiku treats co-occurrence of two concept labels as sufficient evidence even when the utterance *negates* the relationship (e.g., "I don't think about health when at home" cited for `at_home → triggers → health_mindset`). The Negation Check principle in the prompt explicitly defines negation as `insufficient_evidence`. When reviewing confirmed edges, flag evidence quotes containing "don't", "not", "never" — these are inversion candidates.

5. **Turn 0 concepts become permanent orphans without the OPENING tag** — The opening turn extracts 5–9 rich concepts. They appear as RECENT in Turn 1 but get cut by the 40-pair cap. From Turn 2 onward they're absent from the candidate set. The OPENING tag re-includes them as a lowest-priority bucket for turns 2–5. Without it, chain reports show "stranded context" — semantically central concepts never connect.


## Key Files

- `src/services/extraction_service.py` — `ExtractionService` class
- `src/services/turn_pipeline/stages/extraction_stage.py` — Stage 3 wiring
- `src/llm/prompts/extraction.py` — prompt builders and response parser
- `src/llm/client.py` — LLM client with prompt caching infrastructure (block-list system prompts)
- `src/domain/models/extraction.py` — `ExtractedConcept`, `ExtractionResult`
- `src/domain/models/methodology_schema.py` — `MethodologySchema` (ontology validation)
- `config/methodologies/*.yaml` — node types, edge types, naming conventions
