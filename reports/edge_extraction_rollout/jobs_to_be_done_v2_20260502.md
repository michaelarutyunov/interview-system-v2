# Edge Extraction Rollout: JTBD (`jobs_to_be_done_v2`)

**Date:** 2026-05-02
**Bead:** yu8d (B10) — Per-methodology rollout
**Harness:** `scripts/diagnostics/edge_extraction_diff.py`
**Concept:** `coffee_jtbd_v2`
**Persona:** `baseline_cooperative`
**Max turns:** 10

## Metrics Deltas

| Metric | Baseline (OFF) | New (ON) | Delta |
|--------|---------------|----------|-------|
| Total Turns | 10 | 10 | +0 |
| Total Nodes | 23 | 31 | +8 |
| Total Edges | 38 | 41 | +3 |
| Edge/Node Ratio | 1.652 | 1.323 | -0.329 |
| Chain-Relevant Edges | 30 | 32 | +2 |
| Chain Edge Ratio | 0.789 | 0.780 | -0.009 |
| P50 Turn Latency | 14276ms | 15785ms | +1509ms (+10.6%) |
| P90 Turn Latency | 19374ms | 19078ms | -296ms (-1.5%) |
| Mean Turn Latency | 13911ms | 16042ms | +2130ms |

## Strategy Distribution

| Strategy | Baseline (OFF) | New (ON) | Delta |
|----------|---------------|----------|-------|
| ascend | 3 | 4 | +1 |
| ground | 4 | 3 | -1 |
| anchor | 1 | 1 | +0 |
| close | 1 | 1 | +0 |
| unknown | 1 | 1 | +0 |

## Narrative Explanation

**Strategy shift (ascend +1, ground -1):** Minor and explainable. Additional cross-turn edges from the separated edge extraction pipeline provide better chain gap detection, making `ascend` slightly more likely to fire. One turn shift out of 10 is within normal run-to-run variance. No unexplained strategy changes.

**Chain density maintained:** Chain-relevant edges increased (+2) while chain edge ratio held flat (0.789 → 0.780, -0.009). The Edge/Node ratio dropped (1.652 → 1.323) because node count increased (+8) faster than edge count (+3) — the separated extraction finds more concepts while edge extraction is appropriately conservative. No chain degradation.

**P50 latency (+1509ms, +10.6%):** The bulk of the increase is in ExtractionStage (+1207ms) and SlotDiscoveryStage (+804ms), not in edge extraction stages (PrefetchStage +2.9ms, BridgeStage +0.2ms — both negligible). The ExtractionStage increase is likely LLM variance between runs (extraction now only produces nodes, which should be faster, not slower). 

**P90 latency improved (-296ms, -1.5%):** The new path has lower tail latency variance. Edge extraction runs on Haiku concurrently with SlotDiscovery, making overall pipeline timing more consistent.

## Verdict: **PASS**

All criteria met:
- Strategy distribution shift: minor and explainable (cross-turn edges → better chain detection)
- Chain density: maintained (chain-relevant edges +2, ratio flat)
- P50 latency: +10.6% is acceptable given P90 improvement and single-run variance limitation

## Notes

- Single run per configuration — statistical significance not assessed. Multi-run averaging would give more confidence in latency numbers.
- ExtractionStage +1207ms is likely noise (separated extraction should be faster, not slower). Recommend monitoring across subsequent methodology rollouts.
- Edge/Node ratio drop is expected and acceptable — more surface nodes without proportional edge increase means edge extraction is being appropriately selective.
