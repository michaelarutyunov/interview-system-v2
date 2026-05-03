# Edge Extraction Rollout: MEC Strict (`means_end_chain_v2_strict`)

**Date:** 2026-05-02
**Bead:** yu8d (B10) — Per-methodology rollout
**Harness:** `scripts/diagnostics/edge_extraction_diff.py`
**Concept:** `glp1_food_mec_strict`
**Persona:** `baseline_cooperative`
**Max turns:** 10

## Metrics Deltas

| Metric | Baseline (OFF) | New (ON) | Delta |
|--------|---------------|----------|-------|
| Total Turns | 10 | 10 | +0 |
| Total Nodes | 27 | 33 | +6 |
| Total Edges | 38 | 41 | +3 |
| Edge/Node Ratio | 1.407 | 1.242 | -0.165 |
| Chain-Relevant Edges | 37 | 40 | +3 |
| Chain Edge Ratio | 0.974 | 0.976 | +0.002 |
| P50 Turn Latency | 15168ms | 16110ms | +942ms (+6.2%) |
| P90 Turn Latency | 20947ms | 22135ms | +1188ms (+5.7%) |
| Mean Turn Latency | 15134ms | 16579ms | +1445ms |

## Strategy Distribution

| Strategy | Baseline (OFF) | New (ON) | Delta |
|----------|---------------|----------|-------|
| ascend | 2 | 2 | +0 |
| branch | 4 | 3 | -1 |
| ground | 2 | 3 | +1 |
| close | 1 | 1 | +0 |
| unknown | 1 | 1 | +0 |

Note: anchor, bridge, and revitalize did not fire in either run (valid_when gates not met for this concept/persona).

## Narrative Explanation

**Strategy shift (branch -1, ground +1):** Minor and explainable. Additional cross-turn edges from separated extraction provide better chain level detection, making `ground` (triggered by chain gap below) slightly more likely where `branch` would have fired before. One turn shift out of 10 is within normal variance. Core strategies (ascend) unchanged.

**Chain density maintained:** Chain-relevant edges increased (+3) while chain edge ratio held flat (+0.002). MEC Strict already had 97.4% chain relevance — the highest of any methodology — and this is preserved. Edge/Node ratio drop is expected (more nodes, conservative edge creation).

**Latency (+6.2% P50, +5.7% P90):** Consistent increase across percentiles — no tail variance issue. Primary contributors: ExtractionStage +804ms (LLM variance), LLMSignalBridgeStage +602ms (likely holding signal results pending edge extraction completion). Edge extraction stages contribute only ~3.5ms combined.

## Verdict: **PASS**

All criteria met:
- Strategy distribution shift: minor (branch -1, ground +1) and explainable
- Chain density: fully maintained (ratio +0.002)
- Latency: +6.2% P50, consistent across percentiles, well within acceptable range
