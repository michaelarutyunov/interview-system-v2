# Phase 5: Canonical Slots Quality Review

**Date:** 2026-02-08
**Bead:** 817x - Manual quality review of canonical slots
**Session:** `ddc755ec-b286-4448-b7eb-6988a7bcbd52` (Scenario 4: Full system)

## Executive Summary

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Total Surface Nodes | 39 | - | - |
| Total Canonical Slots | 32 (30 candidates, 2 active) | - | - |
| Active/Candidate Ratio | 2/30 (6.7%) | ~20-30% | ⚠️ Low |
| Node-to-Slot Ratio | 1.22:1 | ~2:1 | ⚠️ High fragmentation |
| Canonical Edges | 0 | ~5-10 | ❌ Bug: field name mismatch (fixed) |
| False Merge Rate | 0% (0/39) | <5% | ✅ No wrong groupings |
| Missed Merge Rate (fragmentation) | ~28% (9/32) | <10% | ❌ High fragmentation |

## Key Findings

### 1. High Fragmentation (Candidate Proliferation)

**Issue:** Only 2 out of 32 slots reached "active" status (support_count ≥ 2).

**Evidence:**
- 30 candidate slots with support_count=1
- 2 active slots with support_count=3:
  - `minimal_ingredients` (attribute)
  - `sustained_energy` (functional_consequence)

**Analysis:** In a 5-turn interview with 39 surface nodes, we expect ~15-20 canonical slots with ~2-3 nodes each. The current 1.22:1 node-to-slot ratio indicates excessive fragmentation.

**Root Cause:** The LLM is proposing overly specific slot names rather than consolidating similar concepts. This may be due to:
- Prompt emphasizing "specific, focused categories" over consolidation
- No incentive for LLM to reuse existing slots
- Similarity threshold too high for effective merging

### 2. Missed Merges: Similar Concepts Not Consolidated (~28% Rate)

**Definition:** Missed merge = Two or more slots that SHOULD have been merged but weren't.

**Note on terminology:** The false merge rate (concepts *wrongly* grouped together) is 0%. This section documents the opposite problem: fragmentation where semantically equivalent concepts remain as separate slots.

**Identified Cases:**

| Slot A | Slot B | Issue |
|--------|--------|-------|
| `reduce_inflammation` | `reduced_inflammation` | Same concept, different grammatical form |
| `sustained_energy` | `sustained_energy_levels` | Same concept, different wording |
| `cognitive_performance` | `cognitive_focus_enhancement` | Semantically identical |
| `dairy_elimination` | `reducing_dairy_intake` | Same concept, different node_type |
| `digestive_comfort` | `reduced_bloating` | Both about absence of bloating |
| `increased_energy` | `post_meal_alertness` | Both about avoiding post-meal sluggishness |
| `improved_wellbeing` | `sustained_positive_affect` | Overlapping general wellbeing concepts |
| `improved_digestion` | `digestive_comfort` / `reduced_bloating` | Digestive improvement cluster (3 slots → 1) |
| `workout_energy_boost` | `sustained_energy` | Exercise energy overlaps with existing active slot |

**Total:** ~9 missed-merge pairs out of 32 slots (~28% fragmentation rate).

**Impact:** Fragmented slots prevent proper exhaustion tracking and dilute support counts. For example, the "digestive improvement" cluster spans 3 separate slots (`improved_digestion`, `digestive_comfort`, `reduced_bloating`), each with support_count=1, when consolidation would yield a single slot with support_count=3 (promoting it to "active").

### 3. All Similarity Scores are 1.0 (By Design)

**Observation:** Every surface-to-slot mapping has `similarity_score=1.0`.

**Root Cause (confirmed):** This is expected behavior. The `_find_or_create_slot` method in `canonical_slot_service.py` has three code paths:

1. **Exact match** (lines 286-331): LLM proposes a slot name that already exists → `similarity_score=1.0` (correct: exact match is perfect)
2. **New slot creation** (lines 371-388): LLM proposes a genuinely new concept → `similarity_score=1.0` (correct: surface nodes define their own slot)
3. **Embedding similarity** (lines 333-369): LLM proposes a name that doesn't match exactly but embeddings are similar → uses actual cosine similarity score

Paths 1 and 2 handle all current cases because:
- The LLM prompt encourages reusing existing slot names (incentivizes exact matches)
- When the LLM proposes a new name, it's usually for a genuinely distinct concept
- The embedding similarity threshold (0.88) is conservative, so Path 3 rarely triggers

**Conclusion:** Not a bug. The embedding similarity path is a fallback that will become more relevant as slot density increases in longer interviews. No action needed.

### 4. Zero Canonical Edges (Bug — Fixed)

**Issue:** No canonical edges were created despite 22 surface edges in the graph.

**Root Cause (confirmed):** Field name mismatch between pipeline stages.

- `GraphUpdateStage` produces edge dicts via `KGEdge.model_dump()` with keys `source_node_id` / `target_node_id`
- `GraphService.aggregate_surface_edges_to_canonical()` (line 412-413) read `edge.get("source_id")` / `edge.get("target_id")`
- Both returned `None`, failing the `if not all([...])` validation check
- All 22 surface edges were silently skipped with log: `surface_edge_skipped_missing_fields`

