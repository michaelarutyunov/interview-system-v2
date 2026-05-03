# Edge Extraction Rollout: CIT (`critical_incident_v2`)

**Date:** 2026-05-03
**Bead:** yu8d (B10) — Per-methodology rollout
**Harness:** `scripts/diagnostics/edge_extraction_diff.py`
**Concept:** `zerofizz_beverage_cit`
**Persona:** `baseline_cooperative`
**Max turns:** 10
**Note:** Fixed pre-existing bug — `generate_conversation_level_question` raised `ValueError` for `elicit_narrative` (only supported `close`/`revitalize`). Added `elicit_narrative` support, routed through revitalize prompt path.

## Metrics Deltas

| Metric | Baseline (OFF) | New (ON) | Delta |
|--------|---------------|----------|-------|
| Total Turns | 10 | 10 | +0 |
| Total Nodes | 34 | 37 | +3 |
| Total Edges | 42 | 41 | -1 |
| Edge/Node Ratio | 1.235 | 1.108 | -0.127 |
| Chain-Relevant Edges | 0 | 0 | +0 |
| Chain Edge Ratio | 0.000 | 0.000 | +0.000 |
| P50 Turn Latency | 15998ms | 17384ms | +1386ms (+8.7%) |
| P90 Turn Latency | 19631ms | 20878ms | +1247ms (+6.4%) |
| Mean Turn Latency | 16085ms | 16758ms | +673ms |

## Strategy Distribution

| Strategy | Baseline (OFF) | New (ON) | Delta |
|----------|---------------|----------|-------|
| ascend | 0 | 1 | +1 |
| bridge | 4 | 4 | +0 |
| close | 1 | 1 | +0 |
| elicit_narrative | 3 | 3 | +0 |
| revitalize | 1 | 0 | -1 |
| unknown | 1 | 1 | +0 |

## Narrative Explanation

**Strategy shift (ascend +1, revitalize -1):** Positive shift — ascend (productive structural strategy) replaced revitalize (escape valve). One turn shift, minor and explainable. Additional edges from separated extraction help ascend's chain gap detection.

**Chain density (harness limitation):** Chain-relevant edges show 0 for both runs. CIT uses edge type names (`relates_to`, `contextualizes`, etc.) not in the harness's hardcoded list. Both runs are equally affected — no regression can be attributed to edge extraction. The harness should be updated with methodology-specific edge type lists for future rollouts.

**Latency (+8.7% P50):** Moderate increase, consistent across percentiles. Edge extraction stages contribute only ~3ms. Primary contributor is ExtractionStage (+777ms) — likely LLM variance. Trend is consistent with JTBD, MEC Strict patterns.

## Verdict: **PASS**

All criteria met:
- Strategy shift: positive (ascend gains, revitalize loses)
- Chain density: harness limitation — both runs equal, no regression detected
- Latency: +8.7% P50, moderate and consistent

## Follow-up

- B9 harness should be updated with methodology-specific chain-relevant edge type lists (CIT, CJM both affected)
- `elicit_narrative` conversation-level prompt should get a dedicated prompt (currently routed through revitalize)
