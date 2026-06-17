# Scoring Summary

Source: `04_scoring.csv`
Total rows: 21,215 (gated: 0)

## Signal Firing Rates

| Signal | Fired | Total | % | Avg Contribution |
|--------|-------|-------|---|------------------|
| convgraph.node.focus.streak.none | 1566 | 1593 | 98% | 0.300 |
| convgraph.node.focus.count.none | 1479 | 1593 | 93% | 0.200 |
| interview.strategy.self_count | 1189 | 2144 | 56% | -0.090 |
| meta.saturation.canonical.high | 762 | 1062 | 72% | -0.300 |
| convgraph.node.novelty.high | 684 | 1593 | 43% | 0.267 |
| response.semantic.llm.engagement.high | 467 | 531 | 88% | 0.100 |
| convgraph.node.chain.has_attribute_foundation.false | 334 | 624 | 54% | -0.150 |
| convgraph.node.chain.has_attribute_foundation.true | 290 | 624 | 46% | 0.075 |
| convgraph.node.llm.elaboration.low | 290 | 498 | 58% | 0.375 |
| response.semantic.llm.certainty.mid | 206 | 531 | 39% | 0.400 |
| response.semantic.llm.certainty.low | 185 | 531 | 35% | 0.800 |
| response.semantic.llm.engagement.low | 129 | 1072 | 12% | -0.294 |
| convgraph.node.llm.elaboration.high | 116 | 996 | 12% | -0.013 |
| convgraph.node.chain.gap.below.true | 116 | 312 | 37% | 0.500 |
| convgraph.node.recency | 114 | 1593 | 7% | 0.232 |
| convgraph.node.exhaustion | 114 | 1593 | 7% | -0.103 |
| convgraph.node.llm.charge.negative | 88 | 498 | 18% | 0.275 |
| canongraph.node.novelty.new | 81 | 531 | 15% | 0.300 |
| convgraph.node.llm.charge.positive | 72 | 249 | 29% | 0.100 |
| convgraph.node.chain.gap.above.true | 62 | 312 | 20% | 0.500 |
| meta.saturation.canonical | 10 | 10 | 100% | -0.348 |
| meta.saturation.conversation | 9 | 10 | 90% | -0.246 |
| interview.phase.early | 8 | 20 | 40% | -3.000 |
| interview.phase.mid | 5 | 10 | 50% | -3.000 |
| interview.phase.late | 1 | 10 | 10% | 0.800 |

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
| convgraph.node.focus.count.medium | 0.20 |
| convgraph.node.is_orphan.true | 0.50 |
| meta.saturation.conversation.high | 0.40 |
| response.semantic.llm.engagement.trend.fatigued | 0.80 |
| response.semantic.llm.engagement.trend.shallowing | 0.30 |

## Always-Firing Signals (>80%)

| Signal | Fired | Total | % |
|--------|-------|-------|---|
| convgraph.node.focus.streak.none | 1566 | 1593 | 98% |
| convgraph.node.focus.count.none | 1479 | 1593 | 93% |
| response.semantic.llm.engagement.high | 467 | 531 | 88% |
| meta.saturation.canonical | 10 | 10 | 100% |
| meta.saturation.conversation | 9 | 10 | 90% |

## Phase Multiplier Differential

Gap widened by multiplier: 2/10 turns

| Turn | Phase | Winner | Runner-up | Winner Multiplier | Runner-up Multiplier | Effect |
|------|-------|--------|-----------|-------------------|---------------------|--------|
| 1 | early | ascend | ground | 1.00 | 1.20 | -0.320 |
| 2 | early | ascend | ground | 1.00 | 1.20 | -0.314 |
| 3 | early | ascend | anchor | 1.00 | 1.20 | -0.308 |
| 4 | early | surface_tension | surface_tension | 1.00 | 1.00 | 0.000 |
| 5 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 6 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 7 | mid | surface_tension | surface_tension | 1.00 | 1.00 | 0.000 |
| 8 | mid | ground | ground | 1.30 | 1.30 | 0.000 |
| 9 | mid | ascend | surface_tension | 1.30 | 1.00 | 0.480 |
| 10 | late | close | ascend | 1.50 | 1.00 | 0.400 |

## Signal Budget Decomposition

| Strategy | Positive Mass | Negative Mass | Net |
|----------|--------------|--------------|-----|
| ascend | 435.730 | -133.942 | 301.788 |
| anchor | 420.220 | -135.464 | 284.756 |
| surface_tension | 328.400 | -44.600 | 283.800 |
| ground | 414.980 | -195.348 | 219.632 |
| revitalize | 0.500 | -17.702 | -17.202 |
| close | 0.800 | -27.000 | -26.200 |

## Node Selection Frequency

| Node Label | Node ID | Turns Selected |
|------------|---------|----------------|
| short-lived refresh that fades after an hour | 25525c5b | 1 |
| fizz sensation dominates morning drink choice (90% of appeal) | 3c6b9af0 | 1 |
| waking up groggy and needing to clear head fast | 58d1f14d | 1 |
| feel alive and present instead of zombie-like | 64c7c3fb | 1 |
| feel jolted awake and reset | 81e4b7b0 | 1 |
| make the afternoon feel less blah | 9e2ae96b | 1 |
| working at the office in the afternoon | e125f1ed | 1 |

## Gate Analysis

No gated pairs — all strategies eligible for all nodes.
