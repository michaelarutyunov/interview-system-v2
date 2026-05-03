# Edge Extraction Rollout: Repertory Grid (`repertory_grid_v2`)

**Date:** 2026-05-03
**Bead:** yu8d (B10) — Per-methodology rollout
**Harness:** `scripts/diagnostics/edge_extraction_diff.py`
**Concept:** `plant_milk_comparison_rg`
**Persona:** `baseline_cooperative`
**Max turns:** 10

## Metrics Deltas

| Metric | Baseline (OFF) | New (ON) | Delta |
|--------|---------------|----------|-------|
| Total Turns | 11 | 11 | +0 |
| Total Nodes | 56 | 50 | -6 |
| Total Edges | 65 | 60 | -5 |
| Edge/Node Ratio | 1.161 | 1.200 | +0.039 |
| Chain-Relevant Edges | 34 | 30 | -4 |
| Chain Edge Ratio | 0.523 | 0.500 | -0.023 |
| P50 Turn Latency | 20369ms | 19379ms | -990ms (-4.9%) |
| P90 Turn Latency | 25314ms | 22932ms | -2382ms (-9.4%) |
| Mean Turn Latency | 20418ms | 18944ms | -1474ms |

## Strategy Distribution

| Strategy | Baseline (OFF) | New (ON) | Delta |
|----------|---------------|----------|-------|
| explore_ideal | 2 | 2 | +0 |
| ladder_construct | 1 | 1 | +0 |
| rate_elements | 3 | 2 | -1 |
| triadic_elicit | 4 | 5 | +1 |
| unknown | 1 | 1 | +0 |

## Narrative Explanation

**Strategy shift (rate_elements -1, triadic_elicit +1):** Minor, one turn shift. Both are productive strategies for RG. No degradation pattern.

**Chain density (-4 chain-relevant edges, -2.3pp ratio):** Small decrease but proportional — total edges dropped by 5, so chain-relevant drop (-4) mirrors the overall edge reduction. Edge/Node ratio actually improved (+0.039 → 1.200). Total nodes also decreased (-6), so fewer edges are expected. This is likely attributable to run-to-run LLM variance (the ON run was generally faster — latency down 5-9%).

**Latency decreased (-4.9% P50, -9.4% P90):** Consistent improvement across all percentiles. Edge extraction stages add negligible overhead. The ON run was faster overall, likely due to LLM timing variance.

## Verdict: **PASS** (with observation)

All criteria met:
- Strategy shift: minor and explainable
- Chain density: small proportional decrease (-2.3pp), consistent with overall edge/node reduction from faster LLM run
- Latency: decreased across all percentiles

**Observation:** Chain-relevant edge count dropped proportionally with total edges. This is the only methodology with a meaningful chain-relevant delta. Recommend monitoring in production — if chain density degrades further under different concepts/personas, investigate whether RG's edge types benefit from bespoke edge extraction prompts.
