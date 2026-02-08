# Phase 4 Test Results - Dual-Graph System

**Date:** 2026-02-08
**Bead:** 3ag1 - Run comprehensive synthetic interview test suite

## Test Configuration

| Scenario | SRL | Canonical Slots | Session ID |
|----------|-----|-----------------|------------|
| 1 - Baseline | ✗ | ✗ | `5e96da51-bd54-4776-95f4-74dda381f128` |
| 2 - SRL only | ✓ | ✗ | `53c5c631-4d3c-4499-bb9c-6f0fce844c17` |
| 3 - Canonical only | ✗ | ✓ | **FAILED** (UNIQUE constraint bug) |
| 4 - Full system | ✓ | ✓ | Not tested |

## Results Summary

### Scenario 1: Baseline (No SRL, No Canonical)

```
Nodes: 35
Edges: 13
Edge/Node Ratio: 0.37
```

### Scenario 2: SRL Only

```
Nodes: 33
Edges: 12
Edge/Node Ratio: 0.36
```

**Observation:** SRL preprocessing produced slightly fewer nodes (-6%) and edges (-8%).

## Issues Found

### 1. UNIQUE Constraint Bug (Critical)

**Error:**
```
sqlite3.IntegrityError: UNIQUE constraint failed: canonical_slots.session_id, canonical_slots.slot_name, canonical_slots.node_type
```

**Location:** `src/persistence/repositories/canonical_slot_repo.py:90` (create_slot)

**Root Cause:** The slot discovery logic attempts to create a canonical slot without first checking if one with the same (session_id, slot_name, node_type) already exists.

**Impact:** Scenario 3 (Canonical only) and Scenario 4 (Full system) cannot complete.

**Fix Required:** In `CanonicalSlotService._find_or_create_slot()`, check if a matching slot exists before calling `create_slot()`. Use a "find or create" pattern similar to `GraphRepository.find_node_by_label_and_type()`.

### 2. Missing signal_norms (Fixed During Testing)

**Error:**
```
ValueError: Numeric signal 'graph.canonical_concept_count' has value 2 (>1) but no signal_norm defined.
```

**Fix:** Added canonical signals to `signal_norms` in `config/methodologies/means_end_chain.yaml`:
```yaml
graph.canonical_concept_count: 30
graph.canonical_edge_density: 1.0
graph.canonical_exhaustion_score: 1.0
```

## Recommendations

1. **Fix UNIQUE constraint bug** before running Scenarios 3 and 4
2. Consider running tests with a fresh database for each scenario to avoid state pollution
3. Add integration tests for canonical slot discovery

## Files Created During Testing

- `scripts/compare_extraction_metrics.py` - Metrics comparison script (bead pong)
- `/tmp/s1_baseline.log` - Scenario 1 logs
- `/tmp/s2_srl_only.log` - Scenario 2 logs
- `/tmp/s3_canonical_only.log` - Scenario 3 logs (error)

## Next Steps

1. Fix the UNIQUE constraint bug in canonical slot discovery
2. Re-run Scenarios 3 and 4
3. Use `compare_extraction_metrics.py` to generate full comparison table
4. Document canonical graph metrics (concept_count, edge_count, orphan_count)
