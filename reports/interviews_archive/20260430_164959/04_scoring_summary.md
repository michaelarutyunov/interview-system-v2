# Scoring Summary

Source: `04_scoring.csv`
Total rows: 18,269 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 1362 | 1392 | 98% | 0.300 |
| convgraph.node.focus.count.none | 1278 | 1392 | 92% | 0.200 |
| interview.strategy.self_count | 1065 | 1878 | 57% | -0.095 |
| meta.saturation.canonical.high | 720 | 928 | 78% | -0.300 |
| convgraph.node.novelty.high | 576 | 1392 | 41% | 0.267 |
| response.semantic.llm.certainty.low | 353 | 464 | 76% | 0.800 |
| convgraph.node.chain.has_attribute_foundation.true | 320 | 536 | 60% | 0.075 |
| convgraph.node.chain.has_attribute_foundation.false | 216 | 536 | 40% | -0.150 |
| convgraph.node.llm.elaboration.low | 184 | 376 | 49% | 0.375 |
| response.semantic.llm.engagement.high | 146 | 464 | 32% | 0.100 |
| meta.saturation.conversation.high | 126 | 928 | 14% | -0.400 |
| convgraph.node.exhaustion | 114 | 1392 | 8% | -0.090 |
| convgraph.node.recency | 114 | 1392 | 8% | 0.230 |
| response.semantic.llm.engagement.low | 113 | 939 | 12% | -0.293 |
| canongraph.node.novelty.new | 67 | 464 | 14% | 0.300 |
| response.semantic.llm.certainty.mid | 67 | 464 | 14% | 0.400 |
| convgraph.node.chain.gap.below.true | 51 | 268 | 19% | 0.500 |
| convgraph.node.llm.charge.positive | 47 | 188 | 25% | 0.100 |
| convgraph.node.llm.elaboration.high | 44 | 752 | 6% | -0.012 |
| convgraph.node.llm.charge.negative | 42 | 376 | 11% | 0.275 |
| convgraph.node.chain.gap.above.true | 20 | 268 | 8% | 0.500 |
| meta.saturation.conversation | 10 | 11 | 91% | -0.217 |
| meta.saturation.canonical | 10 | 11 | 91% | -0.332 |
| interview.phase.early | 8 | 22 | 36% | -3.000 |
| interview.phase.mid | 5 | 11 | 46% | -3.000 |
| interview.phase.late | 2 | 11 | 18% | 0.800 |
| convgraph.node.focus.count.medium | 1 | 464 | 0% | -0.200 |
| response.semantic.llm.engagement.trend.shallowing | 1 | 11 | 9% | 0.300 |

## Global Signals

- `response.semantic.llm.engagement.low`
- `response.semantic.llm.engagement.trend.shallowing`
- `response.semantic.llm.engagement.trend.fatigued`
- `meta.saturation.conversation`
- `meta.saturation.canonical`
- `interview.phase.early`
- `interview.strategy.self_count`
- `interview.phase.late`
- `interview.phase.mid`

## Dead Signals

| Signal | Max Weight |
|--------|-----------|
| convgraph.node.focus.count.high | 0.40 |
| convgraph.node.is_orphan.true | 0.50 |
| response.semantic.llm.engagement.trend.fatigued | 0.80 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 1362 | 1392 | 98% |
| convgraph.node.focus.count.none | 1278 | 1392 | 92% |
| meta.saturation.conversation | 10 | 11 | 91% |
| meta.saturation.canonical | 10 | 11 | 91% |

## Phase Multiplier Differential

Gap widened by multiplier: 3/11 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | ascend | surface_tension | 1.00 | 1.00 | 0.000 |
| 2 | early | ground | ascend | 1.20 | 1.00 | 0.290 |
| 3 | early | ground | ground | 1.20 | 1.20 | 0.000 |
| 4 | early | ascend | surface_tension | 1.00 | 1.00 | 0.000 |
| 5 | mid | ascend | surface_tension | 1.30 | 1.00 | 0.462 |
| 6 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 7 | mid | surface_tension | surface_tension | 1.00 | 1.00 | 0.000 |
| 8 | mid | surface_tension | surface_tension | 1.00 | 1.00 | 0.000 |
| 9 | mid | surface_tension | surface_tension | 1.00 | 1.00 | 0.000 |
| 10 | late | surface_tension | surface_tension | 1.00 | 1.00 | 0.000 |
| 11 | late | close | ascend | 1.50 | 1.00 | 0.400 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| surface_tension | 369.650 | -42.620 | 327.030 |
| ascend | 364.840 | -96.476 | 268.364 |
| anchor | 328.760 | -151.712 | 177.048 |
| ground | 326.890 | -210.864 | 116.026 |
| revitalize | 0.800 | -17.488 | -16.688 |
| close | 1.600 | -27.000 | -25.400 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| no noticeable taste difference from regular soda | ef3699e7 | 2 |
| feel like I'm not sacrificing anything | 059280e7 | 1 |
| sugar-free choice driven by availability not intention | 6e590795 | 1 |
| avoid feeling like I'm settling for a lesser option | 85a49fc9 | 1 |

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
