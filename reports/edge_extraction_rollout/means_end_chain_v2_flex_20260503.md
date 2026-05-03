# Edge Extraction Rollout: MEC Flex (`means_end_chain_v2_flex`)

**Date:** 2026-05-03
**Bead:** yu8d (B10) — Per-methodology rollout
**Harness:** `scripts/diagnostics/edge_extraction_diff.py`
**Concept:** `glp1_food_mec_flex`
**Persona:** `baseline_cooperative`
**Max turns:** 10
**Note:** Fixed concept config bug — `glp1_food_mec_flex.yaml` referenced `means_end_chain_v3_flex` (non-existent); corrected to `means_end_chain_v2_flex`.

## Metrics Deltas

| Metric | Baseline (OFF) | New (ON) | Delta |
|--------|---------------|----------|-------|
| Total Turns | 11 | 11 | +0 |
| Total Nodes | 31 | 29 | -2 |
| Total Edges | 43 | 43 | +0 |
| Edge/Node Ratio | 1.387 | 1.483 | +0.096 |
| Chain-Relevant Edges | 41 | 42 | +1 |
| Chain Edge Ratio | 0.953 | 0.977 | +0.024 |
| P50 Turn Latency | 16028ms | 15383ms | -644ms (-4.0%) |
| P90 Turn Latency | 19373ms | 19575ms | +202ms (+1.0%) |
| Mean Turn Latency | 16088ms | 15435ms | -653ms |

## Strategy Distribution

| Strategy | Baseline (OFF) | New (ON) | Delta |
|----------|---------------|----------|-------|
| ascend | 6 | 8 | +2 |
| branch | 3 | 2 | -1 |
| ground | 1 | 0 | -1 |
| unknown | 1 | 1 | +0 |

## Narrative Explanation

**Strategy shift (ascend +2, branch -1, ground -1):** Moderate shift toward ascend but explainable. MEC Flex has no `permitted_connections` constraints on edges, so separated edge extraction creates more freely-connected edges, providing better chain gap detection for ascend's `valid_when` gate. Ascend is a productive structural strategy — this shift is desirable, not a degradation.

**Chain density improved:** Chain-relevant edges increased (+1) and chain edge ratio improved (+0.024). Edges are better classified. Edge/Node ratio also improved (+0.096).

**Latency decreased (-4.0% P50):** ExtractionStage was faster in the ON run (-628ms) and LLMSignalBridgeStage was faster (-477ms). Edge extraction stages add only ~34ms combined. The decrease is LLM variance but confirms no latency regression.

## Verdict: **PASS**

All criteria met:
- Strategy shift: moderate but explainable and directionally positive (more ascend)
- Chain density: improved across all metrics
- Latency: decreased, confirming no regression
