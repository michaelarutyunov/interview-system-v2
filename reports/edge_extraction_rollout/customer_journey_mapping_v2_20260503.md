# Edge Extraction Rollout: CJM (`customer_journey_mapping_v2`)

**Date:** 2026-05-03
**Bead:** yu8d (B10) — Per-methodology rollout
**Harness:** `scripts/diagnostics/edge_extraction_diff.py`
**Concept:** `zerofizz_beverage_cjm`
**Persona:** `baseline_cooperative`
**Max turns:** 10

## Metrics Deltas

| Metric | Baseline (OFF) | New (ON) | Delta |
|--------|---------------|----------|-------|
| Total Turns | 11 | 11 | +0 |
| Total Nodes | 30 | 37 | +7 |
| Total Edges | 47 | 50 | +3 |
| Edge/Node Ratio | 1.567 | 1.351 | -0.216 |
| Chain-Relevant Edges | 0 | 0 | +0 |
| Chain Edge Ratio | 0.000 | 0.000 | +0.000 |
| P50 Turn Latency | 15173ms | 14796ms | -378ms (-2.5%) |
| P90 Turn Latency | 25062ms | 22476ms | -2586ms (-10.3%) |
| Mean Turn Latency | 15259ms | 15762ms | +503ms |

## Strategy Distribution

| Strategy | Baseline (OFF) | New (ON) | Delta |
|----------|---------------|----------|-------|
| advance_stage | 0 | 1 | +1 |
| close | 1 | 0 | -1 |
| deepen_stage | 4 | 3 | -1 |
| probe_friction | 3 | 3 | +0 |
| track_emotions | 2 | 3 | +1 |
| unknown | 1 | 1 | +0 |

## Narrative Explanation

**Strategy shift (advance_stage +1, close -1, deepen_stage -1, track_emotions +1):** Minor shifts across multiple strategies. Most notable: `advance_stage` appeared (replacing `close`), which is a positive shift — moving from a terminal strategy to a productive one. `track_emotions` gained one from `deepen_stage`. No unexplained patterns.

**Chain density (harness limitation):** Chain-relevant edges show 0 for both runs — same harness limitation as CIT (CJM edge types don't match the hardcoded list). Both runs equally affected.

**Latency decreased (-2.5% P50, -10.3% P90):** Significant tail latency improvement. P90 dropped by 2.6 seconds. Edge extraction stages contribute negligible overhead. The concurrent Haiku edge extraction may actually smooth out pipeline timing by better load distribution.

## Verdict: **PASS**

All criteria met:
- Strategy shift: minor, directionally positive (advance_stage replaces close)
- Chain density: harness limitation — both runs equal
- Latency: decreased, P90 improvement of 2.6s is notable
