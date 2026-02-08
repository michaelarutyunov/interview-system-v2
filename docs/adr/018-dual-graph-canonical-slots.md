# ADR-018: Dual-Graph Architecture with Canonical Slots

**Status:** Accepted
**Date:** 2026-02-08
**Context:** Phase 2-3 (Dual-Graph Architecture)

## Context

The interview system extracts knowledge graph nodes from respondent language. A key problem emerged:

**Problem:** Respondent paraphrases fragment signal detection and exhaust tracking.

### Example Fragmentation

Respondent says:
1. "I like oat milk because it has few additives"
2. "The simple ingredients are important to me"
3. "I avoid gums and carrageenan"

These become 3 surface nodes (`few_additives`, `simple_ingredients`, `avoid_gums`) that represent the SAME latent concept. This causes:

1. **Signal Fragmentation:** Exhaustion tracking sees 3 "fresh" concepts when actually 1 concept has been discussed 3 times
2. **Noise:** Strategy selection gets misleading signals - looks like 3 separate topics when it's 1 topic
3. **Poor Strategy:** System keeps asking about "additives" because each surface node looks "fresh"

### Previous Attempts

1. **Better deduplication** (Phase 1): Tried semantic similarity at extraction time - insufficient, LLM uses varied language
2. **Prompt engineering**: Asked LLM to consolidate - unreliable, depends on LLM "mood"
3. **Post-hoc clustering**: Clustered nodes after interview - too late, doesn't help real-time strategy

## Decision

**Adopt a dual-graph architecture with canonical slot discovery:**

1. **Surface Graph:** Original extraction (respondent's exact language), high fidelity
2. **Canonical Graph:** Deduplicated abstract concepts (canonical slots), stable signals

```
Surface Nodes                     Canonical Slots
-------------                    ---------------
"few additives"      ──────────>  "ingredient_quality"
"simple ingredients" ──────────>  (slot_name)
"avoiding gums"     ──────────>
```

### Key Properties

- **Unidirectional flow:** Surface → Canonical only (never reverse)
- **LLM-generated abstractions:** Canonical slot names/descriptions from LLM
- **Embedding similarity:** spaCy en_core_web_md for candidate matching
- **Candidate → Active lifecycle:** Slots promoted after sufficient support

### Architecture

```
Stage 4: GraphUpdate (surface graph)
    │
    ▼
Stage 4.5: SlotDiscovery (canonical slots)
    ├─ LLM proposes canonical slot names/descriptions
    ├─ Embedding similarity matches existing slots
    ├─ Surface nodes mapped to canonical slots
    └─ Canonical edges aggregated from surface edges
    │
    ▼
Stage 5: StateComputation (both graphs)
    ├─ Surface: GraphState (nodes, edges, orphans)
    └─ Canonical: CanonicalGraphState (concepts, edges, orphans)
```

## Consequences

### Positive

1. **Cleaner signals:** Exhaustion tracking sees "1 concept discussed 3 times" not "3 fresh concepts"
2. **Accurate strategy:** System recognizes topic exhaustion correctly
3. **Stable metrics:** Canonical concept count stable across paraphrase variations
4. **Queryable provenance:** `surface_to_slot_mapping` table shows which surface nodes map to each canonical slot

### Negative

1. **+2-3s latency per turn:** LLM call for slot discovery + embedding computation
2. **Complexity:** More moving parts (slot discovery, embedding service, canonical repo)
3. **Debugging difficulty:** Two graphs to understand instead of one

### Mitigations

- Latency acceptable within 200ms budget (confirmed in Phase 1 SRL testing)
- Graceful degradation via `enable_canonical_slots` flag for testing/A-B
- Clear separation: surface for fidelity, canonical for signals

## Alternatives Considered

### 1. Single Graph with Deduplication

**Rejected:** Doesn't preserve respondent language fidelity. We need original language for traceability.

### 2. LLM Consolidation at Extraction Time

**Rejected:** Unreliable. LLM may or may not consolidate based on context/temperature.

### 3. Post-Interview Clustering

**Rejected:** Doesn't help real-time strategy selection. Signals needed DURING interview.

## Implementation Reference

- **Bead eejs:** `CanonicalSlotRepository` - SQLite tables for slots, mappings, edges
- **Bead lmyr:** `EmbeddingService` - spaCy en_core_web_md lazy-loading
- **Bead yuhv:** `SlotDiscoveryStage` (Stage 4.5) - Maps surface → canonical
- **Bead ht0e:** `NodeStateTracker` - Keys by `canonical_slot_id` after Phase 3
- **Bead 3pna:** Canonical graph signals for strategy selection

## Terminology

- **Surface node:** Knowledge graph node from extraction (respondent language)
- **Canonical slot:** Deduplicated abstract concept (LLM-generated name)
- **Dual-graph:** Two separate graph representations (surface + canonical)
- **Slot discovery:** Process of mapping surface nodes to canonical slots
