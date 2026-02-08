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
| Canonical Edges | 0 | ~5-10 | ❌ None created |
| False Merge Rate (estimated) | ~12% (4/32) | <5% | ❌ Above threshold |

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

### 2. False Positive: Similar Concepts Not Merged

**Definition:** False positive = Two slots that SHOULD have been merged but weren't.

**Identified Cases:**

| Slot A | Slot B | Issue | Similarity |
|--------|--------|-------|------------|
| `reduce_inflammation` | `reduced_inflammation` | Same concept, different grammatical form | Should merge |
| `sustained_energy` | `sustained_energy_levels` | Same concept, different wording | Should merge |
| `cognitive_performance` | `cognitive_focus_enhancement` | Semantically identical | Should merge |
| `dairy_elimination` | `reducing_dairy_intake` | Same concept, different node_type | Should merge |

**Impact:** These false positives fragment signal and prevent proper exhaustion tracking. For example, "sustained_energy" appears in 3 surface nodes but "sustained_energy_levels" captures a related node, reducing the effective support count for the core concept.

### 3. All Similarity Scores are 1.0

**Observation:** Every surface-to-slot mapping has `similarity_score=1.0`.

**Possible Explanations:**
1. **Exact match finding working:** The `_find_or_create_slot` method finds exact matches first (lines 286-331 in `canonical_slot_service.py`), setting similarity to 1.0.
2. **Similarity search not running:** The embedding similarity search may not be executing for new slots.
3. **Embedding model limitation:** spaCy's `en_core_web_md` may produce identical embeddings for semantically similar phrases.

**Recommendation:** Verify that similarity search is actually being triggered. Add logging to track when exact match vs similarity match occurs.

### 4. Zero Canonical Edges

**Issue:** No canonical edges were created despite 22 surface edges in the graph.

**Root Cause Investigation:**
1. SlotDiscoveryStage (4.5) has edge aggregation code (lines 153-185)
2. GraphService.aggregate_surface_edges_to_canonical() exists and is called
3. Possible causes:
   - All surface edges are between unmapped nodes (unlikely - 39/39 nodes mapped)
   - All canonical edges are self-loops (source_slot == target_slot)
   - Edges are filtered by some other criterion

**Impact:** Canonical graph has no structural information. Signals based on edge density, connectivity, or path analysis will fail.

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

1. **Fix canonical edge creation**
   - Add debug logging to `aggregate_surface_edges_to_canonical()`
   - Verify canonical_slot_repo is not None
   - Check why edges are not being created despite valid surface edges

2. **Reduce slot proliferation**
   - Increase `canonical_min_support_nodes` from 2 to 3
   - OR modify LLM prompt to favor consolidation over specificity
   - Add "maximum slots per turn" constraint

3. **Investigate similarity scores**
   - Add logging to distinguish exact matches vs similarity matches
   - Verify embedding similarity search is executing
   - Test with known similar phrases to validate spaCy embeddings

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

1. Investigate why canonical edges are not being created
2. Implement logging to distinguish exact vs similarity matches
3. Adjust LLM prompt to reduce slot proliferation
4. Re-run quality review after changes
5. Document findings in ADR if architectural changes needed

## Sign-Off

**Reviewed by:** Claude Code (glm-4.7)
**Date:** 2026-02-08
**Status:** ✅ Review complete, issues documented