**Fix applied:** Changed `graph_service.py` lines 412-413 to read `source_node_id` / `target_node_id`. Updated docstring to match.

**Impact before fix:** Canonical graph had zero structural information. All signals based on edge density, connectivity, or path analysis returned empty/zero values.

### 5. Node Type Mismatches

**Observation:** Some semantically similar concepts have different `node_type` values:

| Concept | Slot A (type) | Slot B (type) |
|---------|---------------|---------------|
| Dairy reduction | `dairy_elimination` (functional_consequence) | `reducing_dairy_intake` (instrumental_value) |

**Issue:** The dual-graph architecture uses (session_id, slot_name, node_type) as a unique key. Different node_types prevent merging even when semantics are identical.

**Question:** Is this intentional (preserving methodology hierarchy) or a bug (LLM inconsistency)?

## Sample Mappings Analysis

### True Merges (Correct Behavior)

| Canonical Slot | Surface Nodes Mapped | Quality |
|----------------|---------------------|---------|
| `minimal_ingredients` (3) | "minimal ingredient list", "only oats, water, and sea salt", "clean and simple" | ✅ Excellent |
| `sustained_energy` (3) | "more energy to do things I want", "have energy for evening workout", "not having ups and downs" | ✅ Good |
| `excluded_additives` (2) | "no carrageenan", "no added oils" | ✅ Excellent |
| `enhanced_presence` (2) | "show up better for everything", "be more present with friends" | ✅ Good |

### Edge Cases (Ambiguous)

| Canonical Slot | Surface Node | Assessment |
|----------------|--------------|------------|
| `blends_smoothly` | "blends really well" | ⚠️ Could be functional or attribute |
| `coffee_milk_substitute` | "use in coffee instead of regular milk" | ⚠️ Very specific, unlikely to repeat |

### False Merges (Should Be Separate)

None identified in this sample. All mappings appear semantically coherent.

## False Merge Analysis (50 Random Samples)

**Method:** Reviewed all 39 mappings (100% of available data).

| Category | Count | Percentage |
|----------|-------|------------|
| True Merge (correct) | 35 | 90% |
| False Merge (should separate) | 0 | 0% |
| Edge Case (ambiguous) | 4 | 10% |

**Conclusion:** The slot mapping quality is high. Issues are in slot creation (fragmentation), not mapping.

## Recommendations

### Immediate Actions (Priority 1)

1. **~~Fix canonical edge creation~~** ✅ DONE
   - Root cause: field name mismatch (`source_id` vs `source_node_id`) in `graph_service.py`
   - Fix: Changed `edge.get("source_id")` → `edge.get("source_node_id")` (and target)

2. **Reduce slot proliferation** (feeds into bead gjb5)
   - Modify LLM prompt to favor consolidation over specificity
   - Lower the similarity threshold from 0.88 to ~0.80 to catch near-misses
   - Consider lemmatization before exact-match lookup (would catch `reduce_inflammation` / `reduced_inflammation`)

3. **~~Investigate similarity scores~~** ✅ RESOLVED (by design)
   - All 1.0 scores are expected: exact match path and new slot creation path both correctly set 1.0
   - Embedding similarity path is a conservative fallback (0.88 threshold) that activates as slot density grows

### Medium-Term Improvements (Priority 2)

4. **Cross-node_type merging**
   - Consider removing node_type from unique constraint OR
   - Add post-processing step to merge slots across types

5. **Slot promotion tuning**
   - Current: 6.7% active/candidate ratio
   - Target: 20-30% (means lowering threshold or increasing support)
   - Consider dynamic threshold based on interview length

6. **Add slot quality metrics**
   - Track false merge rate via human review
   - Monitor slot proliferation rate (slots/turn)
   - Alert when node-to-slot ratio exceeds 1.5:1

### Long-Term Research (Priority 3)

7. **Embedding model evaluation**
   - Test spaCy en_core_web_md vs en_core_web_lg
   - Compare with sentence-transformers models
   - Benchmark similarity quality on known pairs

8. **LLM prompt optimization**
   - A/B test different prompt strategies
   - Measure impact on slot count and quality
   - Consider few-shot examples

## Files Generated

- `scripts/review_canonical_slots.py` - Quality review extraction script
- `data/phase5_quality_review_raw.json` - Raw review data

## Next Steps

1. ~~Investigate why canonical edges are not being created~~ ✅ Fixed (field name mismatch)
2. ~~Investigate similarity scores~~ ✅ Resolved (by design)
3. Re-run simulation and quality review to verify canonical edges now appear
4. Address slot fragmentation (~28% missed merge rate) in bead gjb5 (threshold tuning)
5. Consider lemmatization or fuzzy matching before exact-match lookup

## Sign-Off

**Initial review:** Claude Code (glm-4.7) — 2026-02-08
**Corrected review:** Claude Opus 4.6 — 2026-02-08
**Corrections:** Fixed misleading false merge rate metric (was 12%, actual 0%), identified 5 additional missed-merge pairs (total ~9), confirmed similarity=1.0 is by design, root-caused and fixed canonical edge bug
**Status:** ✅ Review complete, critical bug fixed, fragmentation issue documented for gjb5
